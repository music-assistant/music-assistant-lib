"""Helper module for parsing the Deezer API. Also helper for getting audio streams

This helpers file is an async wrapper around the excellent deezer-python package.
While the deezer-python package does an excellent job at parsing the Deezer results,
it is unfortunately not async, which is required for Music Assistant to run smoothly.
This also nicely separates the parsing logic from the Deezer provider logic.

CREDITS:
deezer-python: https://github.com/browniebroke/deezer-python by @browniebroke
dzr: (which heavily inspired the track url and decoder but is not used) https://github.com/yne/dzr by @yne
"""

import asyncio
import json
from time import time

import deezer


class credential:
    """Class for storing credentials"""

    def __init__(self, app_id: int, app_secret: str, access_token: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.access_token = access_token

    app_id: int
    app_secret: str
    access_token: str


async def get_deezer_client(creds: credential = None) -> deezer.Client:  # type: ignore
    """
    Returns a deezer-python Client
    If credentials are given the client is authorized. If no credentials are given the deezer client is not authorized

    :param creds: Credentials. If none are given client is not authorized, defaults to None
    :type creds: credential, optional
    """
    if creds:
        if not isinstance(creds, credential):
            raise TypeError("Creds must be of type credential")

    def _authorize():
        if creds:
            client = deezer.Client(
                app_id=creds.app_id, app_secret=creds.app_secret, access_token=creds.access_token
            )
        else:
            client = deezer.Client()
        return client

    return await asyncio.to_thread(_authorize)


async def get_artist(artist_id: int) -> deezer.Artist:
    """Async wrapper of the deezer-python get_artist function"""

    client = await get_deezer_client()

    def _get_artist():
        artist = client.get_artist(artist_id=artist_id)
        return artist

    return await asyncio.to_thread(_get_artist)


async def get_album(album_id: int) -> deezer.Album:
    """Async wrapper of the deezer-python get_album function"""

    client = await get_deezer_client()

    def _get_album():
        album = client.get_album(album_id=album_id)
        return album

    return await asyncio.to_thread(_get_album)


async def get_playlist(creds: credential, playlist_id) -> deezer.Playlist:
    """Async wrapper of the deezer-python get_playlist function"""

    client = await get_deezer_client(creds=creds)

    def _get_playlist():
        playlist = client.get_playlist(playlist_id=playlist_id)
        return playlist

    return await asyncio.to_thread(_get_playlist)


async def get_track(track_id: int) -> deezer.Track:
    """Async wrapper of the deezer-python get_track function"""

    client = await get_deezer_client()

    def _get_track():
        track = client.get_track(track_id=track_id)
        return track

    return await asyncio.to_thread(_get_track)


async def get_user_artists(creds: credential) -> deezer.PaginatedList:
    """Async wrapper of the deezer-python get_user_artists function"""

    client = await get_deezer_client(creds=creds)

    def _get_track():
        artists = client.get_user_artists()
        return artists

    return await asyncio.to_thread(_get_track)


# async def get_user_playlists(creds : credential) -> deezer.PaginatedList:
#    """Async wrapper of the deezer-python get_user_playlists function"""
#
#    client = await get_deezer_client(creds=creds)
#    def _get_track():
#        playlists = client.get_user_playlists()
#        return playlists
#
#    return await asyncio.to_thread(_get_track)


async def get_user_albums(creds: credential) -> deezer.PaginatedList:
    """Async wrapper of the deezer-python get_user_albums function"""

    client = await get_deezer_client(creds=creds)

    def _get_track():
        albums = client.get_user_albums()
        return albums

    return await asyncio.to_thread(_get_track)


async def add_user_albums(creds: credential, album_id: int) -> bool:
    """Async wrapper of the deezer-python add_user_albums function"""

    client = await get_deezer_client(creds=creds)

    def _get_track():
        success = client.add_user_album(album_id=album_id)
        return success

    return await asyncio.to_thread(_get_track)


async def remove_user_albums(creds: credential, album_id: int) -> bool:
    """Async wrapper of the deezer-python remove_user_albums function"""

    client = await get_deezer_client(creds=creds)

    def _get_track():
        success = client.remove_user_album(album_id=album_id)
        return success

    return await asyncio.to_thread(_get_track)


async def add_user_tracks(creds: credential, track_id: int) -> bool:
    """Async wrapper of the deezer-python add_user_tracks function"""

    client = await get_deezer_client(creds=creds)

    def _get_track():
        success = client.add_user_track(track_id=track_id)
        return success

    return await asyncio.to_thread(_get_track)


async def remove_user_tracks(creds: credential, track_id: int) -> bool:
    """Async wrapper of the deezer-python remove_user_tracks function"""

    client = await get_deezer_client(creds=creds)

    def _get_track():
        success = client.remove_user_track(track_id=track_id)
        return success

    return await asyncio.to_thread(_get_track)


async def add_user_artists(creds: credential, artist_id: int) -> bool:
    """Async wrapper of the deezer-python add_user_artists function"""

    client = await get_deezer_client(creds=creds)

    def _get_artist():
        success = client.add_user_artist(artist_id=artist_id)
        return success

    return await asyncio.to_thread(_get_artist)


async def remove_user_artists(creds: credential, artist_id: int) -> bool:
    """Async wrapper of the deezer-python remove_user_artists function"""

    client = await get_deezer_client(creds=creds)

    def _get_artist():
        success = client.remove_user_artist(artist_id=artist_id)
        return success

    return await asyncio.to_thread(_get_artist)


async def search(query: str, filter: str = None) -> deezer.PaginatedList:  # type: ignore
    """Async wrapper of the deezer-python search function"""

    client = await get_deezer_client()

    def _search():
        if filter == "album":
            result = client.search_albums(query=query)
        elif filter == "artist":
            result = client.search_artists(query=query)
        else:
            result = client.search(query=query)
        print(result)
        return result

    return await asyncio.to_thread(_search)
