"""Model/base for a Plugin Provider implementation."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

from music_assistant_models.enums import MediaType

from .provider import Provider

if TYPE_CHECKING:
    from music_assistant_models.media_items import PluginSource
    from music_assistant_models.streamdetails import StreamDetails

# ruff: noqa: ARG001, ARG002


class PluginProvider(Provider):
    """
    Base representation of a Plugin for Music Assistant.

    Plugin Provider implementations should inherit from this base model.
    """

    async def get_sources(self) -> list[PluginSource]:  # type: ignore[return]
        """Get all audio sources provided by this provider."""
        # Will only be called if ProviderFeature.AUDIO_SOURCE is declared
        raise NotImplementedError

    async def get_source(self, prov_source_id: str) -> PluginSource:  # type: ignore[return]
        """Get AudioSource details by id."""
        # Will only be called if ProviderFeature.AUDIO_SOURCE is declared
        raise NotImplementedError

    async def get_stream_details(
        self, item_id: str, media_type: MediaType = MediaType.TRACK
    ) -> StreamDetails:
        """Return the streamdetails to stream an (audio)source provided by this plugin."""
        # Will only be called if ProviderFeature.AUDIO_SOURCE is declared
        raise NotImplementedError

    async def get_audio_stream(
        self, streamdetails: StreamDetails, seek_position: int = 0
    ) -> AsyncGenerator[bytes, None]:
        """
        Return the (custom) audio stream for the provider item.

        Will only be called when the stream_type is set to CUSTOM.
        """
        if False:
            yield b""
        raise NotImplementedError

    async def on_streamed(
        self,
        streamdetails: StreamDetails,
    ) -> None:
        """
        Handle callback when given streamdetails completed streaming.

        To get the number of seconds streamed, see streamdetails.seconds_streamed.
        To get the number of seconds seeked/skipped, see streamdetails.seek_position.
        Note that seconds_streamed is the total streamed seconds, so without seeked time.

        NOTE: Due to internal and player buffering,
        this may be called in advance of the actual completion.
        """
