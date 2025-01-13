"""Parse objects from py-opensonic into Music Assistant types."""

from __future__ import annotations

from typing import TYPE_CHECKING

from music_assistant_models.enums import ImageType
from music_assistant_models.media_items import Artist, MediaItemImage, ProviderMapping
from music_assistant_models.unique_list import UniqueList

if TYPE_CHECKING:
    from libopensonic.media import Artist as SonicArtist
    from libopensonic.media import ArtistInfo as SonicArtistInfo


def parse_artist(
    instance_id: str, sonic_artist: SonicArtist, sonic_info: SonicArtistInfo = None
) -> Artist:
    """Parse artist and artistInfo into a Music Assistant Artist."""
    artist = Artist(
        item_id=sonic_artist.id,
        name=sonic_artist.name,
        provider="opensubsonic",
        favorite=bool(sonic_artist.starred),
        provider_mappings={
            ProviderMapping(
                item_id=sonic_artist.id,
                provider_domain="opensubsonic",
                provider_instance=instance_id,
            )
        },
    )

    artist.metadata.images = UniqueList()
    if sonic_artist.cover_id:
        artist.metadata.images.append(
            MediaItemImage(
                type=ImageType.THUMB,
                path=sonic_artist.cover_id,
                provider=instance_id,
                remotely_accessible=False,
            )
        )

    if sonic_info:
        if sonic_info.biography:
            artist.metadata.description = sonic_info.biography
        if sonic_info.small_url:
            artist.metadata.images.append(
                MediaItemImage(
                    type=ImageType.THUMB,
                    path=sonic_info.small_url,
                    provider=instance_id,
                    remotely_accessible=True,
                )
            )

    return artist
