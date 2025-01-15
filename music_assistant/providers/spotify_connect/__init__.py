"""
Spotify Connect plugin for Music Assistant.

We tie a single player to a single Spotify Connect daemon.
The provider has multi instance support,
so multiple players can be linked to multiple Spotify Connect daemons.
"""

from __future__ import annotations

import asyncio
import os
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
from music_assistant_models.streamdetails import LivestreamMetadata, StreamDetails

from music_assistant.constants import CONF_ENTRY_WARN_PREVIEW
from music_assistant.helpers.audio import get_chunksize
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
        CONF_ENTRY_WARN_PREVIEW,
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
        # ConfigEntry(
        #     key=CONF_HANDOFF_MODE,
        #     type=ConfigEntryType.BOOLEAN,
        #     label="Enable handoff mode",
        #     default_value=False,
        #     description="The default behavior of the Spotify Connect plugin is to "
        #     "forward the actual Spotify Connect audio stream as-is to the player. "
        #     "The Spotify audio is basically just a live audio stream. \n\n"
        #     "For controlling the playback (and queue contents), "
        #     "you need to use the Spotify app. Also, depending on the player's "
        #     "buffering strategy and capabilities, the audio may not be fully in sync with "
        #     "what is shown in the Spotify app. \n\n"
        #     "When enabling handoff mode, the Spotify Connect plugin will instead "
        #     "forward the Spotify playback request to the Music Assistant Queue, so basically "
        #     "the spotify app can be used to initiate playback, but then MA will take over "
        #     "the playback and manage the queue, the normal operating mode of MA. \n\n"
        #     "This mode however means that the Spotify app will not report the actual playback ",
        #     required=False,
        # ),
    )


class SpotifyConnectProvider(MusicProvider):
    """Implementation of a Spotify Connect Plugin."""

    def __init__(
        self, mass: MusicAssistant, manifest: ProviderManifest, config: ProviderConfig
    ) -> None:
        """Initialize MusicProvider."""
        super().__init__(mass, manifest, config)
        self.mass_player_id = cast(str, self.config.get_value(CONF_MASS_PLAYER_ID))
        self.cache_dir = os.path.join(self.mass.cache_path, self.instance_id)
        self._librespot_bin: str | None = None
        self._stop_called: bool = False
        self._runner_task: asyncio.Task | None = None  # type: ignore[type-arg]
        self._librespot_proc: AsyncProcess | None = None
        self._librespot_started = asyncio.Event()
        self._player_connected: bool = False
        self._current_streamdetails: StreamDetails | None = None
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

    @property
    def name(self) -> str:
        """Return (custom) friendly name for this provider instance."""
        if custom_name := cast(str, self.config.get_value(CONF_CUSTOM_NAME)):
            return f"{self.manifest.name}: {custom_name}"
        if player := self.mass.players.get(self.mass_player_id):
            return f"{self.manifest.name}: {player.display_name}"
        return super().name

    async def handle_async_init(self) -> None:
        """Handle async initialization of the provider."""
        self._librespot_bin = await get_librespot_binary()
        if self.mass.players.get(self.mass_player_id):
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
        return PluginSource(
            item_id=CONNECT_ITEM_ID,
            provider=self.instance_id,
            name="Spotify Connect",
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
        self._current_streamdetails = streamdetails = StreamDetails(
            item_id=CONNECT_ITEM_ID,
            provider=self.instance_id,
            audio_format=AudioFormat(
                content_type=ContentType.PCM_S16LE,
            ),
            media_type=MediaType.PLUGIN_SOURCE,
            allow_seek=False,
            can_seek=False,
            stream_type=StreamType.CUSTOM,
            extra_input_args=["-readrate", "1.0", "-readrate_initial_burst", "10"],
        )
        return streamdetails

    async def get_audio_stream(
        self, streamdetails: StreamDetails, seek_position: int = 0
    ) -> AsyncGenerator[bytes, None]:
        """Return the audio stream for the provider item."""
        if not self._librespot_proc or self._librespot_proc.closed:
            raise MediaNotFoundError(f"Librespot not ready for: {streamdetails.item_id}")
        self._player_connected = True
        chunksize = get_chunksize(streamdetails.audio_format)
        try:
            async for chunk in self._librespot_proc.iter_chunked(chunksize):
                if self._librespot_proc.closed or self._stop_called:
                    break
                yield chunk
        finally:
            self._player_connected = False
            await asyncio.sleep(2)
            if not self._player_connected:
                # handle situation where the stream is disconnected from the MA player
                # easiest way to unmark this librespot instance as active player is to close it
                await self._librespot_proc.close(True)

    async def _librespot_runner(self) -> None:
        """Run the spotify connect daemon in a background task."""
        assert self._librespot_bin
        if not (player := self.mass.players.get(self.mass_player_id)):
            raise MediaNotFoundError(f"Player not found: {self.mass_player_id}")
        name = cast(str, self.config.get_value(CONF_CUSTOM_NAME) or player.display_name)
        self.logger.info("Starting Spotify Connect background daemon %s", name)
        os.environ["MASS_CALLBACK"] = f"{self.mass.streams.base_url}/{self.instance_id}"
        try:
            args: list[str] = [
                self._librespot_bin,
                "--name",
                name,
                "--cache",
                self.cache_dir,
                "--disable-audio-cache",
                "--bitrate",
                "320",
                "--backend",
                "pipe",
                "--dither",
                "none",
                # disable volume control
                "--mixer",
                "softvol",
                "--volume-ctrl",
                "fixed",
                "--initial-volume",
                "100",
                # forward events to the events script
                "--onevent",
                str(EVENTS_SCRIPT),
                "--emit-sink-events",
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
                if "error sending packet Os" in line:
                    continue
                if "dropping truncated packet" in line:
                    continue
                if "couldn't parse packet from " in line:
                    continue
                self.logger.debug(line)
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
        """Handle incoming requests on the custom webservice."""
        json_data = await request.json()
        self.logger.debug("Received metadata on webservice: \n%s", json_data)

        # handle session connected event
        # this player has become the active spotify connect player
        # we need to start the playback
        if not self._player_connected and json_data.get("event") in (
            "session_connected",
            "play_request_id_changed",
        ):
            # initiate playback by selecting the pluginsource mediaitem on the player
            pluginsource_item = await self.get_source(CONNECT_ITEM_ID)
            self.mass.create_task(
                self.mass.player_queues.play_media(
                    queue_id=self.mass_player_id,
                    media=pluginsource_item,
                    option=QueueOption.REPLACE,
                )
            )

        if self._current_streamdetails:
            # parse metadata fields
            if "common_metadata_fields" in json_data:
                title = json_data["common_metadata_fields"].get("name", "Unknown")
                if artists := json_data.get("track_metadata_fields", {}).get("artists"):
                    artist = artists[0]
                else:
                    artist = "Unknown"
                if images := json_data["common_metadata_fields"].get("covers"):
                    image_url = images[0]
                else:
                    image_url = None
                self._current_streamdetails.stream_metadata = LivestreamMetadata(
                    title=title, artist=artist, image_url=image_url
                )

        return Response()
