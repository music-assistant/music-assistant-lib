"""Schema definition of Audiobookshelf.

https://api.audiobookshelf.org/
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Annotated

from mashumaro.config import BaseConfig
from mashumaro.mixins.json import DataClassJSONMixin
from mashumaro.types import Alias


class BaseModel(DataClassJSONMixin):
    """BaseModel for Schema.

    forbid_extra_keys: response of API may have more keys than used by us
    serialize_by_alias: when using to_json(), we get the Alias keys
    """

    class Config(BaseConfig):
        """Config."""

        forbid_extra_keys = False
        serialize_by_alias = True


@dataclass
class ABSAudioTrack(BaseModel):
    """ABS audioTrack.

    https://api.audiobookshelf.org/#audio-track
    """

    index: int
    start_offset: Annotated[float, Alias("startOffset")] = 0.0
    duration: float = 0.0
    title: str = ""
    content_url: Annotated[str, Alias("contentUrl")] = ""
    mime_type: str = ""
    # metadata: # not needed for mass application


@dataclass
class ABSPodcastEpisodeExpanded(BaseModel):
    """ABSPodcastEpisode.

    https://api.audiobookshelf.org/#podcast-episode
    """

    library_item_id: Annotated[str, Alias("libraryItemId")]
    id_: Annotated[str, Alias("id")]
    index: int | None
    # audio_file: # not needed for mass application
    published_at: Annotated[int | None, Alias("publishedAt")]  # ms posix epoch
    added_at: Annotated[int | None, Alias("addedAt")]  # ms posix epoch
    updated_at: Annotated[int | None, Alias("updatedAt")]  # ms posix epoch
    audio_track: Annotated[ABSAudioTrack, Alias("audioTrack")]
    size: int  # in bytes
    season: str = ""
    episode: str = ""
    episode_type: Annotated[str, Alias("episodeType")] = ""
    title: str = ""
    subtitle: str = ""
    description: str = ""
    enclosure: str = ""
    pub_date: Annotated[str, Alias("pubDate")] = ""
    guid: str = ""
    # chapters
    duration: float = 0.0


@dataclass
class ABSPodcastMetaData(BaseModel):
    """PodcastMetaData https://api.audiobookshelf.org/?shell#podcasts."""

    title: str | None
    author: str | None
    description: str | None
    release_date: Annotated[str | None, Alias("releaseDate")]
    genres: list[str] | None
    feed_url: Annotated[str | None, Alias("feedUrl")]
    image_url: Annotated[str | None, Alias("imageUrl")]
    itunes_page_url: Annotated[str | None, Alias("itunesPageUrl")]
    itunes_id: Annotated[int | None, Alias("itunesId")]
    itunes_artist_id: Annotated[int | None, Alias("itunesArtistId")]
    explicit: bool
    language: str | None
    type_: Annotated[str | None, Alias("type")]


@dataclass
class ABSPodcastMedia(BaseModel):
    """ABSPodcastMedia."""

    metadata: ABSPodcastMetaData
    cover_path: Annotated[str, Alias("coverPath")]
    episodes: list[ABSPodcastEpisodeExpanded]
    num_episodes: Annotated[int, Alias("numEpisodes")] = 0


@dataclass
class ABSPodcast(BaseModel):
    """ABSPodcast.

    Depending on endpoint we get different results. This class does not
    fully reflect https://api.audiobookshelf.org/#podcast.
    """

    id_: Annotated[str, Alias("id")]
    media: ABSPodcastMedia


@dataclass
class ABSAuthorMinified(BaseModel):
    """ABSAuthor.

    https://api.audiobookshelf.org/#author
    """

    id_: Annotated[str, Alias("id")]
    name: str


@dataclass
class ABSSeriesSequence(BaseModel):
    """Series Sequence.

    https://api.audiobookshelf.org/#series
    """

    id_: Annotated[str, Alias("id")]
    name: str
    sequence: str | None


@dataclass
class ABSAudioBookMetaData(BaseModel):
    """ABSAudioBookMetaData.

    https://api.audiobookshelf.org/#book-metadata
    """

    title: str
    subtitle: str
    authors: list[ABSAuthorMinified]
    narrators: list[str]
    series: list[ABSSeriesSequence]
    genres: list[str] | None
    published_year: Annotated[str | None, Alias("publishedYear")]
    published_date: Annotated[str | None, Alias("publishedDate")]
    publisher: str | None
    description: str | None
    isbn: str | None
    asin: str | None
    language: str | None
    explicit: bool


@dataclass
class ABSAudioBookChapter(BaseModel):
    """
    ABSAudioBookChapter.

    https://api.audiobookshelf.org/#book-chapter
    """

    id_: Annotated[int, Alias("id")]
    start: float
    end: float
    title: str


@dataclass
class ABSAudioBookMedia(BaseModel):
    """ABSAudioBookMedia.

    Helper class due to API endpoint used.
    """

    metadata: ABSAudioBookMetaData
    cover_path: Annotated[str, Alias("coverPath")]
    chapters: list[ABSAudioBookChapter]
    duration: float
    tracks: list[ABSAudioTrack]


@dataclass
class ABSAudioBook(BaseModel):
    """ABSAudioBook.

    Depending on endpoint we get different results. This class does not
    full reflect https://api.audiobookshelf.org/#book.
    """

    id_: Annotated[str, Alias("id")]
    media: ABSAudioBookMedia


@dataclass
class ABSMediaProgress(BaseModel):
    """ABSMediaProgress.

    https://api.audiobookshelf.org/#media-progress
    """

    id_: Annotated[str, Alias("id")]
    library_item_id: Annotated[str, Alias("libraryItemId")]
    episode_id: Annotated[str, Alias("episodeId")]
    duration: float  # seconds
    progress: float  # percent 0->1
    current_time: Annotated[float, Alias("currentTime")]  # seconds
    is_finished: Annotated[bool, Alias("isFinished")]
    hide_from_continue_listening: Annotated[bool, Alias("hideFromContinueListening")]
    last_update: Annotated[int, Alias("lastUpdate")]  # ms epoch
    started_at: Annotated[int, Alias("startedAt")]  # ms epoch
    finished_at: Annotated[int | None, Alias("finishedAt")]  # ms epoch


@dataclass
class ABSAudioBookmark(BaseModel):
    """ABSAudioBookmark."""

    library_item_id: Annotated[str, Alias("libraryItemId")]
    title: str
    time: float  # seconds
    created_at: Annotated[int, Alias("createdAt")]  # unix epoch ms


@dataclass
class ABSUserPermissions(BaseModel):
    """ABSUserPermissions."""

    download: bool
    update: bool
    delete: bool
    upload: bool
    access_all_libraries: Annotated[bool, Alias("accessAllLibraries")]
    access_all_tags: Annotated[bool, Alias("accessAllTags")]
    access_explicit_content: Annotated[bool, Alias("accessExplicitContent")]


@dataclass
class ABSUser(BaseModel):
    """ABSUser.

    only attributes we need for mass
    https://api.audiobookshelf.org/#user
    """

    id_: Annotated[str, Alias("id")]
    username: str
    type_: Annotated[str, Alias("type")]
    token: str
    media_progress: Annotated[list[ABSMediaProgress], Alias("mediaProgress")]
    series_hide_from_continue_listening: Annotated[
        list[str], Alias("seriesHideFromContinueListening")
    ]
    bookmarks: list[ABSAudioBookmark]
    is_active: Annotated[bool, Alias("isActive")]
    is_locked: Annotated[bool, Alias("isLocked")]
    last_seen: Annotated[int | None, Alias("lastSeen")]
    created_at: Annotated[int, Alias("createdAt")]
    permissions: ABSUserPermissions
    libraries_accessible: Annotated[list[str], Alias("librariesAccessible")]

    # this seems to be missing
    # item_tags_accessible: Annotated[list[str], Alias("itemTagsAccessible")]


@dataclass
class ABSLoginResponse(BaseModel):
    """ABSLoginResponse."""

    user: ABSUser

    # this seems to be missing
    # user_default_library_id: Annotated[str, Alias("defaultLibraryId")]


@dataclass
class ABSLibrary(BaseModel):
    """ABSLibrary.

    Only attributes we need
    """

    id_: Annotated[str, Alias("id")]
    name: str
    # folders
    # displayOrder: Integer
    # icon: String
    media_type: Annotated[str, Alias("mediaType")]
    provider: str
    # settings
    created_at: Annotated[int, Alias("createdAt")]
    last_update: Annotated[int, Alias("lastUpdate")]


@dataclass
class ABSLibrariesResponse(BaseModel):
    """ABSLibrariesResponse."""

    libraries: list[ABSLibrary]


@dataclass
class ABSLibraryItem(BaseModel):
    """ABSLibraryItem."""

    id_: Annotated[str, Alias("id")]


@dataclass
class ABSLibrariesItemsResponse(BaseModel):
    """ABSLibrariesItemsResponse.

    https://api.audiobookshelf.org/#get-a-library-39-s-items
    """

    results: list[ABSLibraryItem]


# Schema to enable sessions:
@dataclass
class ABSDeviceInfo(BaseModel):
    """ABSDeviceInfo.

    https://api.audiobookshelf.org/#device-info-parameters
    """

    device_id: Annotated[str, Alias("deviceId")]
    client_name: Annotated[str, Alias("clientName")]
    client_version: Annotated[str, Alias("clientVersion")]
    manufacturer: str
    model: str
    # sdkVersion # meant for an Android client


@dataclass
class ABSPlayRequest(BaseModel):
    """ABSPlayRequest.

    https://api.audiobookshelf.org/#play-a-library-item-or-podcast-episode
    """

    device_info: Annotated[ABSDeviceInfo, Alias("deviceInfo")]
    force_direct_play: Annotated[bool, Alias("forceDirectPlay")] = False
    force_transcode: Annotated[bool, Alias("forceTranscode")] = False
    supported_mime_types: Annotated[list[str], Alias("supportedMimeTypes")] = field(
        default_factory=list
    )
    media_player: Annotated[str, Alias("mediaPlayer")] = "unknown"


class ABSPlayMethod(Enum):
    """Playback method in playback session."""

    DIRECT_PLAY = 0
    DIRECT_STREAM = 1
    TRANSCODE = 2
    LOCAL = 3


@dataclass
class ABSPlaybackSessionExpanded(BaseModel):
    """ABSPlaybackSessionExpanded.

    https://api.audiobookshelf.org/#play-method
    """

    id_: Annotated[str, Alias("id")]
    user_id: Annotated[str, Alias("userId")]
    library_id: Annotated[str, Alias("libraryId")]
    library_item_id: Annotated[str, Alias("libraryItemId")]
    episode_id: Annotated[str | None, Alias("episodeId")]
    media_type: Annotated[str, Alias("mediaType")]
    media_metadata: Annotated[ABSPodcastMetaData | ABSAudioBookMetaData, Alias("mediaMetadata")]
    chapters: list[ABSAudioBookChapter]
    display_title: Annotated[str, Alias("displayTitle")]
    display_author: Annotated[str, Alias("displayAuthor")]
    cover_path: Annotated[str, Alias("coverPath")]
    duration: float
    # 0: direct play, 1: direct stream, 2: transcode, 3: local
    play_method: Annotated[ABSPlayMethod, Alias("playMethod")]
    media_player: Annotated[str, Alias("mediaPlayer")]
    device_info: Annotated[ABSDeviceInfo, Alias("deviceInfo")]
    server_version: Annotated[str, Alias("serverVersion")]
    # YYYY-MM-DD
    date: str
    day_of_week: Annotated[str, Alias("dayOfWeek")]
    time_listening: Annotated[float, Alias("timeListening")]  # s
    start_time: Annotated[float, Alias("startTime")]  # s
    current_time: Annotated[float, Alias("currentTime")]  # s
    started_at: Annotated[int, Alias("startedAt")]  # ms since Unix Epoch
    updated_at: Annotated[int, Alias("updatedAt")]  # ms since Unix Epoch
    audio_tracks: Annotated[list[ABSAudioTrack], Alias("audioTracks")]

    # videoTrack:
    # libraryItem:
