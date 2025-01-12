"""Simple Client for Audiobookshelf.

We only implement the functions necessary for mass.
"""

from collections.abc import AsyncGenerator
from enum import Enum
from typing import Any

from aiohttp import ClientSession

from music_assistant.providers.audiobookshelf.abs_schema import (
    ABSAudioBook,
    ABSAudioBookChapter,
    ABSAudioBookmark,
    ABSAudioBookMedia,
    ABSAudioBookMetaData,
    ABSAudioTrack,
    ABSAuthorMinified,
    ABSLibrary,
    ABSMediaProgress,
    ABSPodcast,
    ABSPodcastEpisodeExpanded,
    ABSPodcastMedia,
    ABSPodcastMetaData,
    ABSSeriesSequence,
    ABSUser,
)

# use page calls in case of large libraries
LIMIT_ITEMS_PER_PAGE = 10


def camel_to_snake(camel: str) -> str:
    """Convert Camel to snake."""
    if camel == "id":
        return "id_"
    elif camel == "type":
        return "type_"
    return "".join([x if x.islower() else f"_{x.lower()}" for x in camel]).strip("_")


class ABSStatus(Enum):
    """ABS Status Enum."""

    STATUS_OK = 200
    STATUS_NOT_FOUND = 404


class ABSClient:
    """Simple Audiobookshelf client.

    Only implements methods needed for Music Assistant.
    """

    def __init__(self) -> None:
        """Client authorization."""
        self.podcast_libraries: list[ABSLibrary] = []
        self.audiobook_libraries: list[ABSLibrary] = []
        self.user: ABSUser
        self.check_ssl: bool

    async def init(
        self, base_url: str, username: str, password: str, check_ssl: bool = True
    ) -> None:
        """Initialize."""
        self.check_ssl = check_ssl
        self.session = ClientSession(base_url)
        self.user = await self.login(username=username, password=password)
        self.token: str = self.user.token
        self.session.headers["Authorization"] = f"Bearer {self.token}"

    async def _post(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
        add_api_endpoint: bool = True,
    ) -> dict[str, Any]:
        """POST request to abs api.

        login and logout endpoint do not have "api" in url
        """
        _endpoint = f"/api/{endpoint}" if add_api_endpoint else f"/{endpoint}"
        response = await self.session.post(_endpoint, json=data, ssl=self.check_ssl)
        status = response.status
        if status != ABSStatus.STATUS_OK.value:
            raise RuntimeError(f"API post call to {endpoint=} failed.")
        return await response.json()

    async def _get(
        self, endpoint: str, params: dict[str, str | int] | None = None
    ) -> dict[str, Any]:
        """GET request to abs api."""
        _endpoint = f"/api/{endpoint}"
        response = await self.session.get(_endpoint, params=params, ssl=self.check_ssl)
        status = response.status
        if status not in [ABSStatus.STATUS_OK.value, ABSStatus.STATUS_NOT_FOUND.value]:
            raise RuntimeError(f"API get call to {endpoint=} failed.")
        if response.content_type == "application/json":
            return await response.json()
        elif status == ABSStatus.STATUS_NOT_FOUND.value:
            return {}
        else:
            raise RuntimeError("Response must be json.")

    async def _patch(self, endpoint: str, data: dict[str, Any] | None = None) -> None:
        """PATCH request to abs api."""
        _endpoint = f"/api/{endpoint}"
        response = await self.session.patch(_endpoint, json=data, ssl=self.check_ssl)
        status = response.status
        if status != ABSStatus.STATUS_OK.value:
            raise RuntimeError(f"API patch call to {endpoint=} failed.")

    async def login(self, username: str, password: str) -> ABSUser:
        """Obtain user holding token from ABS with username/ password authentication."""
        data = await self._post(
            "login",
            add_api_endpoint=False,
            data={"username": username, "password": password},
        )

        return await self._parse_user(data["user"])

    async def logout(self) -> None:
        """Logout and close aiohttp session."""
        await self._post("logout", add_api_endpoint=False)
        await self.session.close()

    async def get_user(self, id_: str) -> ABSUser:
        """Get an ABS user."""
        data = await self._get(f"users/{id_}")
        return await self._parse_user(data)

    async def _parse_user(self, user_dict: dict[str, Any]) -> ABSUser:
        """Convert User Dict to ABSUser."""
        abs_user = await self._map_attributes(ABSUser, user_dict)

        abs_user.media_progress = []
        for mp in user_dict["mediaProgress"]:
            abs_mp = await self._map_attributes(ABSMediaProgress, mp)
            abs_user.media_progress.append(abs_mp)

        abs_user.bookmarks = []
        for bm in user_dict["bookmarks"]:
            abs_bm = await self._map_attributes(ABSAudioBookmark, bm)
            abs_user.bookmarks.append(abs_bm)

        return abs_user

    async def sync(self) -> None:
        """Update available book and podcast libraries."""
        data = await self._get("libraries")
        libraries = data["libraries"]
        ids = [x.id_ for x in self.audiobook_libraries]
        ids.extend([x.id_ for x in self.podcast_libraries])
        for library in libraries:
            media_type = library["mediaType"]
            if library["id"] not in ids:
                abs_library = ABSLibrary(name=library["name"], id_=library["id"])
                if media_type == "book":
                    self.audiobook_libraries.append(abs_library)
                elif media_type == "podcast":
                    self.podcast_libraries.append(abs_library)
        self.user = await self.get_user(self.user.id_)

    async def get_all_podcasts(self) -> AsyncGenerator[ABSPodcast]:
        """Get all available podcasts."""
        for library in self.podcast_libraries:
            async for podcast in self.get_all_podcasts_by_library(library):
                yield podcast

    async def _get_lib_items(self, lib: ABSLibrary):
        """Get library items with pagination."""
        page_cnt = 0
        while True:
            data = await self._get(
                f"/libraries/{lib.id_}/items",
                params={"limit": LIMIT_ITEMS_PER_PAGE, "page": page_cnt},
            )
            page_cnt += 1
            yield data

    async def get_all_podcasts_by_library(self, lib: ABSLibrary) -> AsyncGenerator[ABSPodcast]:
        """Get all podcasts in a library."""
        async for podcast_data in self._get_lib_items(lib):
            podcast_list = podcast_data.get("results", None)
            if not podcast_list:  # [] if page exceeds
                return

            async def _get_id(plist=podcast_list):
                for entry in plist:
                    yield entry["id"]

            async for id_ in _get_id():
                podcast = await self.get_podcast(id_)
                yield podcast

    async def get_podcast(self, id_: str) -> ABSPodcast:
        """Get a single Podcast by ID."""
        # this endpoint gives more podcast extra data
        podcast = await self._get(f"items/{id_}?expanded=1")
        abs_podcast = await self._map_attributes(ABSPodcast, podcast)

        abs_media = await self._map_attributes(ABSPodcastMedia, podcast["media"])
        abs_podcast.media = abs_media

        abs_metadata = await self._map_attributes(ABSPodcastMetaData, podcast["media"]["metadata"])
        abs_media.metadata = abs_metadata

        abs_podcast.media.episodes = []
        for episode in podcast["media"]["episodes"]:
            abs_episode = await self._map_attributes(ABSPodcastEpisodeExpanded, episode)
            abs_episode.audio_track = await self._map_attributes(
                ABSAudioTrack, episode["audioTrack"]
            )

            abs_podcast.media.episodes.append(abs_episode)
        abs_podcast.media.num_episodes = len(abs_podcast.media.episodes)

        return abs_podcast

    async def _get_progress_ms(
        self,
        endpoint: str,
    ) -> tuple[int | None, bool]:
        data = await self._get(endpoint=endpoint)
        if not data:
            # entry doesn't exist, so it wasn't played yet
            return 0, False
        abs_media_progress: ABSMediaProgress = await self._map_attributes(ABSMediaProgress, data)

        return (
            int(abs_media_progress.current_time * 1000),
            abs_media_progress.is_finished,
        )

    async def get_podcast_progress_ms(
        self, podcast_id: str, episode_id: str
    ) -> tuple[int | None, bool]:
        """Get podcast progress."""
        endpoint = f"me/progress/{podcast_id}/{episode_id}"
        return await self._get_progress_ms(endpoint)

    async def get_audiobook_progress_ms(self, audiobook_id: str) -> tuple[int | None, bool]:
        """Get audiobook progress."""
        endpoint = f"me/progress/{audiobook_id}"
        return await self._get_progress_ms(endpoint)

    async def _update_progress(
        self,
        endpoint: str,
        progress_seconds: int,
        duration_seconds: int,
        is_finished: bool,
    ) -> None:
        """Update progress of media item.

        0 <= progress_percent <= 1

        Notes:
            - progress in abs is percentage
            - multiple parameters in one call don't work in all combinations
            - currentTime is current position in s
            - currentTime works only if duration is sent as well, but then don't
              send progress at the same time.
        """
        await self._patch(
            endpoint,
            data={"isFinished": is_finished},
        )
        if is_finished:
            return
        await self._patch(
            endpoint,
            data={"progress": progress_seconds / duration_seconds},
        )
        await self._patch(
            endpoint,
            data={"duration": duration_seconds, "currentTime": progress_seconds},
        )

    async def update_podcast_progress(
        self,
        podcast_id: str,
        episode_id: str,
        progress_s: int,
        duration_s: int,
        is_finished: bool = False,
    ) -> None:
        """Update podcast episode progress."""
        endpoint = f"me/progress/{podcast_id}/{episode_id}"

        await self._update_progress(endpoint, progress_s, duration_s, is_finished)

    async def update_audiobook_progress(
        self,
        audiobook_id: str,
        progress_s: int,
        duration_s: int,
        is_finished: bool = False,
    ) -> None:
        """Update audiobook progress."""
        endpoint = f"me/progress/{audiobook_id}"
        await self._update_progress(endpoint, progress_s, duration_s, is_finished)

    async def get_all_audiobooks(self) -> AsyncGenerator[ABSAudioBook]:
        """Get all audiobooks."""
        for library in self.audiobook_libraries:
            async for book in self.get_all_audiobooks_by_library(library):
                yield book

    async def get_all_audiobooks_by_library(self, lib: ABSLibrary) -> AsyncGenerator[ABSAudioBook]:
        """Get all Audiobooks in a library."""
        async for audiobook_data in self._get_lib_items(lib):
            audiobook_list = audiobook_data.get("results", None)
            if not audiobook_list:  # [] if page exceeds
                return

            async def _get_id(alist=audiobook_list):
                for entry in alist:
                    yield entry["id"]

            async for id_ in _get_id():
                audiobook = await self.get_audiobook(id_)
                yield audiobook

    async def get_audiobook(self, id_: str) -> ABSAudioBook:
        """Get a single Audiobook by ID."""
        # this endpoint gives more audiobook extra data
        audiobook = await self._get(f"items/{id_}?expanded=1")
        abs_audiobook = await self._map_attributes(ABSAudioBook, audiobook)

        abs_media = await self._map_attributes(ABSAudioBookMedia, audiobook["media"])
        abs_audiobook.media = abs_media

        abs_metadata = await self._map_attributes(
            ABSAudioBookMetaData, audiobook["media"]["metadata"]
        )
        abs_media.metadata = abs_metadata

        abs_metadata.authors = []
        for author in audiobook["media"]["metadata"]["authors"]:
            abs_author = await self._map_attributes(ABSAuthorMinified, author)
            abs_metadata.authors.append(abs_author)

        abs_metadata.series = []
        for series in audiobook["media"]["metadata"]["series"]:
            abs_series = await self._map_attributes(ABSSeriesSequence, series)
            abs_metadata.series.append(abs_series)

        abs_media.chapters = []
        for chapter in audiobook["media"]["chapters"]:
            abs_chapter = await self._map_attributes(ABSAudioBookChapter, chapter)
            abs_media.chapters.append(abs_chapter)

        abs_media.tracks = []
        for track in audiobook["media"]["tracks"]:
            abs_audio_track = await self._map_attributes(ABSAudioTrack, track)
            abs_media.tracks.append(abs_audio_track)

        return abs_audiobook

    async def _map_attributes(self, dclass, api_dict: dict[str, Any]):
        # how do I type hint this function...
        abs_class = dclass()
        for key, value in api_dict.items():
            related_key = camel_to_snake(key)
            try:
                setattr(abs_class, related_key, value)
            except AttributeError:
                continue
        return abs_class
