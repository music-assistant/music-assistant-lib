"""SMB filesystem provider for Music Assistant."""


import asyncio
import contextvars
import os
from contextlib import asynccontextmanager
from io import BytesIO
from typing import AsyncContextManager, AsyncGenerator

from smb.base import SharedFile, SMBTimeout
from smb.smb_structs import OperationFailure
from smb.SMBConnection import SMBConnection

from music_assistant.helpers.util import get_ip_from_host
from music_assistant.models.enums import ProviderType
from music_assistant.models.errors import LoginFailed

from .base import FileSystemItem, FileSystemProviderBase
from .helpers import get_absolute_path, get_relative_path

SERVICE_NAME = "music_assistant"

smb_conn_ctx = contextvars.ContextVar("smb_conn_ctx", default=None)


async def create_item(
    file_path: str, entry: SharedFile, root_path: str
) -> FileSystemItem:
    """Create FileSystemItem from smb.SharedFile."""

    rel_path = get_relative_path(root_path, file_path)
    abs_path = get_absolute_path(root_path, file_path)
    return FileSystemItem(
        name=entry.filename,
        path=rel_path,
        absolute_path=abs_path,
        is_file=not entry.isDirectory,
        is_dir=entry.isDirectory,
        checksum=str(int(entry.last_write_time)),
        file_size=entry.file_size,
    )


class SMBFileSystemProvider(FileSystemProviderBase):
    """Implementation of an SMB File System Provider."""

    _attr_name = "smb"
    _attr_type = ProviderType.FILESYSTEM_SMB
    _service_name = ""
    _root_path = "/"
    _remote_name = ""
    _default_target_ip = ""

    async def setup(self) -> bool:
        """Handle async initialization of the provider."""
        # extract params from path
        if self.config.path.startswith("\\\\"):
            path_parts = self.config.path[2:].split("\\", 2)
        elif self.config.path.startswith("smb://"):
            path_parts = self.config.path[6:].split("/", 2)
        else:
            path_parts = self.config.path.split(os.sep)
        self._remote_name = path_parts[0]
        self._service_name = path_parts[1]
        if len(path_parts) > 2:
            self._root_path = os.sep + path_parts[2]

        self._default_target_ip = await get_ip_from_host(self._remote_name)
        async with self._get_smb_connection():
            return True

    async def listdir(
        self, path: str, recursive: bool = False
    ) -> AsyncGenerator[FileSystemItem, None]:
        """
        List contents of a given provider directory/path.

        Parameters:
            - path: path of the directory (relative or absolute) to list contents of.
              Empty string for provider's root.
            - recursive: If True will recursively keep unwrapping subdirectories (scandir equivalent).

        Returns:
            AsyncGenerator yielding FileSystemItem objects.

        """
        abs_path = get_absolute_path(self._root_path, path)
        async with self._get_smb_connection() as smb_conn:
            path_result: list[SharedFile] = await asyncio.to_thread(
                smb_conn.listPath, self._service_name, abs_path
            )
            for entry in path_result:
                if entry.filename.startswith("."):
                    # skip invalid/system files and dirs
                    continue
                file_path = os.path.join(path, entry.filename)
                item = await create_item(file_path, entry, self._root_path)
                if recursive and item.is_dir:
                    # yield sublevel recursively
                    try:
                        async for subitem in self.listdir(file_path, True):
                            yield subitem
                    except (OSError, PermissionError) as err:
                        self.logger.warning("Skip folder %s: %s", item.path, str(err))
                elif item.is_file or item.is_dir:
                    yield item

    async def resolve(self, file_path: str) -> FileSystemItem:
        """Resolve (absolute or relative) path to FileSystemItem."""
        absolute_path = get_absolute_path(self._root_path, file_path)
        async with self._get_smb_connection() as smb_conn:
            entry: SharedFile = await asyncio.to_thread(
                smb_conn.getAttributes,
                self._service_name,
                absolute_path,
            )
        return FileSystemItem(
            name=file_path,
            path=get_relative_path(self._root_path, file_path),
            absolute_path=absolute_path,
            is_file=not entry.isDirectory,
            is_dir=entry.isDirectory,
            checksum=str(int(entry.last_write_time)),
            file_size=entry.file_size,
        )

    async def exists(self, file_path: str) -> bool:
        """Return bool is this FileSystem musicprovider has given file/dir."""
        try:
            await self.resolve(file_path)
        except (OperationFailure, SMBTimeout):
            return False
        return True

    async def read_file_content(
        self, file_path: str, seek: int = 0
    ) -> AsyncGenerator[bytes, None]:
        """Yield (binary) contents of file in chunks of bytes."""
        abs_path = get_absolute_path(self._root_path, file_path)
        chunk_size = 256000

        async with self._get_smb_connection() as smb_conn:

            async def _read_chunk_from_file(offset: int):

                with BytesIO() as file_obj:
                    await asyncio.to_thread(
                        smb_conn.retrieveFileFromOffset,
                        self._service_name,
                        abs_path,
                        file_obj,
                        offset,
                        chunk_size,
                    )
                    file_obj.seek(0)
                    return file_obj.read()

            offset = seek
            chunk_num = 1
            while True:
                data = await _read_chunk_from_file(offset)
                if not data:
                    break
                yield data
                chunk_num += 1
                if len(data) < chunk_size:
                    break
                offset += len(data)

    async def write_file_content(self, file_path: str, data: bytes) -> None:
        """Write entire file content as bytes (e.g. for playlists)."""
        raise NotImplementedError  # TODO !

    @asynccontextmanager
    async def _get_smb_connection(self) -> AsyncContextManager[SMBConnection]:
        """Get instance of SMBConnection."""
        target_ip = self.config.options.get("target_ip", self._default_target_ip)
        if existing := smb_conn_ctx.get():
            yield existing
            return

        with SMBConnection(
            username=self.config.username,
            password=self.config.password,
            my_name=SERVICE_NAME,
            remote_name=self._remote_name,
            # choose sane default options but allow user to override them via the options dict
            domain=self.config.options.get("domain", ""),
            use_ntlm_v2=self.config.options.get("use_ntlm_v2", False),
            sign_options=self.config.options.get("sign_options", 2),
            is_direct_tcp=self.config.options.get("is_direct_tcp", False),
        ) as smb_conn:
            target_ip = self.config.options.get("target_ip", self._default_target_ip)
            # connect
            if not await asyncio.to_thread(smb_conn.connect, target_ip):
                raise LoginFailed(f"SMB Connect failed to {self._remote_name}")
            token = smb_conn_ctx.set(smb_conn)
            yield smb_conn
        smb_conn_ctx.reset(token)
