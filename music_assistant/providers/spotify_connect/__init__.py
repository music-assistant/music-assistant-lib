"""
Spotify Connect plugin for Music Assistant.

We tie a single player to a single Spotify Connect daemon.
The provider has multi instance support,
so multiple players can be linked to multiple Spotify Connect daemons.
"""

from __future__ import annotations

import asyncio
import pathlib
from collections.abc import Callable
from typing import TYPE_CHECKING, cast

from aiohttp.web import Response
from music_assistant_models.config_entries import ConfigEntry, ConfigValueOption
from music_assistant_models.enums import (
    ConfigEntryType,
    ContentType,
    EventType,
    MediaType,
    ProviderFeature,
    QueueOption,
    StreamType,
)
from music_assistant_models.errors import MediaNotFoundError
from music_assistant_models.media_items import AudioFormat, PluginSource, ProviderMapping
from music_assistant_models.streamdetails import StreamDetails

from music_assistant.helpers.process import AsyncProcess
from music_assistant.models.music_provider import MusicProvider
from music_assistant.providers.spotify.helpers import get_librespot_binary

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from aiohttp.web import Request
    from music_assistant_models.config_entries import ConfigValueType, ProviderConfig
    from music_assistant_models.event import MassEvent
    from music_assistant_models.provider import ProviderManifest

    from music_assistant.mass import MusicAssistant
    from music_assistant.models import ProviderInstanceType

CONF_MASS_PLAYER_ID = "mass_player_id"
CONF_CUSTOM_NAME = "custom_name"
CONF_HANDOFF_MODE = "handoff_mode"
CONNECT_ITEM_ID = "spotify_connect"

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
            key=CONF_MASS_PLAYER_ID,
            type=ConfigEntryType.STRING,
            label="Connected Music Assistant Player",
            description="Select the player for which you want to enable Spotify Connect.",
            multi_value=False,
            options=tuple(
                ConfigValueOption(x.display_name, x.player_id)
                for x in mass.players.all(False, False)
            ),
            required=True,
        ),
        ConfigEntry(
            key=CONF_CUSTOM_NAME,
            type=ConfigEntryType.STRING,
            label="Name for the Spotify Connect Player",
            default_value="",
            description="Select what name should be shown in the Spotify app as speaker name. "
            "Leave blank to use the Music Assistant player's name",
            required=False,
        ),
        ConfigEntry(
            key=CONF_HANDOFF_MODE,
            type=ConfigEntryType.BOOLEAN,
            label="Enable handoff mode",
            default_value=False,
            description="The default behavior of the Spotify Connect plugin is to "
            "forward the actual Spotify Connect audio stream as-is to the player, "
            "without any intervention of Music Assistant to the stream or queue, "
            "so completely bypassing the Music Assistant Queue. The Spotify audio is "
            "basically just a live audio stream. For controlling the playback (and "
            "queue contents), you need to use the Spotify app. Also, depending on the player's "
            "buffering strategy and capabilities, the audio may not be full in sync with "
            "what is shown in the Spotify app. \n\n"
            "When enabling handoff mode, the Spotify Connect plugin will instead "
            "forward the Spotify playback request to the Music Assistant Queue, so basically "
            "the spotify app can be used to initiate playback, but then MA will take over "
            "the playback and manage the queue, the normal operating mode of MA. \n\n"
            "This mode however means that the Spotify app will not report the actual playback ",
            required=False,
        ),
    )


class SpotifyConnectProvider(MusicProvider):
    """Implementation of a Spotify Connect Plugin."""

    def __init__(
        self, mass: MusicAssistant, manifest: ProviderManifest, config: ProviderConfig
    ) -> None:
        """Initialize MusicProvider."""
        super().__init__(mass, manifest, config)
        self.mass_player_id = cast(str, self.config.get_value(CONF_MASS_PLAYER_ID))
        self._librespot_bin: str | None = None
        self._stop_called: bool = False
        self._runner_task: asyncio.Task | None = None  # type: ignore[type-arg]
        self._librespot_proc: AsyncProcess | None = None
        self._librespot_started = asyncio.Event()
        self._player_connected: bool = False
        self._on_unload_callbacks: list[Callable[..., None]] = [
            self.mass.subscribe(
                self._on_mass_player_event,
                (EventType.PLAYER_ADDED, EventType.PLAYER_REMOVED),
                id_filter=self.mass_player_id,
            ),
            self.mass.streams.register_dynamic_route(
                f"/{self.instance_id}",
                self._handle_custom_webservice,
            ),
        ]

    @property
    def supported_features(self) -> set[ProviderFeature]:
        """Return the features supported by this Provider."""
        return {ProviderFeature.AUDIO_SOURCE}

    async def handle_async_init(self) -> None:
        """Handle async initialization of the provider."""
        self._librespot_bin = await get_librespot_binary()
        self._setup_player_daemon()

    async def unload(self, is_removed: bool = False) -> None:
        """Handle close/cleanup of the provider."""
        self._stop_called = True
        if self._runner_task and not self._runner_task.done():
            self._runner_task.cancel()
        for callback in self._on_unload_callbacks:
            callback()

    async def get_sources(self) -> list[PluginSource]:
        """Get all audio sources provided by this provider."""
        # we only have passive/hidden sources so no need to supply this listing
        return []

    async def get_source(self, prov_source_id: str) -> PluginSource:
        """Get AudioSource details by id."""
        if prov_source_id != CONNECT_ITEM_ID:
            raise MediaNotFoundError(f"Invalid source id: {prov_source_id}")
        if not (player := self.mass.players.get(self.mass_player_id)):
            raise MediaNotFoundError(f"Player not found: {self.mass_player_id}")
        name = self.config.get_value(CONF_CUSTOM_NAME) or player.display_name
        return PluginSource(
            item_id=CONNECT_ITEM_ID,
            provider=self.instance_id,
            name=f"Spotify Connect: {name}",
            provider_mappings={
                ProviderMapping(
                    item_id=CONNECT_ITEM_ID,
                    provider_domain=self.domain,
                    provider_instance=self.instance_id,
                    audio_format=AudioFormat(content_type=ContentType.OGG),
                )
            },
        )

    async def get_stream_details(
        self, item_id: str, media_type: MediaType = MediaType.TRACK
    ) -> StreamDetails:
        """Return the streamdetails to stream an audiosource provided by this plugin."""
        return StreamDetails(
            item_id=CONNECT_ITEM_ID,
            provider=self.instance_id,
            audio_format=AudioFormat(
                content_type=ContentType.PCM_S16LE,
            ),
            media_type=MediaType.PLUGIN_SOURCE,
            allow_seek=False,
            can_seek=False,
            stream_type=StreamType.CUSTOM,
            extra_input_args=[],
        )

    async def get_audio_stream(
        self, streamdetails: StreamDetails, seek_position: int = 0
    ) -> AsyncGenerator[bytes, None]:
        """Return the audio stream for the provider item."""
        if not self._librespot_proc or self._librespot_proc.closed:
            raise MediaNotFoundError(f"Librespot not ready for: {streamdetails.item_id}")
        self._player_connected = True
        try:
            async for chunk in self._librespot_proc.iter_any():
                if self._librespot_proc.closed or self._stop_called:
                    break
                yield chunk
        finally:
            self._player_connected = False

    async def _librespot_runner(self) -> None:
        """Run the spotify connect daemon in a background task."""
        assert self._librespot_bin
        if not (player := self.mass.players.get(self.mass_player_id)):
            raise MediaNotFoundError(f"Player not found: {self.mass_player_id}")
        name = cast(str, self.config.get_value(CONF_CUSTOM_NAME) or player.display_name)
        self.logger.info("Starting Spotify Connect background daemon %s", name)
        try:
            args: list[str] = [
                self._librespot_bin,
                "--name",
                name,
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
            self._librespot_proc = librespot = AsyncProcess(
                args, stdout=True, stderr=True, name=f"librespot[{name}]"
            )
            await librespot.start()
            # keep reading logging from stderr until exit
            async for line in librespot.iter_stderr():
                if (
                    not self._librespot_started.is_set()
                    and "Using StdoutSink (pipe) with format: S16" in line
                ):
                    self._librespot_started.set()
                self.logger.debug(line)
                if not self._player_connected and "librespot_playback::player] Loading <" in line:
                    self._player_connected = True
                    # initiate playback by selecting the pluginsource mediaitem on the player
                    pluginsource_item = await self.get_source(CONNECT_ITEM_ID)
                    self.mass.create_task(
                        self.mass.player_queues.play_media(
                            queue_id=self.mass_player_id,
                            media=pluginsource_item,
                            option=QueueOption.REPLACE,
                        )
                    )
        except asyncio.CancelledError:
            await librespot.close(True)
        finally:
            self.logger.info("Spotify Connect background daemon stopped for %s", name)
        # auto restart if not stopped manually
        if not self._stop_called and self._librespot_started.is_set():
            self._setup_player_daemon()

    def _setup_player_daemon(self) -> None:
        """Handle setup of the spotify connect daemon for a player."""
        self._librespot_started.clear()
        self._runner_task = asyncio.create_task(self._librespot_runner())

    def _on_mass_player_event(self, event: MassEvent) -> None:
        """Handle incoming event from linked airplay player."""
        if event.object_id != self.mass_player_id:
            return
        if event.event == EventType.PLAYER_REMOVED:
            self._stop_called = True
            self.mass.create_task(self.unload())
            return
        if event.event == EventType.PLAYER_ADDED:
            self._setup_player_daemon()
            return

    async def _handle_custom_webservice(self, request: Request) -> Response:
        """Serve the multi-client flow stream audio to a player."""
        # print("handle custom webservice")
        # print(request)
        return Response()
