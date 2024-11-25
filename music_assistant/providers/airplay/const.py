"""Constants for the AirPlay provider."""

from __future__ import annotations

from music_assistant_models.enums import ContentType
from music_assistant_models.media_items import AudioFormat

DOMAIN = "airplay"

CONF_ENCRYPTION = "encryption"
CONF_ALAC_ENCODE = "alac_encode"
CONF_VOLUME_START = "volume_start"
CONF_PASSWORD = "password"
CONF_BIND_INTERFACE = "bind_interface"
CONF_READ_AHEAD_BUFFER = "read_ahead_buffer"

BACKOFF_TIME_LOWER_LIMIT = 15  # seconds
BACKOFF_TIME_UPPER_LIMIT = 300  # Five minutes

CONF_CREDENTIALS = "credentials"
CACHE_KEY_PREV_VOLUME = "airplay_prev_volume"
FALLBACK_VOLUME = 20

AIRPLAY_FLOW_PCM_FORMAT = AudioFormat(
    content_type=ContentType.PCM_F32LE,
    sample_rate=44100,
    bit_depth=32,
)
AIRPLAY_PCM_FORMAT = AudioFormat(
    content_type=ContentType.from_bit_depth(16), sample_rate=44100, bit_depth=16
)

IGNORE_RAOP_SONOS_MODELS = (
    # A recent fw update of newer gen Sonos speakers block RAOP (airplay 1) support,
    # basically rendering our airplay implementation useless on these devices.
    # This list contains the models that are known to have this issue.
    # Hopefully the issue won't spread to other models.
    "Era 100",
    "Era 300",
    "Move 2",
    "Roam 2",
    "Arc Ultra",
)
