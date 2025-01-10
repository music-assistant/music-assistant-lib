"""Spotify Connect plugin for Music Assistant."""

from __future__ import annotations

import asyncio
import pathlib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, cast

from music_assistant_models.config_entries import ConfigEntry, ConfigValueOption
from music_assistant_models.enums import (
    ConfigEntryType,
    ContentType,
    MediaType,
    ProviderFeature,
    StreamType,
)
from music_assistant_models.errors import MediaNotFoundError
from music_assistant_models.media_items import AudioFormat
from music_assistant_models.player import PlayerMedia, PlayerSource
from music_assistant_models.streamdetails import StreamDetails

from music_assistant.helpers.process import AsyncProcess
from music_assistant.models.music_provider import MusicProvider
from music_assistant.providers.spotify.helpers import get_librespot_binary

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from music_assistant_models.config_entries import ConfigValueType, ProviderConfig
    from music_assistant_models.provider import ProviderManifest

    from music_assistant.mass import MusicAssistant
    from music_assistant.models import ProviderInstanceType

CONF_ENABLED_PLAYERS = "enabled_players"

EVENTS_SCRIPT = pathlib.Path(__file__).parent.resolve().joinpath("events.py")


async def setup(
    mass: MusicAssistant, manifest: ProviderManifest, config: ProviderConfig
) -> ProviderInstanceType:
    """Initialize provider(instance) with given configuration."""
    return SpotifyConnectProvider(mass, manifest, config)


async def get_config_entries(
    mass: MusicAssistant,
    instance_id: str | None = None,  # noqa: ARG001
    action: str | None = None,  # noqa: ARG001
    values: dict[str, ConfigValueType] | None = None,  # noqa: ARG001
) -> tuple[ConfigEntry, ...]:
    """
    Return Config entries to setup this provider.

    instance_id: id of an existing provider instance (None if new instance setup).
    action: [optional] action key called from config entries UI.
    values: the (intermediate) raw values for config entries sent with the action.
    """
    return (
        ConfigEntry(
            key=CONF_ENABLED_PLAYERS,
            type=ConfigEntryType.STRING,
            label="Enabled players",
            default_value=[],
            description="Select all players for which you want to enable Spotify Connect.",
            multi_value=True,
            options=tuple(
                ConfigValueOption(x.display_name, x.player_id)
                for x in mass.players.all(False, False)
            ),
        ),
    )


@dataclass
class SpotifyConnectDaemon:
    """Class to hold details for a single Spotify Connect Daemon."""

    player_id: str
    name: str
    source_details: PlayerSource
    task: asyncio.Task | None = None  # type: ignore[type-arg]
    process: AsyncProcess | None = None
    started: asyncio.Event = field(default_factory=asyncio.Event)
    player_connected: bool = False


class SpotifyConnectProvider(MusicProvider):
    """Implementation of a Spotify Connect Plugin."""

    _librespot_bin: str | None = None
    _daemons: dict[str, SpotifyConnectDaemon] | None = None
    _stop_called: bool = False

    @property
    def supported_features(self) -> set[ProviderFeature]:
        """Return the features supported by this Provider."""
        return {ProviderFeature.AUDIO_SOURCE}

    async def handle_async_init(self) -> None:
        """Handle async initialization of the provider."""
        self._librespot_bin = await get_librespot_binary()
        enabled_players = cast(list[str], self.config.get_value(CONF_ENABLED_PLAYERS))
        self._daemons = {}
        for player_id in enabled_players:
            if not (player := self.mass.players.get(player_id)):
                continue
            self._daemons[player_id] = daemon_details = SpotifyConnectDaemon(
                player_id=player_id,
                name=player.display_name,
                source_details=PlayerSource(
                    id=player_id,
                    name="Spotify Connect",
                    passive=True,
                    metadata=PlayerMedia(uri=player_id),
                ),
            )
            daemon_details.task = asyncio.create_task(self._librespot_runner(daemon_details))

    async def unload(self, is_removed: bool = False) -> None:
        """Handle close/cleanup of the provider."""
        self._stop_called = True
        if self._daemons is None:
            return
        for daemon in self._daemons.values():
            if daemon.task:
                daemon.task.cancel()

    async def get_sources(self) -> list[PlayerSource]:
        """Get all audio sources provided by this provider."""
        # we only have passive/hidden sources so no need to supply this listing
        return []

    async def get_source(self, prov_source_id: str) -> PlayerSource:
        """Get AudioSource details by id."""
        assert self._daemons
        if prov_source_id not in self._daemons:
            raise MediaNotFoundError(f"Invalid source id: {prov_source_id}")
        return self._daemons[prov_source_id].source_details

    async def get_stream_details(
        self, item_id: str, media_type: MediaType = MediaType.OTHER
    ) -> StreamDetails:
        """Return the streamdetails to stream a naudiosource provided by this plugin."""
        return StreamDetails(
            item_id=item_id,
            provider=self.instance_id,
            audio_format=AudioFormat(
                content_type=ContentType.PCM_S16LE,
            ),
            media_type=MediaType.OTHER,
            can_seek=False,
            stream_type=StreamType.CUSTOM,
        )

    async def get_audio_stream(
        self, streamdetails: StreamDetails, seek_position: int = 0
    ) -> AsyncGenerator[bytes, None]:
        """Return the audio stream for the provider item."""
        assert self._daemons
        if not (daemon := self._daemons.get(streamdetails.item_id)):
            raise MediaNotFoundError(f"Invalid source id: {streamdetails.item_id}")
        if not (librespot := daemon.process):
            raise MediaNotFoundError(f"Librespot not ready for: {streamdetails.item_id}")
        daemon.player_connected = True
        try:
            async for chunk in librespot.iter_any():
                if librespot.closed or self._stop_called:
                    break
                yield chunk
        finally:
            self._daemons[streamdetails.item_id].player_connected = False

    async def _librespot_runner(self, daemon_details: SpotifyConnectDaemon) -> None:
        """Run the spotify connect daemon in a background task."""
        if daemon_details.started.is_set():
            raise RuntimeError("Daemon is already started!")
        assert self._librespot_bin
        self.logger.info("Starting Spotify Connect background daemon for %s", daemon_details.name)
        plugin_uri = f"{self.instance_id}://plugin_source/{daemon_details.player_id}"
        try:
            args = [
                self._librespot_bin,
                "--name",
                daemon_details.name,
                "--bitrate",
                "320",
                "--backend",
                "pipe",
                "--dither",
                "none",
                # "--verbose",
                "--volume-ctrl",
                "fixed",
            ]
            daemon_details.process = librespot = AsyncProcess(
                args, stdout=True, stderr=True, name=f"librespot[{daemon_details.name}]"
            )
            await librespot.start()
            # keep reading logging from stderr until exit
            async for line in librespot.iter_stderr():
                if (
                    not daemon_details.started.is_set()
                    and "Using StdoutSink (pipe) with format: S16" in line
                ):
                    daemon_details.started.set()
                self.logger.debug(line)
                if (
                    not daemon_details.player_connected
                    and "librespot_playback::player] Loading <" in line
                ):
                    daemon_details.player_connected = True
                    self.mass.create_task(
                        self.mass.players.select_source(daemon_details.player_id, plugin_uri)
                    )
        except asyncio.CancelledError:
            await librespot.close(True)
        finally:
            self.logger.info(
                "Spotify Connect background daemon stopped for %s", daemon_details.name
            )
        # auto restart if not stopped manually
        if not self._stop_called and daemon_details.started.is_set():
            daemon_details.started.clear()
            daemon_details.task = asyncio.create_task(self._librespot_runner(daemon_details))
