"""
Sonos Player provider for Music Assistant for speakers running the S2 firmware.

Based on the aiosonos library, which leverages the new websockets API of the Sonos S2 firmware.
https://github.com/music-assistant/aiosonos
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from music_assistant_models.config_entries import ConfigEntry, ConfigEntryType

from music_assistant.constants import VERBOSE_LOG_LEVEL

from .provider import CONF_IPS, SonosPlayerProvider

if TYPE_CHECKING:
    from music_assistant_models.config_entries import ConfigValueType, ProviderConfig
    from music_assistant_models.provider import ProviderManifest

    from music_assistant import MusicAssistant
    from music_assistant.models import ProviderInstanceType


async def setup(
    mass: MusicAssistant, manifest: ProviderManifest, config: ProviderConfig
) -> ProviderInstanceType:
    """Initialize provider(instance) with given configuration."""
    prov = SonosPlayerProvider(mass, manifest, config)
    # set-up aiosonos logging
    if prov.logger.isEnabledFor(VERBOSE_LOG_LEVEL):
        logging.getLogger("aiosonos").setLevel(logging.DEBUG)
    else:
        logging.getLogger("aiosonos").setLevel(prov.logger.level + 10)
    return prov


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
            key=CONF_IPS,
            type=ConfigEntryType.STRING,
            label="IP addresses (ADVANCED, NOT SUPPORTED)",
            description="Additional fixed IP addresses for speakers. "
            "Should be formatted as a comma separated list of IP addresses "
            "(e.g. '10.0.0.42, 10.0.0.45').\n"
            "Invalid addresses may result in the Sonos provider "
            "becoming unresponsive and server crashes.\n"
            "Bidirectional unicast communication to and between all IPs is required.\n"
            "NOT SUPPORTED, USE ON YOU'RE OWN RISK",
            category="advanced",
            default_value=None,
            required=False,
        ),
    )
