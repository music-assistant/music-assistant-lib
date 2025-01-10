"""All constants for Music Assistant."""

import pathlib
from typing import Final

from music_assistant_models.config_entries import ConfigEntry, ConfigValueOption
from music_assistant_models.enums import ConfigEntryType

API_SCHEMA_VERSION: Final[int] = 26
MIN_SCHEMA_VERSION: Final[int] = 24


MASS_LOGGER_NAME: Final[str] = "music_assistant"

UNKNOWN_ARTIST: Final[str] = "[unknown]"
UNKNOWN_ARTIST_ID_MBID: Final[str] = "125ec42a-7229-4250-afc5-e057484327fe"
VARIOUS_ARTISTS_NAME: Final[str] = "Various Artists"
VARIOUS_ARTISTS_MBID: Final[str] = "89ad4ac3-39f7-470e-963a-56509c546377"


RESOURCES_DIR: Final[pathlib.Path] = (
    pathlib.Path(__file__).parent.resolve().joinpath("helpers/resources")
)

ANNOUNCE_ALERT_FILE: Final[str] = str(RESOURCES_DIR.joinpath("announce.mp3"))
SILENCE_FILE: Final[str] = str(RESOURCES_DIR.joinpath("silence.mp3"))
SILENCE_FILE_LONG: Final[str] = str(RESOURCES_DIR.joinpath("silence_long.ogg"))
VARIOUS_ARTISTS_FANART: Final[str] = str(RESOURCES_DIR.joinpath("fallback_fanart.jpeg"))
MASS_LOGO: Final[str] = str(RESOURCES_DIR.joinpath("logo.png"))


# config keys
CONF_SERVER_ID: Final[str] = "server_id"
CONF_IP_ADDRESS: Final[str] = "ip_address"
CONF_PORT: Final[str] = "port"
CONF_PROVIDERS: Final[str] = "providers"
CONF_PLAYERS: Final[str] = "players"
CONF_CORE: Final[str] = "core"
CONF_PATH: Final[str] = "path"
CONF_USERNAME: Final[str] = "username"
CONF_PASSWORD: Final[str] = "password"
CONF_VOLUME_NORMALIZATION: Final[str] = "volume_normalization"
CONF_VOLUME_NORMALIZATION_TARGET: Final[str] = "volume_normalization_target"
CONF_DEPRECATED_EQ_BASS: Final[str] = "eq_bass"
CONF_DEPRECATED_EQ_MID: Final[str] = "eq_mid"
CONF_DEPRECATED_EQ_TREBLE: Final[str] = "eq_treble"
CONF_PLAYER_DSP: Final[str] = "player_dsp"
CONF_OUTPUT_CHANNELS: Final[str] = "output_channels"
CONF_FLOW_MODE: Final[str] = "flow_mode"
CONF_LOG_LEVEL: Final[str] = "log_level"
CONF_HIDE_GROUP_CHILDS: Final[str] = "hide_group_childs"
CONF_CROSSFADE_DURATION: Final[str] = "crossfade_duration"
CONF_BIND_IP: Final[str] = "bind_ip"
CONF_BIND_PORT: Final[str] = "bind_port"
CONF_PUBLISH_IP: Final[str] = "publish_ip"
CONF_AUTO_PLAY: Final[str] = "auto_play"
CONF_CROSSFADE: Final[str] = "crossfade"
CONF_GROUP_MEMBERS: Final[str] = "group_members"
CONF_HIDE_PLAYER: Final[str] = "hide_player"
CONF_ENFORCE_MP3: Final[str] = "enforce_mp3"
CONF_SYNC_ADJUST: Final[str] = "sync_adjust"
CONF_TTS_PRE_ANNOUNCE: Final[str] = "tts_pre_announce"
CONF_ANNOUNCE_VOLUME_STRATEGY: Final[str] = "announce_volume_strategy"
CONF_ANNOUNCE_VOLUME: Final[str] = "announce_volume"
CONF_ANNOUNCE_VOLUME_MIN: Final[str] = "announce_volume_min"
CONF_ANNOUNCE_VOLUME_MAX: Final[str] = "announce_volume_max"
CONF_ICON: Final[str] = "icon"
CONF_LANGUAGE: Final[str] = "language"
CONF_SAMPLE_RATES: Final[str] = "sample_rates"
CONF_HTTP_PROFILE: Final[str] = "http_profile"
CONF_BYPASS_NORMALIZATION_RADIO: Final[str] = "bypass_normalization_radio"
CONF_ENABLE_ICY_METADATA: Final[str] = "enable_icy_metadata"
CONF_VOLUME_NORMALIZATION_RADIO: Final[str] = "volume_normalization_radio"
CONF_VOLUME_NORMALIZATION_TRACKS: Final[str] = "volume_normalization_tracks"
CONF_VOLUME_NORMALIZATION_FIXED_GAIN_RADIO: Final[str] = "volume_normalization_fixed_gain_radio"
CONF_VOLUME_NORMALIZATION_FIXED_GAIN_TRACKS: Final[str] = "volume_normalization_fixed_gain_tracks"

# config default values
DEFAULT_HOST: Final[str] = "0.0.0.0"
DEFAULT_PORT: Final[int] = 8095

# common db tables
DB_TABLE_PLAYLOG: Final[str] = "playlog"
DB_TABLE_ARTISTS: Final[str] = "artists"
DB_TABLE_ALBUMS: Final[str] = "albums"
DB_TABLE_TRACKS: Final[str] = "tracks"
DB_TABLE_PLAYLISTS: Final[str] = "playlists"
DB_TABLE_RADIOS: Final[str] = "radios"
DB_TABLE_AUDIOBOOKS: Final[str] = "audiobooks"
DB_TABLE_PODCASTS: Final[str] = "podcasts"
DB_TABLE_CACHE: Final[str] = "cache"
DB_TABLE_SETTINGS: Final[str] = "settings"
DB_TABLE_THUMBS: Final[str] = "thumbnails"
DB_TABLE_PROVIDER_MAPPINGS: Final[str] = "provider_mappings"
DB_TABLE_ALBUM_TRACKS: Final[str] = "album_tracks"
DB_TABLE_TRACK_ARTISTS: Final[str] = "track_artists"
DB_TABLE_ALBUM_ARTISTS: Final[str] = "album_artists"
DB_TABLE_LOUDNESS_MEASUREMENTS: Final[str] = "loudness_measurements"


# all other
MASS_LOGO_ONLINE: Final[str] = (
    "https://github.com/home-assistant/brands/raw/master/custom_integrations/mass/icon%402x.png"
)
ENCRYPT_SUFFIX = "_encrypted_"
CONFIGURABLE_CORE_CONTROLLERS = (
    "streams",
    "webserver",
    "players",
    "metadata",
    "cache",
    "music",
    "player_queues",
)
VERBOSE_LOG_LEVEL: Final[int] = 5
PROVIDERS_WITH_SHAREABLE_URLS = ("spotify", "qobuz")


####### REUSABLE CONFIG ENTRIES #######

CONF_ENTRY_LOG_LEVEL = ConfigEntry(
    key=CONF_LOG_LEVEL,
    type=ConfigEntryType.STRING,
    label="Log level",
    options=(
        ConfigValueOption("global", "GLOBAL"),
        ConfigValueOption("info", "INFO"),
        ConfigValueOption("warning", "WARNING"),
        ConfigValueOption("error", "ERROR"),
        ConfigValueOption("debug", "DEBUG"),
        ConfigValueOption("verbose", "VERBOSE"),
    ),
    default_value="GLOBAL",
    category="advanced",
)

DEFAULT_PROVIDER_CONFIG_ENTRIES = (CONF_ENTRY_LOG_LEVEL,)
DEFAULT_CORE_CONFIG_ENTRIES = (CONF_ENTRY_LOG_LEVEL,)

# some reusable player config entries

CONF_ENTRY_FLOW_MODE = ConfigEntry(
    key=CONF_FLOW_MODE,
    type=ConfigEntryType.BOOLEAN,
    label="Enable queue flow mode",
    default_value=False,
)

CONF_ENTRY_FLOW_MODE_DEFAULT_ENABLED = ConfigEntry.from_dict(
    {**CONF_ENTRY_FLOW_MODE.to_dict(), "default_value": True}
)

CONF_ENTRY_FLOW_MODE_ENFORCED = ConfigEntry.from_dict(
    {
        **CONF_ENTRY_FLOW_MODE.to_dict(),
        "default_value": True,
        "value": True,
        "hidden": True,
    }
)

CONF_ENTRY_FLOW_MODE_HIDDEN_DISABLED = ConfigEntry.from_dict(
    {
        **CONF_ENTRY_FLOW_MODE.to_dict(),
        "default_value": False,
        "value": False,
        "hidden": True,
    }
)


CONF_ENTRY_AUTO_PLAY = ConfigEntry(
    key=CONF_AUTO_PLAY,
    type=ConfigEntryType.BOOLEAN,
    label="Automatically play/resume on power on",
    default_value=False,
    description="When this player is turned ON, automatically start playing "
    "(if there are items in the queue).",
)

CONF_ENTRY_OUTPUT_CHANNELS = ConfigEntry(
    key=CONF_OUTPUT_CHANNELS,
    type=ConfigEntryType.STRING,
    options=(
        ConfigValueOption("Stereo (both channels)", "stereo"),
        ConfigValueOption("Left channel", "left"),
        ConfigValueOption("Right channel", "right"),
        ConfigValueOption("Mono (both channels)", "mono"),
    ),
    default_value="stereo",
    label="Output Channel Mode",
    category="audio",
)

CONF_ENTRY_VOLUME_NORMALIZATION = ConfigEntry(
    key=CONF_VOLUME_NORMALIZATION,
    type=ConfigEntryType.BOOLEAN,
    label="Enable volume normalization",
    default_value=True,
    description="Enable volume normalization (EBU-R128 based)",
    category="audio",
)

CONF_ENTRY_VOLUME_NORMALIZATION_TARGET = ConfigEntry(
    key=CONF_VOLUME_NORMALIZATION_TARGET,
    type=ConfigEntryType.INTEGER,
    range=(-70, -5),
    default_value=-17,
    label="Target level for volume normalization",
    description="Adjust average (perceived) loudness to this target level",
    depends_on=CONF_VOLUME_NORMALIZATION,
    category="advanced",
)

# These EQ Options are deprecated and will be removed in the future
# To allow for automatic migration to the new DSP system, they are still included in the config
CONF_ENTRY_DEPRECATED_EQ_BASS = ConfigEntry(
    key=CONF_DEPRECATED_EQ_BASS,
    type=ConfigEntryType.INTEGER,
    range=(-10, 10),
    default_value=0,
    label="Equalizer: bass",
    description="Use the builtin basic equalizer to adjust the bass of audio.",
    category="audio",
    hidden=True,  # Hidden, use DSP instead
)

CONF_ENTRY_DEPRECATED_EQ_MID = ConfigEntry(
    key=CONF_DEPRECATED_EQ_MID,
    type=ConfigEntryType.INTEGER,
    range=(-10, 10),
    default_value=0,
    label="Equalizer: midrange",
    description="Use the builtin basic equalizer to adjust the midrange of audio.",
    category="audio",
    hidden=True,  # Hidden, use DSP instead
)

CONF_ENTRY_DEPRECATED_EQ_TREBLE = ConfigEntry(
    key=CONF_DEPRECATED_EQ_TREBLE,
    type=ConfigEntryType.INTEGER,
    range=(-10, 10),
    default_value=0,
    label="Equalizer: treble",
    description="Use the builtin basic equalizer to adjust the treble of audio.",
    category="audio",
    hidden=True,  # Hidden, use DSP instead
)


CONF_ENTRY_CROSSFADE = ConfigEntry(
    key=CONF_CROSSFADE,
    type=ConfigEntryType.BOOLEAN,
    label="Enable crossfade",
    default_value=False,
    description="Enable a crossfade transition between (queue) tracks.",
    category="audio",
)

CONF_ENTRY_CROSSFADE_FLOW_MODE_REQUIRED = ConfigEntry(
    key=CONF_CROSSFADE,
    type=ConfigEntryType.BOOLEAN,
    label="Enable crossfade",
    default_value=False,
    description="Enable a crossfade transition between (queue) tracks.\n\n "
    "Requires flow-mode to be enabled",
    category="audio",
    depends_on=CONF_FLOW_MODE,
)

CONF_ENTRY_CROSSFADE_DURATION = ConfigEntry(
    key=CONF_CROSSFADE_DURATION,
    type=ConfigEntryType.INTEGER,
    range=(1, 10),
    default_value=8,
    label="Crossfade duration",
    description="Duration in seconds of the crossfade between tracks (if enabled)",
    depends_on=CONF_CROSSFADE,
    category="advanced",
)

CONF_ENTRY_HIDE_PLAYER = ConfigEntry(
    key=CONF_HIDE_PLAYER,
    type=ConfigEntryType.BOOLEAN,
    label="Hide this player in the user interface",
    default_value=False,
)

CONF_ENTRY_ENFORCE_MP3 = ConfigEntry(
    key=CONF_ENFORCE_MP3,
    type=ConfigEntryType.BOOLEAN,
    label="Enforce (lossy) mp3 stream",
    default_value=False,
    description="By default, Music Assistant sends lossless, high quality audio "
    "to all players. Some players can not deal with that and require the stream to be packed "
    "into a lossy mp3 codec. \n\n "
    "Only enable when needed. Saves some bandwidth at the cost of audio quality.",
    category="audio",
)

CONF_ENTRY_ENFORCE_MP3_DEFAULT_ENABLED = ConfigEntry.from_dict(
    {**CONF_ENTRY_ENFORCE_MP3.to_dict(), "default_value": True}
)
CONF_ENTRY_ENFORCE_MP3_HIDDEN = ConfigEntry.from_dict(
    {**CONF_ENTRY_ENFORCE_MP3.to_dict(), "default_value": True, "hidden": True}
)

CONF_ENTRY_SYNC_ADJUST = ConfigEntry(
    key=CONF_SYNC_ADJUST,
    type=ConfigEntryType.INTEGER,
    range=(-500, 500),
    default_value=0,
    label="Audio synchronization delay correction",
    description="If this player is playing audio synced with other players "
    "and you always hear the audio too early or late on this player, "
    "you can shift the audio a bit.",
    category="advanced",
)


CONF_ENTRY_TTS_PRE_ANNOUNCE = ConfigEntry(
    key=CONF_TTS_PRE_ANNOUNCE,
    type=ConfigEntryType.BOOLEAN,
    default_value=True,
    label="Pre-announce TTS announcements",
    category="announcements",
)


CONF_ENTRY_ANNOUNCE_VOLUME_STRATEGY = ConfigEntry(
    key=CONF_ANNOUNCE_VOLUME_STRATEGY,
    type=ConfigEntryType.STRING,
    options=(
        ConfigValueOption("Absolute volume", "absolute"),
        ConfigValueOption("Relative volume increase", "relative"),
        ConfigValueOption("Volume increase by fixed percentage", "percentual"),
        ConfigValueOption("Do not adjust volume", "none"),
    ),
    default_value="percentual",
    label="Volume strategy for Announcements",
    category="announcements",
)

CONF_ENTRY_ANNOUNCE_VOLUME_STRATEGY_HIDDEN = ConfigEntry.from_dict(
    {**CONF_ENTRY_ANNOUNCE_VOLUME_STRATEGY.to_dict(), "hidden": True}
)

CONF_ENTRY_ANNOUNCE_VOLUME = ConfigEntry(
    key=CONF_ANNOUNCE_VOLUME,
    type=ConfigEntryType.INTEGER,
    default_value=85,
    label="Volume for Announcements",
    category="announcements",
)
CONF_ENTRY_ANNOUNCE_VOLUME_HIDDEN = ConfigEntry.from_dict(
    {**CONF_ENTRY_ANNOUNCE_VOLUME.to_dict(), "hidden": True}
)

CONF_ENTRY_ANNOUNCE_VOLUME_MIN = ConfigEntry(
    key=CONF_ANNOUNCE_VOLUME_MIN,
    type=ConfigEntryType.INTEGER,
    default_value=15,
    label="Minimum Volume level for Announcements",
    description="The volume (adjustment) of announcements should no go below this level.",
    category="announcements",
)
CONF_ENTRY_ANNOUNCE_VOLUME_MIN_HIDDEN = ConfigEntry.from_dict(
    {**CONF_ENTRY_ANNOUNCE_VOLUME_MIN.to_dict(), "hidden": True}
)

CONF_ENTRY_ANNOUNCE_VOLUME_MAX = ConfigEntry(
    key=CONF_ANNOUNCE_VOLUME_MAX,
    type=ConfigEntryType.INTEGER,
    default_value=75,
    label="Maximum Volume level for Announcements",
    description="The volume (adjustment) of announcements should no go above this level.",
    category="announcements",
)
CONF_ENTRY_ANNOUNCE_VOLUME_MAX_HIDDEN = ConfigEntry.from_dict(
    {**CONF_ENTRY_ANNOUNCE_VOLUME_MAX.to_dict(), "hidden": True}
)
HIDDEN_ANNOUNCE_VOLUME_CONFIG_ENTRIES = (
    CONF_ENTRY_ANNOUNCE_VOLUME_HIDDEN,
    CONF_ENTRY_ANNOUNCE_VOLUME_MIN_HIDDEN,
    CONF_ENTRY_ANNOUNCE_VOLUME_MAX_HIDDEN,
    CONF_ENTRY_ANNOUNCE_VOLUME_STRATEGY_HIDDEN,
)

CONF_ENTRY_PLAYER_ICON = ConfigEntry(
    key=CONF_ICON,
    type=ConfigEntryType.ICON,
    default_value="mdi-speaker",
    label="Icon",
    description="Material design icon for this player. "
    "\n\nSee https://pictogrammers.com/library/mdi/",
    category="generic",
)

CONF_ENTRY_PLAYER_ICON_GROUP = ConfigEntry.from_dict(
    {**CONF_ENTRY_PLAYER_ICON.to_dict(), "default_value": "mdi-speaker-multiple"}
)

CONF_ENTRY_SAMPLE_RATES = ConfigEntry(
    key=CONF_SAMPLE_RATES,
    type=ConfigEntryType.INTEGER_TUPLE,
    options=(
        ConfigValueOption("44.1kHz / 16 bits", (44100, 16)),
        ConfigValueOption("44.1kHz / 24 bits", (44100, 24)),
        ConfigValueOption("48kHz / 16 bits", (48000, 16)),
        ConfigValueOption("48kHz / 24 bits", (48000, 24)),
        ConfigValueOption("88.2kHz / 16 bits", (88200, 16)),
        ConfigValueOption("88.2kHz / 24 bits", (88200, 24)),
        ConfigValueOption("96kHz / 16 bits", (96000, 16)),
        ConfigValueOption("96kHz / 24 bits", (96000, 24)),
        ConfigValueOption("176.4kHz / 16 bits", (176400, 16)),
        ConfigValueOption("176.4kHz / 24 bits", (176400, 24)),
        ConfigValueOption("192kHz / 16 bits", (192000, 16)),
        ConfigValueOption("192kHz / 24 bits", (192000, 24)),
        ConfigValueOption("352.8kHz / 16 bits", (352800, 16)),
        ConfigValueOption("352.8kHz / 24 bits", (352800, 24)),
        ConfigValueOption("384kHz / 16 bits", (384000, 16)),
        ConfigValueOption("384kHz / 24 bits", (384000, 24)),
    ),
    default_value=[(44100, 16), (48000, 16)],
    required=True,
    multi_value=True,
    label="Sample rates supported by this player",
    category="advanced",
    description="The sample rates (and bit depths) supported by this player.\n"
    "Content with unsupported sample rates will be automatically resampled.",
)


CONF_ENTRY_HTTP_PROFILE = ConfigEntry(
    key=CONF_HTTP_PROFILE,
    type=ConfigEntryType.STRING,
    options=(
        ConfigValueOption("Profile 1 - chunked", "chunked"),
        ConfigValueOption("Profile 2 - no content length", "no_content_length"),
        ConfigValueOption("Profile 3 - forced content length", "forced_content_length"),
    ),
    default_value="no_content_length",
    label="HTTP Profile used for sending audio",
    category="advanced",
    description="This is considered to be a very advanced setting, only adjust this if needed, "
    "for example if your player stops playing halfway streams or if you experience "
    "other playback related issues. In most cases the default setting is fine.",
)

CONF_ENTRY_HTTP_PROFILE_FORCED_1 = ConfigEntry.from_dict(
    {**CONF_ENTRY_HTTP_PROFILE.to_dict(), "default_value": "chunked", "hidden": True}
)
CONF_ENTRY_HTTP_PROFILE_FORCED_2 = ConfigEntry.from_dict(
    {
        **CONF_ENTRY_HTTP_PROFILE.to_dict(),
        "default_value": "no_content_length",
        "hidden": True,
    }
)

CONF_ENTRY_ENABLE_ICY_METADATA = ConfigEntry(
    key=CONF_ENABLE_ICY_METADATA,
    type=ConfigEntryType.STRING,
    options=(
        ConfigValueOption("Disabled - do not send ICY metadata", "disabled"),
        ConfigValueOption("Profile 1 - basic info", "basic"),
        ConfigValueOption("Profile 2 - full info (including image)", "full"),
    ),
    depends_on=CONF_FLOW_MODE,
    default_value="disabled",
    label="Try to ingest metadata into stream (ICY)",
    category="advanced",
    description="Try to ingest metadata into the stream (ICY) to show track info on the player, "
    "even when flow mode is enabled.\n\nThis is called ICY metadata and its what is also used by "
    "online radio station to inform you what is playing. \n\nBe aware that not all players support "
    "this correctly. If you experience issues with playback, try to disable this setting.",
)


def create_sample_rates_config_entry(
    max_sample_rate: int,
    max_bit_depth: int,
    safe_max_sample_rate: int = 48000,
    safe_max_bit_depth: int = 16,
    hidden: bool = False,
) -> ConfigEntry:
    """Create sample rates config entry based on player specific helpers."""
    assert CONF_ENTRY_SAMPLE_RATES.options
    conf_entry = ConfigEntry.from_dict(CONF_ENTRY_SAMPLE_RATES.to_dict())
    conf_entry.hidden = hidden
    options: list[ConfigValueOption] = []
    default_value: list[tuple[int, int]] = []
    for option in CONF_ENTRY_SAMPLE_RATES.options:
        if not isinstance(option.value, tuple):
            continue
        sample_rate, bit_depth = option.value
        if sample_rate <= max_sample_rate and bit_depth <= max_bit_depth:
            options.append(option)
        if sample_rate <= safe_max_sample_rate and bit_depth <= safe_max_bit_depth:
            default_value.append(option.value)
    conf_entry.options = tuple(options)
    conf_entry.default_value = default_value
    return conf_entry


BASE_PLAYER_CONFIG_ENTRIES = (
    # config entries that are valid for all players
    CONF_ENTRY_PLAYER_ICON,
    CONF_ENTRY_FLOW_MODE,
    CONF_ENTRY_VOLUME_NORMALIZATION,
    CONF_ENTRY_AUTO_PLAY,
    CONF_ENTRY_VOLUME_NORMALIZATION_TARGET,
    CONF_ENTRY_HIDE_PLAYER,
    CONF_ENTRY_TTS_PRE_ANNOUNCE,
    CONF_ENTRY_SAMPLE_RATES,
    CONF_ENTRY_HTTP_PROFILE_FORCED_2,
)
