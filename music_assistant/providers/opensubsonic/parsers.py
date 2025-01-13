"""Parse objects from py-opensonic into Music Assistant types."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from music_assistant_models.enums import (
    ImageType,
    MediaType,
)
from music_assistant_models.media_items import (
    Album,
    Artist,
    ItemMapping,
    MediaItemImage,
    ProviderMapping,
)
from music_assistant_models.unique_list import UniqueList

from music_assistant.constants import UNKNOWN_ARTIST

if TYPE_CHECKING:
    from libopensonic.media import Album as SonicAlbum
    from libopensonic.media import AlbumInfo as SonicAlbumInfo
    from libopensonic.media import Artist as SonicArtist
    from libopensonic.media import ArtistInfo as SonicArtistInfo

UNKNOWN_ARTIST_ID = "fake_artist_unknown"


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


def parse_album(
    logger: logging.Logger,
    instance_id: str,
    sonic_album: SonicAlbum,
    sonic_info: SonicAlbumInfo | None = None,
) -> Album:
    """Parse album and albumInfo into a Music Assistant Album."""
    album_id = sonic_album.id
    album = Album(
        item_id=album_id,
        provider="opensubsonic",
        name=sonic_album.name,
        favorite=bool(sonic_album.starred),
        provider_mappings={
            ProviderMapping(
                item_id=album_id,
                provider_domain="opensubsonic",
                provider_instance=instance_id,
            )
        },
        year=sonic_album.year,
    )

    album.metadata.images = UniqueList()
    if sonic_album.cover_id:
        album.metadata.images.append(
            MediaItemImage(
                type=ImageType.THUMB,
                path=sonic_album.cover_id,
                provider=instance_id,
                remotely_accessible=False,
            ),
        )

    if sonic_album.artist_id:
        album.artists.append(
            ItemMapping(
                media_type=MediaType.ARTIST,
                item_id=sonic_album.artist_id,
                provider=instance_id,
                name=sonic_album.artist if sonic_album.artist else UNKNOWN_ARTIST,
            )
        )
    else:
        logger.info(
            "Unable to find an artist ID for album '%s' with ID '%s'.",
            sonic_album.name,
            sonic_album.id,
        )
        album.artists.append(
            Artist(
                item_id=UNKNOWN_ARTIST_ID,
                name=UNKNOWN_ARTIST,
                provider=instance_id,
                provider_mappings={
                    ProviderMapping(
                        item_id=UNKNOWN_ARTIST_ID,
                        provider_domain="opensubsonic",
                        provider_instance=instance_id,
                    )
                },
            )
        )

    if sonic_info:
        if sonic_info.small_url:
            album.metadata.images.append(
                MediaItemImage(
                    type=ImageType.THUMB,
                    path=sonic_info.small_url,
                    remotely_accessible=False,
                    provider=instance_id,
                )
            )
        if sonic_info.notes:
            album.metadata.description = sonic_info.notes

    return album
