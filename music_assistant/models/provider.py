"""Model for a Music Providers."""
from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, AsyncGenerator, List, Optional

from music_assistant.models.config import MusicProviderConfig
from music_assistant.models.enums import MediaType, ProviderType
from music_assistant.models.media_items import (
    Album,
    Artist,
    MediaItemType,
    Playlist,
    Radio,
    Track,
)
from music_assistant.models.player_queue import StreamDetails

if TYPE_CHECKING:
    from music_assistant.mass import MusicAssistant


class MusicProvider:
    """Model for a Music Provider."""

    _attr_name: str = None
    _attr_type: ProviderType = None
    _attr_available: bool = True
    _attr_supported_mediatypes: List[MediaType] = []

    def __init__(self, mass: MusicAssistant, config: MusicProviderConfig) -> None:
        """Initialize MusicProvider."""
        self.mass = mass
        self.config = config
        self.logger = mass.logger
        self.cache = mass.cache

    @abstractmethod
    async def setup(self) -> bool:
        """
        Handle async initialization of the provider.

        Called when provider is registered.
        """

    @property
    def type(self) -> ProviderType:
        """Return provider type for this provider."""
        return self._attr_type

    @property
    def name(self) -> str:
        """Return provider Name for this provider."""
        return self._attr_name

    @property
    def available(self) -> bool:
        """Return boolean if this provider is available/initialized."""
        return self._attr_available

    @property
    def supported_mediatypes(self) -> List[MediaType]:
        """Return MediaTypes the provider supports."""
        return self._attr_supported_mediatypes

    async def search(
        self, search_query: str, media_types=Optional[List[MediaType]], limit: int = 5
    ) -> List[MediaItemType]:
        """
        Perform search on musicprovider.

            :param search_query: Search query.
            :param media_types: A list of media_types to include. All types if None.
            :param limit: Number of items to return in the search (per type).
        """
        raise NotImplementedError

    async def get_library_artists(self) -> AsyncGenerator[Artist, None]:
        """Retrieve library artists from the provider."""
        if MediaType.ARTIST in self.supported_mediatypes:
            raise NotImplementedError

    async def get_library_albums(self) -> AsyncGenerator[Album, None]:
        """Retrieve library albums from the provider."""
        if MediaType.ALBUM in self.supported_mediatypes:
            raise NotImplementedError

    async def get_library_tracks(self) -> AsyncGenerator[Track, None]:
        """Retrieve library tracks from the provider."""
        if MediaType.TRACK in self.supported_mediatypes:
            raise NotImplementedError

    async def get_library_playlists(self) -> AsyncGenerator[Playlist, None]:
        """Retrieve library/subscribed playlists from the provider."""
        if MediaType.PLAYLIST in self.supported_mediatypes:
            raise NotImplementedError

    async def get_library_radios(self) -> AsyncGenerator[Radio, None]:
        """Retrieve library/subscribed radio stations from the provider."""
        if MediaType.RADIO in self.supported_mediatypes:
            raise NotImplementedError

    async def get_artist(self, prov_artist_id: str) -> Artist:
        """Get full artist details by id."""
        if MediaType.ARTIST in self.supported_mediatypes:
            raise NotImplementedError

    async def get_artist_albums(self, prov_artist_id: str) -> List[Album]:
        """Get a list of all albums for the given artist."""
        if MediaType.ALBUM in self.supported_mediatypes:
            raise NotImplementedError

    async def get_artist_toptracks(self, prov_artist_id: str) -> List[Track]:
        """Get a list of most popular tracks for the given artist."""
        if MediaType.TRACK in self.supported_mediatypes:
            raise NotImplementedError

    async def get_album(self, prov_album_id: str) -> Album:
        """Get full album details by id."""
        if MediaType.ALBUM in self.supported_mediatypes:
            raise NotImplementedError

    async def get_track(self, prov_track_id: str) -> Track:
        """Get full track details by id."""
        if MediaType.TRACK in self.supported_mediatypes:
            raise NotImplementedError

    async def get_playlist(self, prov_playlist_id: str) -> Playlist:
        """Get full playlist details by id."""
        if MediaType.PLAYLIST in self.supported_mediatypes:
            raise NotImplementedError

    async def get_radio(self, prov_radio_id: str) -> Radio:
        """Get full radio details by id."""
        if MediaType.RADIO in self.supported_mediatypes:
            raise NotImplementedError

    async def get_album_tracks(self, prov_album_id: str) -> List[Track]:
        """Get album tracks for given album id."""
        if MediaType.ALBUM in self.supported_mediatypes:
            raise NotImplementedError

    async def get_playlist_tracks(self, prov_playlist_id: str) -> List[Track]:
        """Get all playlist tracks for given playlist id."""
        if MediaType.PLAYLIST in self.supported_mediatypes:
            raise NotImplementedError

    async def library_add(self, prov_item_id: str, media_type: MediaType) -> bool:
        """Add item to provider's library. Return true on succes."""
        raise NotImplementedError

    async def library_remove(self, prov_item_id: str, media_type: MediaType) -> bool:
        """Remove item from provider's library. Return true on succes."""
        raise NotImplementedError

    async def add_playlist_tracks(
        self, prov_playlist_id: str, prov_track_ids: List[str]
    ) -> None:
        """Add track(s) to playlist."""
        if MediaType.PLAYLIST in self.supported_mediatypes:
            raise NotImplementedError

    async def remove_playlist_tracks(
        self, prov_playlist_id: str, prov_track_ids: List[str]
    ) -> None:
        """Remove track(s) from playlist."""
        if MediaType.PLAYLIST in self.supported_mediatypes:
            raise NotImplementedError

    async def get_stream_details(self, item_id: str) -> StreamDetails:
        """Get streamdetails for a track/radio."""
        raise NotImplementedError

    async def get_item(self, media_type: MediaType, prov_item_id: str) -> MediaItemType:
        """Get single MediaItem from provider."""
        if media_type == MediaType.ARTIST:
            return await self.get_artist(prov_item_id)
        if media_type == MediaType.ALBUM:
            return await self.get_album(prov_item_id)
        if media_type == MediaType.TRACK:
            return await self.get_track(prov_item_id)
        if media_type == MediaType.PLAYLIST:
            return await self.get_playlist(prov_item_id)
        if media_type == MediaType.RADIO:
            return await self.get_radio(prov_item_id)

    async def sync(self) -> None:
        """Run/schedule sync for this provider."""
        await self.mass.music.run_provider_sync(self.id)

    # DO NOT OVERRIDE BELOW

    @property
    def id(self) -> str:
        """
        Return unique provider id to distinguish multiple instances of the same provider.

        Defaults to combination of type and username/path.
        """
        if self.config.path:
            return f"{self.type.value}.{self.config.path}"
        if self.config.username:
            return f"{self.type.value}.{self.config.username}"
        return self.type.value
