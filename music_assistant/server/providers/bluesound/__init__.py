"""
DEMO/TEMPLATE Player Provider for Music Assistant.

This is an empty player provider with no actual implementation.
Its meant to get started developing a new player provider for Music Assistant.

Use it as a reference to discover what methods exists and what they should return.
Also it is good to look at existing player providers to get a better understanding,
due to the fact that providers may be flexible and support different features and/or
ways to discover players on the network.

In general, the actual device communication should reside in a separate library.
You can then reference your library in the manifest in the requirements section,
which is a list of (versioned!) python modules (pip syntax) that should be installed
when the provider is selected by the user.

To add a new player provider to Music Assistant, you need to create a new folder
in the providers folder with the name of your provider (e.g. 'my_player_provider').
In that folder you should create (at least) a __init__.py file and a manifest.json file.

Optional is an icon.svg file that will be used as the icon for the provider in the UI,
but we also support that you specify a material design icon in the manifest.json file.

IMPORTANT NOTE:
We strongly recommend developing on either MacOS or Linux and start your development
environment by running the setup.sh scripts in the scripts folder of the repository.
This will create a virtual environment and install all dependencies needed for development.
See also our general DEVELOPMENT.md guide in the repository for more information.

"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, TypedDict

from pyblu import Player as BluosPlayer

# TODO fix input and presets
# from pyblu import Input, Preset
from pyblu import Status, SyncStatus
from zeroconf import ServiceStateChange

from music_assistant.common.models.config_entries import (
    CONF_ENTRY_CROSSFADE,
    CONF_ENTRY_CROSSFADE_FLOW_MODE_REQUIRED,
    CONF_ENTRY_ENFORCE_MP3_DEFAULT_ENABLED,
    CONF_ENTRY_FLOW_MODE_DEFAULT_ENABLED,
    CONF_ENTRY_HTTP_PROFILE_FORCED_2,
    ConfigEntry,
    ConfigValueType,
    # PlayerConfig,
)
from music_assistant.common.models.enums import (
    # ConfigEntryType,
    PlayerFeature,
    PlayerState,
    PlayerType,
    ProviderFeature,
)
from music_assistant.common.models.errors import PlayerCommandFailed
from music_assistant.common.models.player import DeviceInfo, Player, PlayerMedia
from music_assistant.server.helpers.util import (
    get_port_from_zeroconf,
    get_primary_ip_address_from_zeroconf,
)
from music_assistant.server.models.player_provider import PlayerProvider

if TYPE_CHECKING:
    from zeroconf.asyncio import AsyncServiceInfo

    from music_assistant.common.models.config_entries import ProviderConfig
    from music_assistant.common.models.provider import ProviderManifest
    from music_assistant.server import MusicAssistant
    from music_assistant.server.models import ProviderInstanceType


# from music_assistant.constants import (
#     CONF_IP_ADDRESS,
#     CONF_PORT,
#     VERBOSE_LOG_LEVEL,
# )

PLAYER_FEATURES_BASE = {
    PlayerFeature.SYNC,
    PlayerFeature.VOLUME_MUTE,
    PlayerFeature.ENQUEUE_NEXT,
    PlayerFeature.PAUSE,
}

PLAYBACK_STATE_MAP = {
    "play": PlayerState.PLAYING,
    "stream": PlayerState.PLAYING,
    "stop": PlayerState.IDLE,
    "pause": PlayerState.PAUSED,
    "connecting": PlayerState.IDLE,
}

SOURCE_LINE_IN = "line_in"
SOURCE_AIRPLAY = "airplay"


async def setup(
    mass: MusicAssistant, manifest: ProviderManifest, config: ProviderConfig
) -> ProviderInstanceType:
    """Initialize provider(instance) with given configuration."""
    # setup is called when the user wants to setup a new provider instance.
    # you are free to do any preflight checks here and but you must return
    #  an instance of the provider.
    return BluesoundPlayerProvider(mass, manifest, config)


async def get_config_entries(
    # not used yet, ruff doesn't like that
    mass: MusicAssistant,
    instance_id: str | None = None,
    action: str | None = None,
    values: dict[str, ConfigValueType] | None = None,
) -> tuple[ConfigEntry, ...]:
    """
    Return Config entries to setup bluesound provider.

    instance_id: id of an existing provider instance (None if new instance setup).
    action: [optional] action key called from config entries UI.
    values: the (intermediate) raw values for config entries sent with the action.
    """
    # mass.logger.debug("loading entries")
    # Config Entries are used to configure the Player Provider if needed.
    # See the models of ConfigEntry and ConfigValueType for more information what is supported.
    # The ConfigEntry is a dataclass that represents a single configuration entry.
    # The ConfigValueType is an Enum that represents the type of value that
    # can be stored in a ConfigEntry.
    # If your provider does not need any configuration, you can return an empty tuple.
    # ruff: noqa: ARG001
    return ()


class BluesoundDiscoveryInfo(TypedDict):
    """Template for MDNS discovery info."""

    _objectType: str
    ip_address: str
    port: str
    mac: str
    model: str
    zs: bool


class BluesoundPlayer:
    """Holds the details of the (discovered) BluOS player."""

    def __init__(
        self,
        prov: BluesoundPlayerProvider,
        player_id: str,
        discovery_info: BluesoundDiscoveryInfo,
        ip_address: str,
        port: int,
    ) -> None:
        """Initialize the BluOS Player."""
        self.port = port
        self.prov = prov
        self.mass = prov.mass
        self.player_id = player_id
        self.discovery_info = discovery_info
        self.ip_address = ip_address
        self.logger = prov.logger.getChild(player_id)
        self.connected: bool = True
        self.client = BluosPlayer(self.ip_address, self.port, self.mass.http_session)
        self.sync_status = SyncStatus
        self.status = Status
        self.mass_player: Player | None = None
        self._listen_task: asyncio.Task | None = None

    async def disconnect(self) -> None:
        """Disconnect the client and cleanup."""
        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
        if self.client:
            await self.client.close()
        self.connected = False
        self.logger.debug("Disconnected from player API")

    async def update_attributes(self, player_id: str) -> None:
        """Update the player attributes."""
        self.logger.debug("Update attributes")

        self.sync_status = await self.client.sync_status()
        self.status = await self.client.status()

        if not self.mass_player:
            return
        if self.sync_status.volume == -1:
            self.mass_player.volume_level = 100
        else:
            self.mass_player.volume_level = self.sync_status.volume
        self.mass_player.volume_muted = self.status.mute

        # TODO check pair status
        # active_group = sync_status_result.group

        # self.logger.debug(sync_status_result.slaves)

        # TODO fix pairing

        if self.sync_status.master is None:
            # self.logger.debug("Is Master")

            # Ensure 'slaves' exists and is not empty before proceeding
            if self.sync_status.slaves:
                self.mass_player.group_childs = (
                    self.sync_status.slaves if len(self.sync_status.slaves) > 1 else set()
                )
                self.mass_player.synced_to = None

            # Example of retrieving the client's status name
            # print(sync_status_result.name)

            # Get the container's status and determine the active source
            # container = status_result
            # if container:
            #     if container.get("type") == "linein":
            #         self.mass_player.active_source = SOURCE_LINE_IN
            #     elif container.get("type") == "linein.airplay":
            #         self.mass_player.active_source = SOURCE_AIRPLAY
            #     else:
            #         self.mass_player.active_source = None
            # self.logger.debug("seconds")
            # self.logger.debug(status_result.seconds)

            if self.status.state:
                # test variables:
                # track_images = status_result.image
                # track_image_url = status_result.image
                # track_duration_millis = status_result.total_seconds/1000
                self.mass_player.current_media = PlayerMedia(
                    uri=self.status.stream_url,
                    title=self.status.name,
                    artist=self.status.artist,
                    album=self.status.album,
                    # duration=self.status.total_seconds / 1000,
                    image_url=self.status.image,
                )

            # TODO fix sync and multiple players
            # elif container.get("name") and container.get("id"):
            #     images = self.status.image
            #     image_url = self.status.image
            #     self.mass_player.current_media = PlayerMedia(
            #         uri=self.status.stream_url,
            #         title=self.status.name,
            #         image_url=self.status.image,
            #     )
            else:
                self.mass_player.current_media = None

        else:
            self.mass_player.group_childs = set()
            self.mass_player.synced_to = self.sync_status.master
            self.mass_player.active_source = self.sync_status.master
        # self.mass_player.state = PLAYBACK_STATE_MAP[active_group.playback_state]

        self.mass_player.elapsed_time = self.status.seconds
        self.mass_player.elapsed_time_last_updated = time.time()
        self.mass.players.update(self.player_id)
        self.logger.debug(self.status.seconds)
        self.mass_player.state = PLAYBACK_STATE_MAP[self.status.state]
        self.mass_player.can_sync_with = (
            tuple(x for x in self.prov.bluos_players if x != self.player_id),
        )


class BluesoundPlayerProvider(PlayerProvider):
    """Bluos compatible player provider, providing support for bluesound speaker."""

    bluos_players: dict[str, BluesoundPlayer]

    def __init__(self, *args, **kwargs):
        """Initialize the BluOS Provider."""
        super().__init__(*args, **kwargs)
        self.bluos_players = {}

    @property
    def supported_features(self) -> tuple[ProviderFeature, ...]:
        """Return the features supported by this Provider."""
        # MANDATORY
        # you should return a tuple of provider-level features
        # here that your player provider supports or an empty tuple if none.
        # for example 'ProviderFeature.SYNC_PLAYERS' if you can sync players.
        return (
            ProviderFeature.SYNC_PLAYERS,
            #  ProviderFeature.PLAYER_GROUP_CREATE
        )

    async def handle_async_init(self) -> None:
        """Handle async initialization of the provider."""
        self.bluos_players: dict[str, BluosPlayer] = {}

    async def loaded_in_mass(self) -> None:
        """Call after the provider has been loaded."""

        # OPTIONAL
        # this is an optional method that you can implement if
        # relevant or leave out completely if not needed.
        # it will be called after the provider has been fully loaded into Music Assistant.
        # you can use this for instance to trigger custom (non-mdns) discovery of players
        # or any other logic that needs to run after the provider is fully loaded.

    async def unload(self) -> None:
        """
        Handle unload/close of the provider.

        Called when provider is deregistered (e.g. MA exiting or config reloading).
        """
        # OPTIONAL
        # this is an optional method that you can implement if
        # relevant or leave out completely if not needed.
        # it will be called when the provider is unloaded from Music Assistant.
        # this means also when the provider is getting reloaded

    async def on_mdns_service_state_change(
        self, name: str, state_change: ServiceStateChange, info: AsyncServiceInfo | None
    ) -> None:
        """Handle MDNS service state callback."""
        # MANDATORY IF YOU WANT TO USE MDNS DISCOVERY
        # OPTIONAL if you dont use mdns for discovery of players
        # If you specify a mdns service type in the manifest.json, this method will be called
        # automatically on mdns changes for the specified service type.

        # If no mdns service type is specified, this method is omitted and you
        # can completely remove it from your provider implementation.

        # NOTE: If you do not use mdns for discovery of players on the network,
        # you must implement your own discovery mechanism and logic to add new players
        # and update them on state changes when needed.
        # Below is a bit of example implementation but we advise to look at existing
        # player providers for more inspiration.

        name = name.split(".", 1)[0]
        self.player_id = info.decoded_properties["mac"]  # this is just an example!
        # handle removed player

        if state_change == ServiceStateChange.Removed:
            # check if the player manager has an existing entry for this player
            if mass_player := self.mass.players.get(self.player_id):
                # the player has become unavailable
                self.logger.debug("Player offline: %s", mass_player.display_name)
                mass_player.available = False
                self.mass.players.update(self.player_id)
            return
        # handle update for existing device
        # (state change is either updated or added)
        # check if we have an existing player in the player manager
        # note that you can use this point to update the player connection info
        # if that changed (e.g. ip address)
        if bluos_player := self.bluos_players.get(self.player_id):
            if mass_player := self.mass.players.get(self.player_id):
                # existing player found in the player manager,
                # this is an existing player that has been updated/reconnected
                # or simply a re-announcement on mdns.
                cur_address = get_primary_ip_address_from_zeroconf(info)
                cur_port = get_port_from_zeroconf(info)
                if cur_address and cur_address != mass_player.device_info.address:
                    self.logger.debug(
                        "Address updated to %s for player %s", cur_address, mass_player.display_name
                    )
                    bluos_player.ip_address = cur_address
                    bluos_player.port = cur_port
                    mass_player.device_info = DeviceInfo(
                        model=mass_player.device_info.model,
                        manufacturer=mass_player.device_info.manufacturer,
                        address=str(cur_address),
                    )
                if not mass_player.available:
                    # if the player was marked offline and you now receive an mdns update
                    # it means the player is back online and we should try to connect to it
                    self.logger.debug("Player back online: %s", mass_player.display_name)
                    # you can try to connect to the player here if needed
                    bluos_player.client.sync()
                    mass_player.available = True
                # inform the player manager of any changes to the player object
                # note that you would normally call this from some other callback from
                # the player's native api/library which informs you of changes in the player state.
                # as a last resort you can also choose to let the player manager
                # poll the player for state changes
                bluos_player.discovery_info = info
                self.mass.players.update(self.player_id)
                return
            # handle new player
        cur_address = get_primary_ip_address_from_zeroconf(info)
        cur_port = get_port_from_zeroconf(info)
        self.logger.debug("Discovered device %s on %s", name, cur_address)
        # your own connection logic will probably be implemented here where
        # you connect to the player etc. using your device/provider specific library.

        # Instantiate the MA Player object and register it with the player manager

        # register the player with the player manager

        self.bluos_players[self.player_id] = bluos_player = BluesoundPlayer(
            self, self.player_id, discovery_info=info, ip_address=cur_address, port=cur_port
        )
        # self.logger.debug(name)
        bluos_player.mass_player = mass_player = Player(
            player_id=self.player_id,
            provider=self.instance_id,
            type=PlayerType.PLAYER,
            name=name,
            available=True,
            powered=True,
            device_info=DeviceInfo(
                model="BluOS speaker",
                manufacturer="Bluesound",
                address=cur_address,
            ),
            # set the supported features for this player only with
            # the ones the player actually supports
            supported_features=(
                # PlayerFeature.POWER,  # if the player can be turned on/off
                PlayerFeature.VOLUME_SET,
                PlayerFeature.VOLUME_MUTE,
                PlayerFeature.PLAY_ANNOUNCEMENT,  # see play_announcement method
                PlayerFeature.ENQUEUE_NEXT,  # see play_media/enqueue_next_media methods
                PlayerFeature.PAUSE,
                PlayerFeature.SEEK,
            ),
            needs_poll=True,
            poll_interval=1,
        )
        self.mass.players.register(mass_player)
        # sync_status_result = await self.client.sync_status()
        # status_result = await self.client.status()
        await bluos_player.update_attributes()

        # once the player is registered, you can either instruct the player manager to
        # poll the player for state changes or you can implement your own logic to
        # listen for state changes from the player and update the player object accordingly.
        # in any case, you need to call the update method on the player manager:
        self.mass.players.update(self.player_id)

    async def get_player_config_entries(
        self,
        player_id: str,
    ) -> tuple[ConfigEntry, ...]:
        """Return Config Entries for the given player."""
        base_entries = await super().get_player_config_entries(self.player_id)
        if not self.bluos_players.get(self.player_id):
            # TODO fix player entries
            # if not (bluos_player := self.bluos_players.get(self.player_id)):
            #     # most probably a syncgroup
            return (*base_entries, CONF_ENTRY_CROSSFADE)
        return (
            *base_entries,
            CONF_ENTRY_HTTP_PROFILE_FORCED_2,
            CONF_ENTRY_CROSSFADE,
            CONF_ENTRY_CROSSFADE_FLOW_MODE_REQUIRED,
            CONF_ENTRY_ENFORCE_MP3_DEFAULT_ENABLED,
            CONF_ENTRY_FLOW_MODE_DEFAULT_ENABLED,
        )

    async def cmd_stop(self, player_id: str) -> None:
        """Send STOP command to given player."""
        if bluos_player := self.bluos_players[player_id]:
            await bluos_player.client.stop()
        # MANDATORY
        # this method is mandatory and should be implemented.
        # this method should send a stop command to the given player.

    async def cmd_play(self, player_id: str) -> None:
        """Send PLAY command to given player."""
        if bluos_player := self.bluos_players[player_id]:
            await bluos_player.client.play()

    async def cmd_pause(self, player_id: str) -> None:
        """Send PAUSE command to given player."""
        if bluos_player := self.bluos_players[player_id]:
            await bluos_player.client.pause()

    async def cmd_volume_set(self, player_id: str, volume_level: int) -> None:
        """Send VOLUME_SET command to given player."""
        self.logger.debug(volume_level)
        if bluos_player := self.bluos_players[player_id]:
            await bluos_player.client.volume(level=volume_level)
            mass_player = self.mass.players.get(self.player_id)
            # Optimistic state, reduces interface lag
            mass_player.volume_level = volume_level

    async def cmd_volume_mute(self, player_id: str, muted: bool) -> None:
        """Send VOLUME MUTE command to given player."""
        if bluos_player := self.bluos_players[player_id]:
            await bluos_player.client.volume(mute=muted)
            # Optimistic state, reduces interface lag
            mass_player = self.mass.players.get(self.player_id)
            mass_player.volume_mute = muted

    async def cmd_seek(self, player_id: str, position: int) -> None:
        """Handle SEEK command for given queue.

        - player_id: player_id of the player to handle the command.
        - position: position in seconds to seek to in the current playing item.
        """
        if bluos_player := self.bluos_players[player_id]:
            await bluos_player.client.play(seek=position)

        # OPTIONAL - required only if you specified PlayerFeature.SEEK
        # this method should handle the seek command for the given player.
        # the position is the position in seconds to seek to in the current playing item.

    async def play_media(
        self, player_id: str, media: PlayerMedia, timeout: float | None = None
    ) -> None:
        """Handle PLAY MEDIA on given player using the provided URL."""
        # if status_result.state:
        #     # this should be already handled by the player manager, but just in case...
        #     msg = (
        #         f"Player {mass_player.display_name} cannot "
        #         "accept play_media command, it is synced to another player."
        #     )
        #     raise PlayerCommandFailed(msg)

        # Prepare the URL to play
        # media_url = f"{self.mass.streams.base_url}/play/{media.queue_id}"

        # Use the play_url method to start playback
        if bluos_player := self.bluos_players[player_id]:
            playback_state = await bluos_player.client.play_url(media.uri, timeout=timeout)

        # Optionally, handle the playback_state or additional logic here
        if playback_state != "playing":
            raise PlayerCommandFailed("Failed to start playback.")

    async def enqueue_next_media(self, player_id: str, media: PlayerMedia) -> None:
        """
        Handle enqueuing of the next (queue) item on the player.

        Only called if the player supports PlayerFeature.ENQUE_NEXT.
        Called about 1 second after a new track started playing.
        Called about 15 seconds before the end of the current track.

        A PlayerProvider implementation is in itself responsible for handling this
        so that the queue items keep playing until its empty or the player stopped.

        This will NOT be called if the end of the queue is reached (and repeat disabled).
        This will NOT be called if the player is using flow mode to playback the queue.
        """
        # OPTIONAL - required only if you specified PlayerFeature.ENQUEUE_NEXT
        # this method should handle the enqueuing of the next queue item on the player.

    async def cmd_sync(self, player_id: str, target_player: str) -> None:
        """Handle SYNC command for given player.

        Join/add the given player(id) to the given (master) player/sync group.

            - player_id: player_id of the player to handle the command.
            - target_player: player_id of the syncgroup master or group player.
        """
        # OPTIONAL - required only if you specified ProviderFeature.SYNC_PLAYERS
        # this method should handle the sync command for the given player.
        # you should join the given player to the target_player/syncgroup.

    async def cmd_unsync(self, player_id: str) -> None:
        """Handle UNSYNC command for given player.

        Remove the given player from any syncgroups it currently is synced to.

            - player_id: player_id of the player to handle the command.
        """
        if bluos_player := self.bluos_players[player_id]:
            await bluos_player.client.player.leave_group()

    async def play_announcement(
        self, player_id: str, announcement: PlayerMedia, volume_level: int | None = None
    ) -> None:
        """Send announcement to player."""
        if bluos_player := self.bluos_players[player_id]:
            await bluos_player.client.Input(announcement.uri, volume_level)

    async def poll_player(self, player_id: str) -> None:
        """Poll player for state updates."""
        if bluos_player := self.bluos_players[player_id]:
            await bluos_player.update_attributes()
