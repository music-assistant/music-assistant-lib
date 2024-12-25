"""
Podcast RSS Feed Music Provider for Music Assistant.

A URL to a podcast feed can be configured. The contents of that specific podcast
feed will be forwarded to music assistant. In order to have multiple podcast feeds,
multiple instances with each one feed must exist.

"""

from __future__ import annotations

import urllib.request
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

import podcastparser
from music_assistant_models.config_entries import ConfigEntry, ConfigValueType
from music_assistant_models.enums import (
    ConfigEntryType,
    ContentType,
    ImageType,
    MediaType,
    ProviderFeature,
    StreamType,
)
from music_assistant_models.errors import InvalidProviderURI, MediaNotFoundError
from music_assistant_models.media_items import (
    AudioFormat,
    Episode,
    MediaItemImage,
    MediaItemType,
    Podcast,
    ProviderMapping,
    SearchResults,
)
from music_assistant_models.streamdetails import StreamDetails

from music_assistant.models.music_provider import MusicProvider

if TYPE_CHECKING:
    from music_assistant_models.config_entries import ProviderConfig
    from music_assistant_models.provider import ProviderManifest

    from music_assistant import MusicAssistant
    from music_assistant.models import ProviderInstanceType

CONF_FEED_URL = "feed_url"


async def setup(
    mass: MusicAssistant, manifest: ProviderManifest, config: ProviderConfig
) -> ProviderInstanceType:
    """Initialize provider(instance) with given configuration."""
    # ruff: noqa: ARG001
    if not config.get_value(CONF_FEED_URL):
        msg = "No podcast feed set"
        return InvalidProviderURI(msg)
    return PodcastMusicprovider(mass, manifest, config)


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
    return (
        ConfigEntry(
            key=CONF_FEED_URL,
            type=ConfigEntryType.STRING,
            default_value=[],
            label="RSS Feed URL",
            required=True,
        ),
    )


class PodcastMusicprovider(MusicProvider):
    """Podcast RSS Feed Music Provider."""

    @property
    def supported_features(self) -> tuple[ProviderFeature, ...]:
        """Return the features supported by this Provider."""
        return (
            ProviderFeature.BROWSE,
            ProviderFeature.SEARCH,
            ProviderFeature.LIBRARY_PODCASTS,
            # see the ProviderFeature enum for all available features
        )

    async def handle_async_init(self) -> None:
        """Handle async initialization of the provider."""
        # ruff: noqa: S310
        # ruff: noqa: ASYNC210
        # self.parsed = await podcastparser.parse(
        #    self.config.get_value(CONF_FEED_URL),
        #    urllib.request.urlopen(
        #        podcastparser.normalize_feed_url(self.config.get_value(CONF_FEED_URL))
        #    ),
        # )

    @property
    def is_streaming_provider(self) -> bool:
        """
        Return True if the provider is a streaming provider.

        This literally means that the catalog is not the same as the library contents.
        For local based providers (files, plex), the catalog is the same as the library content.
        It also means that data is if this provider is NOT a streaming provider,
        data cross instances is unique, the catalog and library differs per instance.

        Setting this to True will only query one instance of the provider for search and lookups.
        Setting this to False will query all instances of this provider for search and lookups.
        """
        return True

    async def search(
        self,
        search_query: str,
        media_types: list[MediaType],
        limit: int = 5,
    ) -> SearchResults:
        """Perform search on musicprovider.

        :param search_query: Search query.
        :param media_types: A list of media_types to include.
        :param limit: Number of items to return in the search (per type).
        """
        result = SearchResults()

        if MediaType.PODCAST in media_types or media_types is None:
            # return podcast if artist matches podcast name
            if search_query in self.parsed["title"]:
                result.podcasts.append(await self._parse_podcast())

        # if MediaType.EPISODE in media_types or media_types is None:
        #    if search_query in self.parsed["title"]:
        #        for episode in self.parsed["episodes"]:
        #            result.podcasts.append(await self._parse_episode(episode))

        return result

    async def get_library_podcasts(self) -> AsyncGenerator[Podcast, None]:
        """Retrieve library/subscribed podcasts from the provider."""
        yield await self._parse_podcast()

    async def get_podcast(self, prov_podcast_id: str) -> Podcast:
        """Get full artist details by id."""
        return await self._parse_podcast()

    # type: ignore[return]
    async def get_episode(self, prov_episode_id: str) -> Episode:
        """Get (full) podcast episode details by id."""
        for episode in self.parsed["episodes"]:
            if prov_episode_id in episode["guid"]:
                return await self._parse_episode(episode)
        raise MediaNotFoundError("Track not found")

    async def get_podcast_episodes(
        self,
        prov_podcast_id: str,
    ) -> list[Episode]:
        """List all episodes for the podcast."""
        episodes = []

        for episode in self.parsed["episodes"]:
            episodes.append(await self._parse_episode(episode))

        return episodes

    async def library_add(self, item: MediaItemType) -> bool:
        """Add item to provider's library. Return true on success."""
        return True

    async def library_remove(self, prov_item_id: str, media_type: MediaType) -> bool:
        """Remove item from provider's library. Return true on success."""
        return True

    async def get_stream_details(self, item_id: str) -> StreamDetails:
        """Get streamdetails for a track/radio."""
        for episode in self.parsed["episodes"]:
            if item_id in episode["guid"]:
                return StreamDetails(
                    provider=self.instance_id,
                    item_id=item_id,
                    audio_format=AudioFormat(
                        # hard coded mp3 for now
                        content_type=ContentType.MP3,
                    ),
                    media_type=MediaType.PODCAST,
                    stream_type=StreamType.HTTP,
                    path=episode["enclosures"][0]["url"],
                )
        raise MediaNotFoundError("Stream not found")

    async def resolve_image(self, path: str) -> str | bytes:
        """
        Resolve an image from an image path.

        This either returns (a generator to get) raw bytes of the image or
        a string with an http(s) URL or local path that is accessible from the server.
        """
        return path

    async def sync_library(self, media_types: tuple[MediaType, ...]) -> None:
        """Run library sync for this provider."""
        self.parsed = podcastparser.parse(
            self.config.get_value(CONF_FEED_URL),
            urllib.request.urlopen(self.config.get_value(CONF_FEED_URL)),
        )

    async def _parse_podcast(self) -> Podcast:
        """Parse podcast information from podcast feed."""
        podcast = Podcast(
            item_id=hash(self.parsed["title"]),
            name=self.parsed["title"],
            provider=self.domain,
            provider_mappings={
                ProviderMapping(
                    item_id=self.parsed["title"],
                    provider_domain=self.domain,
                    provider_instance=self.instance_id,
                    url=self.parsed["link"],
                )
            },
        )

        podcast.metadata.description = self.parsed["description"]
        podcast.metadata.style = "Podcast"

        if self.parsed["cover_url"]:
            img_url = self.parsed["cover_url"]
            podcast.metadata.images = [
                MediaItemImage(
                    type=ImageType.THUMB,
                    path=img_url,
                    provider=self.lookup_key,
                    remotely_accessible=True,
                )
            ]

        return podcast

    async def _parse_episode(self, track_obj: dict, track_position: int = 0) -> Episode:
        name = track_obj["title"]
        track_id = track_obj["guid"]
        episode = Episode(
            item_id=track_id,
            provider=self.domain,
            name=name,
            duration=track_obj["total_time"],
            provider_mappings={
                ProviderMapping(
                    item_id=track_id,
                    provider_domain=self.domain,
                    provider_instance=self.instance_id,
                    audio_format=AudioFormat(
                        content_type=ContentType.MP3,
                    ),
                    url=track_obj["link"],
                )
            },
            position=track_position,
        )

        episode.podcast.append(await self._parse_podcast())

        if "episode_art_url" in track_obj:
            episode.metadata.images = [
                MediaItemImage(
                    type=ImageType.THUMB,
                    path=track_obj["episode_art_url"],
                    provider=self.lookup_key,
                    remotely_accessible=True,
                )
            ]
        episode.metadata.description = track_obj["description"]
        episode.metadata.explicit = track_obj["explicit"]

        return episode
