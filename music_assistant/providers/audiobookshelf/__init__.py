"""Audiobookshelf provider for Music Assistant.

Audiobookshelf is abbreviated ABS here.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Sequence
from typing import TYPE_CHECKING

from music_assistant_models.config_entries import ConfigEntry, ConfigValueType, ProviderConfig
from music_assistant_models.enums import (
    ConfigEntryType,
    ContentType,
    ImageType,
    MediaType,
    ProviderFeature,
    StreamType,
)
from music_assistant_models.errors import LoginFailed, MediaNotFoundError
from music_assistant_models.media_items import (
    Audiobook,
    AudioFormat,
    BrowseFolder,
    ItemMapping,
    MediaItemChapter,
    MediaItemImage,
    MediaItemType,
    Podcast,
    PodcastEpisode,
    ProviderMapping,
    UniqueList,
)
from music_assistant_models.streamdetails import StreamDetails

from music_assistant.models.music_provider import MusicProvider
from music_assistant.providers.audiobookshelf.abs_cache_helpers import (
    BrowseExtendedKeys,
    CacheAudiobookLibrary,
    CacheAuthor,
    CacheCollection,
    CachePodcastLibrary,
    CacheSeries,
)
from music_assistant.providers.audiobookshelf.abs_client import ABSClient
from music_assistant.providers.audiobookshelf.abs_schema import (
    ABSDeviceInfo,
    ABSLibraryItemExpandedBook,
    ABSLibraryItemExpandedPodcast,
    ABSLibraryItemMinifiedBook,
    ABSLibraryItemMinifiedPodcast,
    ABSPlaybackSessionExpanded,
    ABSPodcastEpisodeExpanded,
)

if TYPE_CHECKING:
    from music_assistant_models.provider import ProviderManifest

    from music_assistant.mass import MusicAssistant
    from music_assistant.models import ProviderInstanceType

CONF_URL = "url"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_VERIFY_SSL = "verify_ssl"
# optionally hide podcasts with no episodes
CONF_HIDE_EMPTY_PODCASTS = "hide_empty_podcasts"
# make extended browse optional
CONF_EXTENDED_BROWSE = "extended_browse"


async def setup(
    mass: MusicAssistant, manifest: ProviderManifest, config: ProviderConfig
) -> ProviderInstanceType:
    """Initialize provider(instance) with given configuration."""
    return Audiobookshelf(mass, manifest, config)


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
            key=CONF_URL,
            type=ConfigEntryType.STRING,
            label="Server",
            required=True,
            description="The url of the Audiobookshelf server to connect to.",
        ),
        ConfigEntry(
            key=CONF_USERNAME,
            type=ConfigEntryType.STRING,
            label="Username",
            required=True,
            description="The username to authenticate to the remote server.",
        ),
        ConfigEntry(
            key=CONF_PASSWORD,
            type=ConfigEntryType.SECURE_STRING,
            label="Password",
            required=False,
            description="The password to authenticate to the remote server.",
        ),
        ConfigEntry(
            key=CONF_EXTENDED_BROWSE,
            type=ConfigEntryType.BOOLEAN,
            label="Extended browse",
            required=False,
            description="Browse by author, collection and series in the browse function"
            "at the cost of a little longer sync times.",
            default_value=False,
        ),
        ConfigEntry(
            key=CONF_VERIFY_SSL,
            type=ConfigEntryType.BOOLEAN,
            label="Verify SSL",
            required=False,
            description="Whether or not to verify the certificate of SSL/TLS connections.",
            category="advanced",
            default_value=True,
        ),
        ConfigEntry(
            key=CONF_HIDE_EMPTY_PODCASTS,
            type=ConfigEntryType.BOOLEAN,
            label="Hide empty podcasts.",
            required=False,
            description="This will skip podcasts with no episodes associated.",
            category="advanced",
            default_value=False,
        ),
    )


class Audiobookshelf(MusicProvider):
    """Audiobookshelf MusicProvider."""

    @property
    def supported_features(self) -> set[ProviderFeature]:
        """Features supported by this Provider."""
        return {
            ProviderFeature.LIBRARY_PODCASTS,
            ProviderFeature.LIBRARY_AUDIOBOOKS,
            ProviderFeature.BROWSE,
        }

    async def handle_async_init(self) -> None:
        """Pass config values to client and initialize."""
        self._client = ABSClient(mass=self.mass)
        base_url = str(self.config.get_value(CONF_URL))
        username = str(self.config.get_value(CONF_USERNAME))
        try:
            await self._client.init(
                session=self.mass.http_session,
                base_url=base_url,
                username=username,
                password=str(self.config.get_value(CONF_PASSWORD)),
                lookup_key=self.lookup_key,
                logger=self.logger,
                check_ssl=bool(self.config.get_value(CONF_VERIFY_SSL)),
            )
        except RuntimeError:
            # login details were not correct
            raise LoginFailed(f"Login to abs instance at {base_url} failed.")

        # this will be provided when creating sessions or receive already opened sessions
        self.device_info = ABSDeviceInfo(
            device_id=self.lookup_key,
            client_name="Music Assistant",
            client_version=self.mass.version,
            manufacturer="",
            model=self.mass.server_id,
        )

        self.logger.debug(f"Our playback session device_id is {self.lookup_key}")

    async def loaded_in_mass(self) -> None:
        """Call when provider loaded."""
        await self._client._loaded_in_mass()

    async def unload(self, is_removed: bool = False) -> None:
        """
        Handle unload/close of the provider.

        Called when provider is deregistered (e.g. MA exiting or config reloading).
        is_removed will be set to True when the provider is removed from the configuration.
        """
        await self._client.update_cache()
        await self._client.close_all_playback_sessions()
        await self._client.logout()

    @property
    def is_streaming_provider(self) -> bool:
        """Return True if the provider is a streaming provider."""
        # For streaming providers return True here but for local file based providers return False.
        return False

    async def sync_library(self, media_types: tuple[MediaType, ...]) -> None:
        """Run library sync for this provider."""
        await self._client.sync()
        if bool(self.config.get_value(CONF_EXTENDED_BROWSE)):
            await self._client.sync_extended()
        await super().sync_library(media_types=media_types)
        await self._client.update_cache()

    def _parse_podcast(
        self, abs_podcast: ABSLibraryItemExpandedPodcast | ABSLibraryItemMinifiedPodcast
    ) -> Podcast:
        """Translate ABSPodcast to MassPodcast."""
        title = abs_podcast.media.metadata.title
        # Per API doc title may be None.
        if title is None:
            title = "UNKNOWN"
        mass_podcast = Podcast(
            item_id=abs_podcast.id_,
            name=title,
            publisher=abs_podcast.media.metadata.author,
            provider=self.lookup_key,
            provider_mappings={
                ProviderMapping(
                    item_id=abs_podcast.id_,
                    provider_domain=self.domain,
                    provider_instance=self.lookup_key,
                )
            },
        )
        mass_podcast.metadata.description = abs_podcast.media.metadata.description
        token = self._client.token
        image_url = (
            f"{self.config.get_value(CONF_URL)}/api/items/{abs_podcast.id_}/cover?token={token}"
        )
        mass_podcast.metadata.images = UniqueList(
            [MediaItemImage(type=ImageType.THUMB, path=image_url, provider=self.lookup_key)]
        )
        mass_podcast.metadata.explicit = abs_podcast.media.metadata.explicit
        if abs_podcast.media.metadata.language is not None:
            mass_podcast.metadata.languages = UniqueList([abs_podcast.media.metadata.language])
        if abs_podcast.media.metadata.genres is not None:
            mass_podcast.metadata.genres = set(abs_podcast.media.metadata.genres)
        mass_podcast.metadata.release_date = abs_podcast.media.metadata.release_date

        if isinstance(abs_podcast, ABSLibraryItemExpandedPodcast):
            mass_podcast.total_episodes = len(abs_podcast.media.episodes)
        elif isinstance(abs_podcast, ABSLibraryItemMinifiedPodcast):
            mass_podcast.total_episodes = abs_podcast.media.num_episodes

        return mass_podcast

    async def _parse_podcast_episode(
        self,
        episode: ABSPodcastEpisodeExpanded,
        prov_podcast_id: str,
        fallback_episode_cnt: int | None = None,
    ) -> PodcastEpisode:
        """Translate ABSPodcastEpisode to MassPodcastEpisode.

        For an episode the id is set to f"{podcast_id} {episode_id}".
        ABS ids have no spaces, so we can split at a space to retrieve both
        in other functions.
        """
        url = f"{self.config.get_value(CONF_URL)}{episode.audio_track.content_url}"
        episode_id = f"{prov_podcast_id} {episode.id_}"

        if episode.published_at is not None:
            position = -episode.published_at
        else:
            position = 0
            if fallback_episode_cnt is not None:
                position = fallback_episode_cnt
        mass_episode = PodcastEpisode(
            item_id=episode_id,
            provider=self.lookup_key,
            name=episode.title,
            duration=int(episode.duration),
            position=position,
            podcast=ItemMapping(
                item_id=prov_podcast_id,
                provider=self.lookup_key,
                name=episode.title,
                media_type=MediaType.PODCAST,
            ),
            provider_mappings={
                ProviderMapping(
                    item_id=episode_id,
                    provider_domain=self.domain,
                    provider_instance=self.lookup_key,
                    audio_format=AudioFormat(
                        content_type=ContentType.UNKNOWN,
                    ),
                    url=url,
                )
            },
        )
        progress, finished = await self._client.get_podcast_progress_ms(
            prov_podcast_id, episode.id_
        )
        if progress is not None:
            mass_episode.resume_position_ms = progress
            mass_episode.fully_played = finished

        # cover image
        url_base = f"{self.config.get_value(CONF_URL)}"
        url_api = f"/api/items/{prov_podcast_id}/cover?token={self._client.token}"
        url_cover = f"{url_base}{url_api}"
        mass_episode.metadata.images = UniqueList(
            [MediaItemImage(type=ImageType.THUMB, path=url_cover, provider=self.lookup_key)]
        )

        return mass_episode

    async def get_library_podcasts(self) -> AsyncGenerator[Podcast, None]:
        """Retrieve library/subscribed podcasts from the provider."""
        async for abs_podcast in self._client.get_all_podcasts_minified():
            mass_podcast = self._parse_podcast(abs_podcast)
            if (
                bool(self.config.get_value(CONF_HIDE_EMPTY_PODCASTS))
                and mass_podcast.total_episodes == 0
            ):
                continue
            yield mass_podcast

    async def get_podcast(self, prov_podcast_id: str) -> Podcast:
        """Get single podcast."""
        abs_podcast = await self._client.get_podcast_expanded(prov_podcast_id)
        return self._parse_podcast(abs_podcast)

    async def get_podcast_episodes(self, prov_podcast_id: str) -> list[PodcastEpisode]:
        """Get all podcast episodes of podcast."""
        abs_podcast = await self._client.get_podcast_expanded(prov_podcast_id)
        episode_list = []
        episode_cnt = 1
        for abs_episode in abs_podcast.media.episodes:
            mass_episode = await self._parse_podcast_episode(
                abs_episode, prov_podcast_id, episode_cnt
            )
            episode_list.append(mass_episode)
            episode_cnt += 1
        return episode_list

    async def get_podcast_episode(self, prov_episode_id: str) -> PodcastEpisode:
        """Get single podcast episode."""
        prov_podcast_id, e_id = prov_episode_id.split(" ")
        abs_podcast = await self._client.get_podcast_expanded(prov_podcast_id)
        episode_cnt = 1
        for abs_episode in abs_podcast.media.episodes:
            if abs_episode.id_ == e_id:
                return await self._parse_podcast_episode(abs_episode, prov_podcast_id, episode_cnt)

            episode_cnt += 1
        raise MediaNotFoundError("Episode not found")

    async def _parse_audiobook(
        self, abs_audiobook: ABSLibraryItemExpandedBook | ABSLibraryItemMinifiedBook
    ) -> Audiobook:
        mass_audiobook = Audiobook(
            item_id=abs_audiobook.id_,
            provider=self.lookup_key,
            name=abs_audiobook.media.metadata.title,
            duration=int(abs_audiobook.media.duration),
            provider_mappings={
                ProviderMapping(
                    item_id=abs_audiobook.id_,
                    provider_domain=self.domain,
                    provider_instance=self.lookup_key,
                )
            },
            publisher=abs_audiobook.media.metadata.publisher,
        )
        mass_audiobook.metadata.description = abs_audiobook.media.metadata.description
        if abs_audiobook.media.metadata.language is not None:
            mass_audiobook.metadata.languages = UniqueList([abs_audiobook.media.metadata.language])
        mass_audiobook.metadata.release_date = abs_audiobook.media.metadata.published_date
        if abs_audiobook.media.metadata.genres is not None:
            mass_audiobook.metadata.genres = set(abs_audiobook.media.metadata.genres)

        mass_audiobook.metadata.explicit = abs_audiobook.media.metadata.explicit

        # cover
        base_url = f"{self.config.get_value(CONF_URL)}"
        api_url = f"/api/items/{abs_audiobook.id_}/cover?token={self._client.token}"
        cover_url = f"{base_url}{api_url}"
        mass_audiobook.metadata.images = UniqueList(
            [MediaItemImage(type=ImageType.THUMB, path=cover_url, provider=self.lookup_key)]
        )

        # expanded version
        if isinstance(abs_audiobook, ABSLibraryItemExpandedBook):
            authors = UniqueList([x.name for x in abs_audiobook.media.metadata.authors])
            narrators = UniqueList(abs_audiobook.media.metadata.narrators)
            mass_audiobook.authors = authors
            mass_audiobook.narrators = narrators
            chapters = []
            for idx, chapter in enumerate(abs_audiobook.media.chapters):
                chapters.append(
                    MediaItemChapter(
                        position=idx + 1,  # chapter starting at 1
                        name=chapter.title,
                        start=chapter.start,
                        end=chapter.end,
                    )
                )
            mass_audiobook.metadata.chapters = chapters

            progress, finished = await self._client.get_audiobook_progress_ms(abs_audiobook.id_)
            if progress is not None:
                mass_audiobook.resume_position_ms = progress
                mass_audiobook.fully_played = finished
        elif isinstance(abs_audiobook, ABSLibraryItemMinifiedBook):
            mass_audiobook.authors = UniqueList([abs_audiobook.media.metadata.author_name])
            mass_audiobook.narrators = UniqueList([abs_audiobook.media.metadata.narrator_name])

        return mass_audiobook

    async def get_library_audiobooks(self) -> AsyncGenerator[Audiobook, None]:
        """Get Audiobook libraries."""
        async for abs_audiobook in self._client.get_all_audiobooks_minified():
            mass_audiobook = await self._parse_audiobook(abs_audiobook)
            yield mass_audiobook

    async def get_audiobook(self, prov_audiobook_id: str) -> Audiobook:
        """Get a single audiobook."""
        abs_audiobook = await self._client.get_audiobook_expanded(prov_audiobook_id)
        return await self._parse_audiobook(abs_audiobook)

    async def get_streamdetails_from_playback_session(
        self, session: ABSPlaybackSessionExpanded
    ) -> StreamDetails:
        """Give Streamdetails from given session."""
        tracks = session.audio_tracks
        if len(tracks) == 0:
            raise RuntimeError("Playback session has no tracks to play")
        track = tracks[0]
        track_url = track.content_url
        if track_url.split("/")[1] != "hls":
            raise RuntimeError("Did expect HLS stream for session playback")
        item_id = ""
        if session.media_type == "podcast":
            media_type = MediaType.PODCAST_EPISODE
            podcast_id = session.library_item_id
            session_id = session.id_
            episode_id = session.episode_id
            item_id = f"{podcast_id} {episode_id} {session_id}"
        else:
            media_type = MediaType.AUDIOBOOK
            audiobook_id = session.library_item_id
            session_id = session.id_
            item_id = f"{audiobook_id} {session_id}"
        token = self._client.token
        base_url = str(self.config.get_value(CONF_URL))
        media_url = track.content_url
        stream_url = f"{base_url}{media_url}?token={token}"
        return StreamDetails(
            provider=self.lookup_key,
            item_id=item_id,
            audio_format=AudioFormat(
                content_type=ContentType.UNKNOWN,
            ),
            media_type=media_type,
            stream_type=StreamType.HLS,
            path=stream_url,
        )

    async def get_stream_details(
        self, item_id: str, media_type: MediaType = MediaType.TRACK
    ) -> StreamDetails:
        """Get stream of item."""
        # self.logger.debug(f"Streamdetails: {item_id}")
        if media_type == MediaType.PODCAST_EPISODE:
            return await self._get_stream_details_podcast_episode(item_id)
        elif media_type == MediaType.AUDIOBOOK:
            abs_audiobook = await self._client.get_audiobook_expanded(item_id)
            tracks = abs_audiobook.media.tracks
            if len(tracks) == 0:
                raise MediaNotFoundError("Stream not found")
            if len(tracks) > 1:
                session = await self._client.get_playback_session_audiobook(
                    device_info=self.device_info, audiobook_id=item_id
                )
                # small delay, allow abs to launch ffmpeg process
                await asyncio.sleep(1)
                return await self.get_streamdetails_from_playback_session(session)
            return await self._get_stream_details_audiobook(abs_audiobook)
        raise MediaNotFoundError("Stream unknown")

    async def _get_stream_details_audiobook(
        self, abs_audiobook: ABSLibraryItemExpandedBook
    ) -> StreamDetails:
        """Only single audio file in audiobook."""
        self.logger.debug(
            f"Using direct playback for audiobook {abs_audiobook.media.metadata.title}"
        )
        tracks = abs_audiobook.media.tracks
        token = self._client.token
        base_url = str(self.config.get_value(CONF_URL))
        media_url = tracks[0].content_url
        stream_url = f"{base_url}{media_url}?token={token}"
        # audiobookshelf returns information of stream, so we should be able
        # to lift unknown at some point.
        return StreamDetails(
            provider=self.lookup_key,
            item_id=abs_audiobook.id_,
            audio_format=AudioFormat(
                content_type=ContentType.UNKNOWN,
            ),
            media_type=MediaType.AUDIOBOOK,
            stream_type=StreamType.HTTP,
            path=stream_url,
        )

    async def _get_stream_details_podcast_episode(self, podcast_id: str) -> StreamDetails:
        """Stream of a Podcast."""
        abs_podcast_id, abs_episode_id = podcast_id.split(" ")
        abs_episode = None

        abs_podcast = await self._client.get_podcast_expanded(abs_podcast_id)
        for abs_episode in abs_podcast.media.episodes:
            if abs_episode.id_ == abs_episode_id:
                break
        if abs_episode is None:
            raise MediaNotFoundError("Stream not found")
        self.logger.debug(f"Using direct playback for podcast episode {abs_episode.title}")
        token = self._client.token
        base_url = str(self.config.get_value(CONF_URL))
        media_url = abs_episode.audio_track.content_url
        full_url = f"{base_url}{media_url}?token={token}"
        return StreamDetails(
            provider=self.lookup_key,
            item_id=podcast_id,
            audio_format=AudioFormat(
                content_type=ContentType.UNKNOWN,
            ),
            media_type=MediaType.PODCAST_EPISODE,
            stream_type=StreamType.HTTP,
            path=full_url,
        )

    async def on_played(
        self, media_type: MediaType, item_id: str, fully_played: bool, position: int
    ) -> None:
        """Update progress in Audiobookshelf.

        In our case media_type may have 3 values:
            - PODCAST
            - PODCAST_EPISODE
            - AUDIOBOOK
        We ignore PODCAST (function is called on adding a podcast with position=None)

        """
        # self.logger.debug(f"on_played: {media_type=} {item_id=}, {fully_played=} {position=}")
        if media_type == MediaType.PODCAST_EPISODE:
            abs_podcast_id, abs_episode_id = item_id.split(" ")
            mass_podcast_episode = await self.get_podcast_episode(item_id)
            duration = mass_podcast_episode.duration
            self.logger.debug(f"Updating of {media_type.value} named {mass_podcast_episode.name}")
            await self._client.update_podcast_progress(
                podcast_id=abs_podcast_id,
                episode_id=abs_episode_id,
                progress_s=position,
                duration_s=duration,
                is_finished=fully_played,
            )
        if media_type == MediaType.AUDIOBOOK:
            mass_audiobook = await self.get_audiobook(item_id)
            duration = mass_audiobook.duration
            self.logger.debug(f"Updating {media_type.value} named {mass_audiobook.name} progress")
            await self._client.update_audiobook_progress(
                audiobook_id=item_id,
                progress_s=position,
                duration_s=duration,
                is_finished=fully_played,
            )

    async def _browse_simple_root(
        self,
        library_dict: dict[str, CachePodcastLibrary] | dict[str, CacheAudiobookLibrary],
        item_path: str,
    ) -> Sequence[MediaItemType | ItemMapping]:
        """Browse root folder in browse view.

        Helper functions. Shows the library name, ABS supports multiple libraries
        of both podcasts and audiobooks.
        """
        items: list[MediaItemType | ItemMapping] = []
        for library in library_dict.values():
            items.append(
                BrowseFolder(
                    item_id=library.id_,
                    name=library.name,
                    provider=self.lookup_key,
                    path=f"{self.lookup_key}://{item_path}/{library.id_}",
                )
            )
        return items

    async def _browse_simple_lib(
        self,
        library_id: str,
        library_dict: dict[str, CachePodcastLibrary] | dict[str, CacheAudiobookLibrary],
        media_type: MediaType,
    ) -> Sequence[MediaItemType | ItemMapping]:
        """Browse lib folder in browse view.

        Helper functions. Shows the items which are part of an ABS library.
        """
        library = library_dict.get(library_id, None)
        if library is None:
            raise MediaNotFoundError("Lib missing.")

        items: list[MediaItemType | ItemMapping] = []
        if media_type in [MediaType.PODCAST, MediaType.AUDIOBOOK]:
            _attr = None
            if media_type == MediaType.PODCAST:
                _attr = "podcasts"
            elif media_type == MediaType.AUDIOBOOK:
                _attr = "audiobooks"
            assert _attr is not None
            for item_id in getattr(library, _attr):
                mass_item = await self.mass.music.get_library_item_by_prov_id(
                    media_type=media_type,
                    item_id=item_id,
                    provider_instance_id_or_domain=self.lookup_key,
                )
                if mass_item is not None:
                    items.append(mass_item)
        else:
            raise RuntimeError(f"Media type must not be {media_type}")
        return items

    async def _browse_simple(self, path: str) -> Sequence[MediaItemType | ItemMapping]:
        """Browse simple.

        Browse shows Library name in media within (initial implementation).
        """
        item_path = path.split("://", 1)[1]
        if not item_path:  # root
            return await super().browse(path)

        # HANDLE ROOT PATH
        if item_path == "audiobooks":
            book_dict = self._client.audiobook_libraries.libraries
            return await self._browse_simple_root(book_dict, item_path)
        elif item_path == "podcasts":
            podcast_dict = self._client.podcast_libraries.libraries
            return await self._browse_simple_root(podcast_dict, item_path)

        # HANDLE WITHIN LIBRARY
        library_type, library_id = item_path.split("/")
        if library_type == "audiobooks":
            audiobook_dict = self._client.audiobook_libraries.libraries
            media_type = MediaType.AUDIOBOOK
            return await self._browse_simple_lib(library_id, audiobook_dict, media_type)
        elif library_type == "podcasts":
            podcast_dict = self._client.podcast_libraries.libraries
            media_type = MediaType.PODCAST
            return await self._browse_simple_lib(library_id, podcast_dict, media_type)
        else:
            raise MediaNotFoundError("Specified Lib Type unknown")

    async def browse(self, path: str) -> Sequence[MediaItemType | ItemMapping]:
        """Browse features shows libraries names."""
        if bool(self.config.get_value(CONF_EXTENDED_BROWSE)):
            return await self._browse_expanded(path)
        else:
            return await self._browse_simple(path)

    async def _browse_expanded_audiobooks(
        self, full_path: str, sub_paths: list[str]
    ) -> list[MediaItemType | ItemMapping]:
        items: list[MediaItemType | ItemMapping] = []
        if not sub_paths:
            for folder_name in BrowseExtendedKeys:
                if folder_name == BrowseExtendedKeys.PODCASTS.value:
                    continue
                items.append(
                    BrowseFolder(
                        item_id=folder_name.lower(),
                        name=f"All {folder_name}",
                        provider=self.lookup_key,
                        path=f"{full_path}/{folder_name.lower()}",
                    )
                )
            return items

        client_lib = self._client.audiobook_libraries
        target = None
        for sub_path in sub_paths:
            target = (
                client_lib.get(sub_path)
                if isinstance(client_lib, dict)
                else getattr(client_lib, sub_path)
            )
        if target is None:
            raise RuntimeError("Unable to browse.")
        if isinstance(target, dict):
            for id_, params in target.items():
                items.append(
                    BrowseFolder(
                        item_id=id_,
                        name=params.name,
                        provider=self.lookup_key,
                        path=f"{full_path}/{id_}",
                    )
                )
        elif isinstance(target, CacheAuthor | CacheCollection | CacheSeries):
            for book_id in target.audiobooks:
                mass_item = await self.mass.music.get_library_item_by_prov_id(
                    media_type=MediaType.AUDIOBOOK,
                    item_id=book_id,
                    provider_instance_id_or_domain=self.lookup_key,
                )
                if mass_item is not None:
                    items.append(mass_item)
        elif isinstance(target, CacheAudiobookLibrary):
            for folder_name in BrowseExtendedKeys:
                if folder_name in [
                    BrowseExtendedKeys.PODCASTS.value,
                    BrowseExtendedKeys.LIBRARIES.value,
                ]:
                    continue
                items.append(
                    BrowseFolder(
                        item_id=folder_name.lower(),
                        name=folder_name,
                        provider=self.lookup_key,
                        path=f"{full_path}/{folder_name.lower()}",
                    )
                )
        elif isinstance(target, list | UniqueList):
            # only media items are in a list:
            for item_id in target:
                mass_item = await self.mass.music.get_library_item_by_prov_id(
                    media_type=MediaType.AUDIOBOOK,
                    item_id=item_id,
                    provider_instance_id_or_domain=self.lookup_key,
                )
                if mass_item is not None:
                    items.append(mass_item)
        return items

    async def _browse_expanded_podcasts(
        self, full_path: str, sub_paths: list[str]
    ) -> list[MediaItemType | ItemMapping]:
        """Podcasts are either by themselves or in playlists."""
        items: list[MediaItemType | ItemMapping] = []
        if not sub_paths:
            folder_names = [BrowseExtendedKeys.PODCASTS.value, BrowseExtendedKeys.LIBRARIES.value]
            for folder_name in folder_names:
                items.append(
                    BrowseFolder(
                        item_id=folder_name.lower(),
                        name=f"All {folder_name}",
                        provider=self.lookup_key,
                        path=f"{full_path}/{folder_name.lower()}",
                    )
                )
            return items

        client_lib = self._client.podcast_libraries
        target = None
        for sub_path in sub_paths:
            target = (
                client_lib.get(sub_path)
                if isinstance(client_lib, dict)
                else getattr(client_lib, sub_path)
            )
        if target is None:
            raise RuntimeError("Unable to browse.")

        if isinstance(target, dict):
            for id_, params in target.items():
                items.append(
                    BrowseFolder(
                        item_id=id_,
                        name=params.name,
                        provider=self.lookup_key,
                        path=f"{full_path}/{id_}",
                    )
                )
        elif isinstance(target, list | UniqueList):
            for item_id in target:
                mass_item = await self.mass.music.get_library_item_by_prov_id(
                    media_type=MediaType.PODCAST,
                    item_id=item_id,
                    provider_instance_id_or_domain=self.lookup_key,
                )
                if mass_item is not None:
                    items.append(mass_item)
        elif isinstance(target, CachePodcastLibrary):
            for podcast_id in target.podcasts:
                mass_item = await self.mass.music.get_library_item_by_prov_id(
                    media_type=MediaType.PODCAST,
                    item_id=podcast_id,
                    provider_instance_id_or_domain=self.lookup_key,
                )
                if mass_item is not None:
                    items.append(mass_item)
        return items

    async def _browse_expanded(self, path: str) -> Sequence[MediaItemType | ItemMapping]:
        """Browse expanded."""
        items: list[MediaItemType | ItemMapping] = []
        item_path = path.split("://", 1)[1]
        if not item_path:  # root
            # Podcast and Audiobook libraries cannot overlap
            # in ABS, so we offer the choice here
            for key in (BrowseExtendedKeys.PODCASTS.value, BrowseExtendedKeys.AUDIOBOOKS.value):
                items.append(
                    BrowseFolder(
                        item_id=key,
                        name=key,
                        provider=self.lookup_key,
                        path=f"{self.lookup_key}://{key.lower()}",
                    )
                )
        else:
            sub_paths = item_path.split("/")
            if sub_paths[0] == BrowseExtendedKeys.PODCASTS.value.lower():
                return await self._browse_expanded_podcasts(full_path=path, sub_paths=sub_paths[1:])
            else:
                return await self._browse_expanded_audiobooks(
                    full_path=path, sub_paths=sub_paths[1:]
                )

        return items
