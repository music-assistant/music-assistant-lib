"""Audiobookshelf provider for Music Assistant.

Audiobookshelf is abbreviated ABS here.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Sequence
from enum import StrEnum
from typing import TYPE_CHECKING

import aioaudiobookshelf as aioabs
from aioaudiobookshelf.client.items import LibraryItemExpandedBook as AbsLibraryItemExpandedBook
from aioaudiobookshelf.client.items import (
    LibraryItemExpandedPodcast as AbsLibraryItemExpandedPodcast,
)
from aioaudiobookshelf.exceptions import ApiError as AbsApiError
from aioaudiobookshelf.exceptions import LoginError as AbsLoginError
from aioaudiobookshelf.schema.calls_authors import (
    AuthorWithItemsAndSeries as AbsAuthorWithItemsAndSeries,
)
from aioaudiobookshelf.schema.calls_items import (
    PlaybackSessionParameters as AbsPlaybackSessionParameters,
)
from aioaudiobookshelf.schema.calls_series import SeriesWithProgress as AbsSeriesWithProgress
from aioaudiobookshelf.schema.library import (
    LibraryItemMinifiedBook as AbsLibraryItemMinifiedBook,
)
from aioaudiobookshelf.schema.library import (
    LibraryItemMinifiedPodcast as AbsLibraryItemMinifiedPodcast,
)
from aioaudiobookshelf.schema.library import LibraryMediaType as AbsLibraryMediaType
from aioaudiobookshelf.schema.session import DeviceInfo as AbsDeviceInfo
from music_assistant_models.config_entries import ConfigEntry, ConfigValueType, ProviderConfig
from music_assistant_models.enums import (
    ConfigEntryType,
    ContentType,
    MediaType,
    ProviderFeature,
    StreamType,
)
from music_assistant_models.errors import LoginFailed, MediaNotFoundError
from music_assistant_models.media_items import AudioFormat, BrowseFolder, ItemMapping, MediaItemType
from music_assistant_models.streamdetails import StreamDetails

from music_assistant.models.music_provider import MusicProvider
from music_assistant.providers.audiobookshelf.parsers import (
    parse_audiobook,
    parse_podcast,
    parse_podcast_episode,
)

if TYPE_CHECKING:
    from music_assistant_models.media_items import Audiobook, Podcast, PodcastEpisode
    from music_assistant_models.provider import ProviderManifest

    from music_assistant.mass import MusicAssistant
    from music_assistant.models import ProviderInstanceType

CONF_URL = "url"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_VERIFY_SSL = "verify_ssl"
# optionally hide podcasts with no episodes
CONF_HIDE_EMPTY_PODCASTS = "hide_empty_podcasts"


class AbsBrowsePaths(StrEnum):
    """Path prefixes for browse view."""

    LIBRARIES_BOOK = "b"
    LIBRARIES_PODCAST = "p"
    AUTHORS = "a"
    SERIES = "s"
    COLLECTIONS = "c"
    AUDIOBOOKS = "i"


class AbsBrowseItemsBook(StrEnum):
    """Folder names in browse view for books."""

    AUTHORS = "Authors"
    SERIES = "Series"
    COLLECTIONS = "Collections"
    AUDIOBOOKS = "Audiobooks"


class AbsBrowseItemsPodcast(StrEnum):
    """Folder names in browse view for podcasts."""

    PODCASTS = "Podcasts"


ABSBROWSEITEMSTOPATH: dict[str, str] = {
    AbsBrowseItemsBook.AUTHORS: AbsBrowsePaths.AUTHORS,
    AbsBrowseItemsBook.SERIES: AbsBrowsePaths.SERIES,
    AbsBrowseItemsBook.COLLECTIONS: AbsBrowsePaths.COLLECTIONS,
    AbsBrowseItemsBook.AUDIOBOOKS: AbsBrowsePaths.AUDIOBOOKS,
}


async def setup(
    mass: MusicAssistant, manifest: ProviderManifest, config: ProviderConfig
) -> ProviderInstanceType:
    """Initialize provider(instance) with given configuration."""
    return Audiobookshelf(mass, manifest, config)


async def get_config_entries(
    mass: MusicAssistant,
    instance_id: str | None = None,
    action: str | None = None,
    values: dict[str, ConfigValueType] | None = None,
) -> tuple[ConfigEntry, ...]:
    """
    Return Config entries to setup this provider.

    instance_id: id of an existing provider instance (None if new instance setup).
    action: [optional] action key called from config entries UI.
    values: the (intermediate) raw values for config entries sent with the action.
    """
    # ruff: noqa: ARG001
    return (
        ConfigEntry(
            key=CONF_URL,
            type=ConfigEntryType.STRING,
            label="Server",
            required=True,
            description="The url of the Audiobookshelf server to connect to.",
        ),
        ConfigEntry(
            key=CONF_USERNAME,
            type=ConfigEntryType.STRING,
            label="Username",
            required=True,
            description="The username to authenticate to the remote server.",
        ),
        ConfigEntry(
            key=CONF_PASSWORD,
            type=ConfigEntryType.SECURE_STRING,
            label="Password",
            required=False,
            description="The password to authenticate to the remote server.",
        ),
        ConfigEntry(
            key=CONF_VERIFY_SSL,
            type=ConfigEntryType.BOOLEAN,
            label="Verify SSL",
            required=False,
            description="Whether or not to verify the certificate of SSL/TLS connections.",
            category="advanced",
            default_value=True,
        ),
        ConfigEntry(
            key=CONF_HIDE_EMPTY_PODCASTS,
            type=ConfigEntryType.BOOLEAN,
            label="Hide empty podcasts.",
            required=False,
            description="This will skip podcasts with no episodes associated.",
            category="advanced",
            default_value=False,
        ),
    )


class Audiobookshelf(MusicProvider):
    """Audiobookshelf MusicProvider."""

    @property
    def supported_features(self) -> set[ProviderFeature]:
        """Features supported by this Provider."""
        return {
            ProviderFeature.LIBRARY_PODCASTS,
            ProviderFeature.LIBRARY_AUDIOBOOKS,
            ProviderFeature.BROWSE,
        }

    async def handle_async_init(self) -> None:
        """Pass config values to client and initialize."""
        base_url = str(self.config.get_value(CONF_URL))
        username = str(self.config.get_value(CONF_USERNAME))
        password = str(self.config.get_value(CONF_PASSWORD))
        verify_ssl = bool(self.config.get_value(CONF_VERIFY_SSL))
        session_config = aioabs.SessionConfiguration(
            session=self.mass.http_session, url=base_url, verify_ssl=verify_ssl, logger=self.logger
        )
        try:
            self._client = await aioabs.get_user_client(
                session_config=session_config, username=username, password=password
            )
        except AbsLoginError as exc:
            raise LoginFailed(f"Login to abs instance at {base_url} failed.") from exc

        # store library ids
        self.libraries_book: dict[str, str] = {}  # lib_id: lib_name
        self.libraries_podcast: dict[str, str] = {}
        # keep track of open sessions
        self.session_ids: set[str] = set()

        self.logger.debug(f"Our playback session device_id is {self.instance_id}")

    async def unload(self, is_removed: bool = False) -> None:
        """
        Handle unload/close of the provider.

        Called when provider is deregistered (e.g. MA exiting or config reloading).
        is_removed will be set to True when the provider is removed from the configuration.
        """
        await self._close_all_playback_sessions()
        await self._client.logout()

    @property
    def is_streaming_provider(self) -> bool:
        """Return True if the provider is a streaming provider."""
        # For streaming providers return True here but for local file based providers return False.
        return False

    async def sync_library(self, media_types: tuple[MediaType, ...]) -> None:
        """Obtain audiobook library ids and podcast library ids."""
        await self._sync_library_ids()
        await super().sync_library(media_types=media_types)

    async def _sync_library_ids(self) -> None:
        libraries = await self._client.get_all_libraries()
        for library in libraries:
            if library.media_type == AbsLibraryMediaType.BOOK:
                self.libraries_book[library.id_] = library.name
            elif library.media_type == AbsLibraryMediaType.PODCAST:
                self.libraries_podcast[library.id_] = library.name

    async def get_library_podcasts(self) -> AsyncGenerator[Podcast, None]:
        """Retrieve library/subscribed podcasts from the provider.

        Minified podcast information is enough.
        """
        for pod_lib_id in self.libraries_podcast:
            async for response in self._client.get_library_items(library_id=pod_lib_id):
                if not response.results:
                    break
                for abs_podcast in response.results:
                    if not isinstance(abs_podcast, AbsLibraryItemMinifiedPodcast):
                        raise TypeError("Unexpected type of podcast.")
                    mass_podcast = parse_podcast(
                        abs_podcast=abs_podcast,
                        lookup_key=self.lookup_key,
                        domain=self.domain,
                        instance_id=self.instance_id,
                        token=self._client.token,
                        base_url=str(self.config.get_value(CONF_URL)).rstrip("/"),
                    )
                    if (
                        bool(self.config.get_value(CONF_HIDE_EMPTY_PODCASTS))
                        and mass_podcast.total_episodes == 0
                    ):
                        continue
                    yield mass_podcast

    async def get_podcast(self, prov_podcast_id: str) -> Podcast:
        """Get single podcast.

        Basis information is sufficient.
        """
        abs_podcast = await self._client.get_library_item_podcast(
            podcast_id=prov_podcast_id, expanded=False
        )
        return parse_podcast(
            abs_podcast=abs_podcast,
            lookup_key=self.lookup_key,
            domain=self.domain,
            instance_id=self.instance_id,
            token=self._client.token,
            base_url=str(self.config.get_value(CONF_URL)).rstrip("/"),
        )

    async def get_podcast_episodes(self, prov_podcast_id: str) -> list[PodcastEpisode]:
        """Get all podcast episodes of podcast.

        Adds progress information.
        """
        abs_podcast = await self._client.get_library_item_podcast(
            podcast_id=prov_podcast_id, expanded=True
        )
        if not isinstance(abs_podcast, AbsLibraryItemExpandedPodcast):
            raise TypeError("Podcast has wrong type.")
        episode_list = []
        episode_cnt = 1
        for abs_episode in abs_podcast.media.episodes:
            progress = await self._client.get_my_media_progress(
                item_id=prov_podcast_id, episode_id=abs_episode.id_
            )
            mass_episode = parse_podcast_episode(
                episode=abs_episode,
                prov_podcast_id=prov_podcast_id,
                fallback_episode_cnt=episode_cnt,
                lookup_key=self.lookup_key,
                domain=self.domain,
                instance_id=self.instance_id,
                token=self._client.token,
                base_url=str(self.config.get_value(CONF_URL)).rstrip("/"),
                media_progress=progress,
            )
            episode_list.append(mass_episode)
            episode_cnt += 1
        return episode_list

    async def get_podcast_episode(self, prov_episode_id: str) -> PodcastEpisode:
        """Get single podcast episode."""
        prov_podcast_id, e_id = prov_episode_id.split(" ")
        abs_podcast = await self._client.get_library_item_podcast(
            podcast_id=prov_podcast_id, expanded=True
        )
        if not isinstance(abs_podcast, AbsLibraryItemExpandedPodcast):
            raise TypeError("Podcast has wrong type.")
        episode_cnt = 1
        for abs_episode in abs_podcast.media.episodes:
            if abs_episode.id_ == e_id:
                progress = await self._client.get_my_media_progress(
                    item_id=prov_podcast_id, episode_id=abs_episode.id_
                )
                return parse_podcast_episode(
                    episode=abs_episode,
                    prov_podcast_id=prov_podcast_id,
                    fallback_episode_cnt=episode_cnt,
                    lookup_key=self.lookup_key,
                    domain=self.domain,
                    instance_id=self.instance_id,
                    token=self._client.token,
                    base_url=str(self.config.get_value(CONF_URL)).rstrip("/"),
                    media_progress=progress,
                )

            episode_cnt += 1
        raise MediaNotFoundError("Episode not found")

    async def get_library_audiobooks(self) -> AsyncGenerator[Audiobook, None]:
        """Get Audiobook libraries.

        Need expanded version for chapters.
        """
        for book_lib_id in self.libraries_book:
            async for response in self._client.get_library_items(library_id=book_lib_id):
                if not response.results:
                    break
                for abs_audiobook in response.results:
                    if not isinstance(abs_audiobook, AbsLibraryItemMinifiedBook):
                        raise TypeError("Unexpected type of book.")
                    abs_book_expanded = await self._client.get_library_item_book(
                        book_id=abs_audiobook.id_, expanded=True
                    )
                    # use expanded version for chapters.
                    if not isinstance(abs_book_expanded, AbsLibraryItemExpandedBook):
                        raise TypeError("Unexpected type of book.")
                    mass_audiobook = parse_audiobook(
                        abs_audiobook=abs_book_expanded,
                        lookup_key=self.lookup_key,
                        domain=self.domain,
                        instance_id=self.instance_id,
                        token=self._client.token,
                        base_url=str(self.config.get_value(CONF_URL)).rstrip("/"),
                    )
                    yield mass_audiobook

    async def get_audiobook(self, prov_audiobook_id: str) -> Audiobook:
        """Get a single audiobook.

        Progress is added here.
        """
        abs_audiobook = await self._client.get_library_item_book(
            book_id=prov_audiobook_id, expanded=True
        )
        if not isinstance(abs_audiobook, AbsLibraryItemExpandedBook):
            raise TypeError("Book has wrong type.")
        progress = await self._client.get_my_media_progress(item_id=prov_audiobook_id)
        return parse_audiobook(
            abs_audiobook=abs_audiobook,
            lookup_key=self.lookup_key,
            domain=self.domain,
            instance_id=self.instance_id,
            token=self._client.token,
            base_url=str(self.config.get_value(CONF_URL)).rstrip("/"),
            media_progress=progress,
        )

    async def get_stream_details(
        self, item_id: str, media_type: MediaType = MediaType.TRACK
    ) -> StreamDetails:
        """Get stream of item."""
        # self.logger.debug(f"Streamdetails: {item_id}")
        if media_type == MediaType.PODCAST_EPISODE:
            return await self._get_stream_details_episode(item_id)
        elif media_type == MediaType.AUDIOBOOK:
            abs_audiobook = await self._client.get_library_item_book(book_id=item_id, expanded=True)
            if not isinstance(abs_audiobook, AbsLibraryItemExpandedBook):
                raise TypeError("Book has wrong type.")
            tracks = abs_audiobook.media.tracks
            if len(tracks) == 0:
                raise MediaNotFoundError("Stream not found")
            if len(tracks) > 1:
                self.logger.debug(
                    "Using playback via a session for audiobook "
                    f'"{abs_audiobook.media.metadata.title}"'
                )
                return await self._get_stream_details_session(item_id=item_id)
            self.logger.debug(
                f'Using direct playback for audiobook "{abs_audiobook.media.metadata.title}".'
            )
            return await self._get_stream_details_audiobook(abs_audiobook)
        raise MediaNotFoundError("Stream unknown")

    async def _get_stream_details_session(self, item_id: str) -> StreamDetails:
        """Give Streamdetails by opening a session."""
        # Adding audiobook id to device id makes multiple sessions for different books
        # possible, but we can an already opened session for a particular book, if
        # it exists.
        _device_info = AbsDeviceInfo(
            device_id=f"{self.instance_id}/{item_id}",
            client_name="Music Assistant",
            client_version=self.mass.version,
            manufacturer="",
            model=self.mass.server_id,
        )
        _params = AbsPlaybackSessionParameters(
            device_info=_device_info,
            force_direct_play=False,
            force_transcode=False,
            supported_mime_types=[],  # will yield stream as hls without transcoding
        )
        session = await self._client.get_playback_session(
            session_parameters=_params, item_id=item_id
        )

        # small delay, allow abs to launch ffmpeg process
        await asyncio.sleep(1)

        tracks = session.audio_tracks
        if len(tracks) == 0:
            raise RuntimeError("Playback session has no tracks to play")
        track = tracks[0]
        track_url = track.content_url
        if track_url.split("/")[1] != "hls":
            raise RuntimeError("Did expect HLS stream for session playback")
        media_type = MediaType.AUDIOBOOK
        audiobook_id = session.library_item_id
        self.session_ids.add(session.id_)
        streamdetails_id = f"{audiobook_id} {session.id_}"
        token = self._client.token
        base_url = str(self.config.get_value(CONF_URL))
        media_url = track.content_url
        stream_url = f"{base_url}{media_url}?token={token}"
        self.logger.debug(f"Using session with id {session.id_}.")
        return StreamDetails(
            provider=self.instance_id,
            item_id=streamdetails_id,
            audio_format=AudioFormat(
                content_type=ContentType.UNKNOWN,
            ),
            media_type=media_type,
            stream_type=StreamType.HLS,
            path=stream_url,
        )

    async def _get_stream_details_audiobook(
        self, abs_audiobook: AbsLibraryItemExpandedBook
    ) -> StreamDetails:
        """Only single audio file in audiobook."""
        tracks = abs_audiobook.media.tracks
        token = self._client.token
        base_url = str(self.config.get_value(CONF_URL))
        media_url = tracks[0].content_url
        stream_url = f"{base_url}{media_url}?token={token}"
        # audiobookshelf returns information of stream, so we should be able
        # to lift unknown at some point.
        return StreamDetails(
            provider=self.lookup_key,
            item_id=abs_audiobook.id_,
            audio_format=AudioFormat(
                content_type=ContentType.UNKNOWN,
            ),
            media_type=MediaType.AUDIOBOOK,
            stream_type=StreamType.HTTP,
            path=stream_url,
        )

    async def _get_stream_details_episode(self, podcast_id: str) -> StreamDetails:
        """Streamdetails of a podcast episode."""
        abs_podcast_id, abs_episode_id = podcast_id.split(" ")
        abs_episode = None

        abs_podcast = await self._client.get_library_item_podcast(
            podcast_id=abs_podcast_id, expanded=True
        )
        if not isinstance(abs_podcast, AbsLibraryItemExpandedPodcast):
            raise TypeError("Podcast has wrong type.")
        for abs_episode in abs_podcast.media.episodes:
            if abs_episode.id_ == abs_episode_id:
                break
        if abs_episode is None:
            raise MediaNotFoundError("Stream not found")
        self.logger.debug(f'Using direct playback for podcast episode "{abs_episode.title}".')
        token = self._client.token
        base_url = str(self.config.get_value(CONF_URL))
        media_url = abs_episode.audio_track.content_url
        full_url = f"{base_url}{media_url}?token={token}"
        return StreamDetails(
            provider=self.lookup_key,
            item_id=podcast_id,
            audio_format=AudioFormat(
                content_type=ContentType.UNKNOWN,
            ),
            media_type=MediaType.PODCAST_EPISODE,
            stream_type=StreamType.HTTP,
            path=full_url,
        )

    async def on_played(
        self, media_type: MediaType, item_id: str, fully_played: bool, position: int
    ) -> None:
        """Update progress in Audiobookshelf.

        In our case media_type may have 3 values:
            - PODCAST
            - PODCAST_EPISODE
            - AUDIOBOOK
        We ignore PODCAST (function is called on adding a podcast with position=None)

        """
        # self.logger.debug(f"on_played: {media_type=} {item_id=}, {fully_played=} {position=}")
        if media_type == MediaType.PODCAST_EPISODE:
            abs_podcast_id, abs_episode_id = item_id.split(" ")
            mass_podcast_episode = await self.get_podcast_episode(item_id)
            duration = mass_podcast_episode.duration
            self.logger.debug(
                f"Updating media progress of {media_type.value}, title {mass_podcast_episode.name}."
            )
            await self._client.update_my_media_progress(
                item_id=abs_podcast_id,
                episode_id=abs_episode_id,
                duration_seconds=duration,
                progress_seconds=position,
                is_finished=fully_played,
            )
        if media_type == MediaType.AUDIOBOOK:
            mass_audiobook = await self.get_audiobook(item_id)
            duration = mass_audiobook.duration
            self.logger.debug(f"Updating {media_type.value} named {mass_audiobook.name} progress")
            await self._client.update_my_media_progress(
                item_id=item_id,
                duration_seconds=duration,
                progress_seconds=position,
                is_finished=fully_played,
            )

    async def _close_all_playback_sessions(self) -> None:
        for session_id in self.session_ids:
            try:
                await self._client.close_open_session(session_id=session_id)
            except AbsApiError:
                self.logger.warning("Was unable to close playback session %s", session_id)

    async def browse(self, path: str) -> Sequence[MediaItemType | ItemMapping]:
        """Browse for audiobookshelf.

        Generates this view:
        Library_Name_A (Audiobooks)
            Audiobooks
                Audiobook_1
                Audiobook_2
            Series
                Series_1
                    Audiobook_1
                    Audiobook_2
                Series_2
                    Audiobook_3
                    Audiobook_4
            Collections
                Collection_1
                    Audiobook_1
                    Audiobook_2
                Collection_2
                    Audiobook_3
                    Audiobook_4
            Authors
                Author_1
                    Series_1
                    Audiobook_1
                    Audiobook_2
                Author_2
                    Audiobook_3
        Library_Name_B (Podcasts)
            Podcast_1
            Podcast_2
        """
        if not self.libraries_book and not self.libraries_podcast:
            await self._sync_library_ids()

        item_path = path.split("://", 1)[1]
        if not item_path:
            return self._browse_root()
        sub_path = item_path.split("/")
        lib_key, lib_id = sub_path[0].split(" ")
        if len(sub_path) == 1:
            if lib_key == AbsBrowsePaths.LIBRARIES_PODCAST:
                return await self._browse_lib_podcasts(library_id=lib_id)
            else:
                return self._browse_lib_audiobooks(current_path=path)
        elif len(sub_path) == 2:
            item_key = sub_path[1]
            match item_key:
                case AbsBrowsePaths.AUTHORS:
                    return await self._browse_authors(current_path=path, library_id=lib_id)
                case AbsBrowsePaths.SERIES:
                    return await self._browse_series(current_path=path, library_id=lib_id)
                case AbsBrowsePaths.COLLECTIONS:
                    return await self._browse_collections(current_path=path, library_id=lib_id)
                case AbsBrowsePaths.AUDIOBOOKS:
                    return await self._browse_books(library_id=lib_id)
        elif len(sub_path) == 3:
            item_key, item_id = sub_path[1:3]
            match item_key:
                case AbsBrowsePaths.AUTHORS:
                    return await self._browse_author_books(current_path=path, author_id=item_id)
                case AbsBrowsePaths.SERIES:
                    return await self._browse_series_books(series_id=item_id)
                case AbsBrowsePaths.COLLECTIONS:
                    return await self._browse_collection_books(collection_id=item_id)
        elif len(sub_path) == 4:
            # series within author
            series_id = sub_path[3]
            return await self._browse_series_books(series_id=series_id)
        return []

    def _browse_root(self) -> Sequence[MediaItemType]:
        items = []

        def _get_folder(path: str, lib_id: str, lib_name: str) -> BrowseFolder:
            return BrowseFolder(
                item_id=lib_id,
                name=lib_name,
                provider=self.lookup_key,
                path=f"{self.instance_id}://{path}",
            )

        for lib_id, lib_name in self.libraries_book.items():
            path = f"{AbsBrowsePaths.LIBRARIES_BOOK} {lib_id}"
            name = f"{lib_name} ({AbsBrowseItemsBook.AUDIOBOOKS})"
            items.append(_get_folder(path, lib_id, name))
        for lib_id, lib_name in self.libraries_podcast.items():
            path = f"{AbsBrowsePaths.LIBRARIES_PODCAST} {lib_id}"
            name = f"{lib_name} ({AbsBrowseItemsPodcast.PODCASTS})"
            items.append(_get_folder(path, lib_id, name))
        return items

    async def _browse_lib_podcasts(self, library_id: str) -> list[MediaItemType]:
        """No sub categories for podcasts."""
        items = []
        async for response in self._client.get_library_items(library_id=library_id):
            if not response.results:
                break
            for abs_podcast in response.results:
                if not isinstance(abs_podcast, AbsLibraryItemMinifiedPodcast):
                    raise TypeError("Unexpected type of podcast.")
                mass_item = await self.mass.music.get_library_item_by_prov_id(
                    media_type=MediaType.PODCAST,
                    item_id=abs_podcast.id_,
                    provider_instance_id_or_domain=self.instance_id,
                )
                if mass_item is not None:
                    items.append(mass_item)
        return items

    def _browse_lib_audiobooks(self, current_path: str) -> Sequence[MediaItemType]:
        items = []
        for item_name in AbsBrowseItemsBook:
            path = current_path + "/" + ABSBROWSEITEMSTOPATH[item_name]
            items.append(
                BrowseFolder(
                    item_id=item_name.lower(),
                    name=item_name,
                    provider=self.lookup_key,
                    path=path,
                )
            )
        return items

    async def _browse_authors(self, current_path: str, library_id: str) -> Sequence[MediaItemType]:
        abs_authors = await self._client.get_library_authors(library_id=library_id)
        items = []
        for author in abs_authors:
            path = f"{current_path}/{author.id_}"
            items.append(
                BrowseFolder(
                    item_id=author.id_,
                    name=author.name,
                    provider=self.lookup_key,
                    path=path,
                )
            )

        return items

    async def _browse_series(self, current_path: str, library_id: str) -> Sequence[MediaItemType]:
        items = []
        async for response in self._client.get_library_series(library_id=library_id):
            if not response.results:
                break
            for abs_series in response.results:
                path = f"{current_path}/{abs_series.id_}"
                items.append(
                    BrowseFolder(
                        item_id=abs_series.id_,
                        name=abs_series.name,
                        provider=self.lookup_key,
                        path=path,
                    )
                )

        return items

    async def _browse_collections(
        self, current_path: str, library_id: str
    ) -> Sequence[MediaItemType]:
        items = []
        async for response in self._client.get_library_collections(library_id=library_id):
            if not response.results:
                break
            for abs_collection in response.results:
                path = f"{current_path}/{abs_collection.id_}"
                items.append(
                    BrowseFolder(
                        item_id=abs_collection.id_,
                        name=abs_collection.name,
                        provider=self.lookup_key,
                        path=path,
                    )
                )
        return items

    async def _browse_books(self, library_id: str) -> Sequence[MediaItemType]:
        items = []
        async for response in self._client.get_library_items(library_id=library_id):
            if not response.results:
                break
            for abs_book in response.results:
                if not isinstance(abs_book, AbsLibraryItemMinifiedBook):
                    raise TypeError("Unexpected type of book.")
                mass_item = await self.mass.music.get_library_item_by_prov_id(
                    media_type=MediaType.AUDIOBOOK,
                    item_id=abs_book.id_,
                    provider_instance_id_or_domain=self.instance_id,
                )
                if mass_item is not None:
                    items.append(mass_item)
        return items

    async def _browse_author_books(
        self, current_path: str, author_id: str
    ) -> Sequence[MediaItemType]:
        items: list[MediaItemType] = []

        abs_author = await self._client.get_author(
            author_id=author_id, include_items=True, include_series=True
        )
        if not isinstance(abs_author, AbsAuthorWithItemsAndSeries):
            raise TypeError("Unexpected type of author.")

        book_ids = {x.id_ for x in abs_author.library_items}
        series_book_ids = set()

        for series in abs_author.series:
            series_book_ids.update([x.id_ for x in series.items])
            path = f"{current_path}/{series.id_}"
            items.append(
                BrowseFolder(
                    item_id=series.id_,
                    name=f"{series.name} ({AbsBrowseItemsBook.SERIES})",
                    provider=self.lookup_key,
                    path=path,
                )
            )
        book_ids = book_ids.difference(series_book_ids)
        for book_id in book_ids:
            mass_item = await self.mass.music.get_library_item_by_prov_id(
                media_type=MediaType.AUDIOBOOK,
                item_id=book_id,
                provider_instance_id_or_domain=self.instance_id,
            )
            if mass_item is not None:
                items.append(mass_item)

        return items

    async def _browse_series_books(self, series_id: str) -> Sequence[MediaItemType]:
        items = []

        abs_series = await self._client.get_series(series_id=series_id, include_progress=True)
        if not isinstance(abs_series, AbsSeriesWithProgress):
            raise TypeError("Unexpected series type.")

        for book_id in abs_series.progress.library_item_ids:
            # these are sorted in abs by sequence
            mass_item = await self.mass.music.get_library_item_by_prov_id(
                media_type=MediaType.AUDIOBOOK,
                item_id=book_id,
                provider_instance_id_or_domain=self.instance_id,
            )
            if mass_item is not None:
                items.append(mass_item)

        return items

    async def _browse_collection_books(self, collection_id: str) -> Sequence[MediaItemType]:
        items = []
        abs_collection = await self._client.get_collection(collection_id=collection_id)
        for book in abs_collection.books:
            mass_item = await self.mass.music.get_library_item_by_prov_id(
                media_type=MediaType.AUDIOBOOK,
                item_id=book.id_,
                provider_instance_id_or_domain=self.instance_id,
            )
            if mass_item is not None:
                items.append(mass_item)
        return items
