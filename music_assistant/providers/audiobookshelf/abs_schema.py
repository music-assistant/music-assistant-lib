"""Schema definition of Audiobookshelf (ABS).

https://api.audiobookshelf.org/

Some schema definitions have variants. Take book as example:
https://api.audiobookshelf.org/#book
Naming Scheme in this file:
    - the standard definition has nothing added
    - minified/ expanded: here, 2 additional variants

Sometimes these variants remove or change attributes in such a way, that
it makes sense to define a base class for inheritance.
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
    """ABS audioTrack. No variants.

    https://api.audiobookshelf.org/#audio-track
    """

    # index: int | None
    # start_offset: Annotated[float, Alias("startOffset")] = 0.0
    # duration: float = 0.0
    # title: str = ""
    content_url: Annotated[str, Alias("contentUrl")] = ""
    mime_type: str = ""
    # metadata: # not needed for mass application


@dataclass
class ABSBookChapter(BaseModel):
    """
    ABSBookChapter. No variants.

    https://api.audiobookshelf.org/#book-chapter
    """

    id_: Annotated[int, Alias("id")]
    start: float
    end: float
    title: str


@dataclass
class ABSAudioBookmark(BaseModel):
    """ABSAudioBookmark. No variants.

    https://api.audiobookshelf.org/#audio-bookmark
    """

    library_item_id: Annotated[str, Alias("libraryItemId")]
    title: str
    time: float  # seconds
    created_at: Annotated[int, Alias("createdAt")]  # unix epoch ms


@dataclass
class ABSUserPermissions(BaseModel):
    """ABSUserPermissions. No variants.

    https://api.audiobookshelf.org/#user-permissions
    """

    # download: bool
    # update: bool
    # delete: bool
    # upload: bool
    # access_all_libraries: Annotated[bool, Alias("accessAllLibraries")]
    # access_all_tags: Annotated[bool, Alias("accessAllTags")]
    # access_explicit_content: Annotated[bool, Alias("accessExplicitContent")]


@dataclass
class ABSLibrary(BaseModel):
    """ABSLibrary. No variants.

    https://api.audiobookshelf.org/#library
    Only attributes we need
    """

    id_: Annotated[str, Alias("id")]
    name: str
    # folders
    # displayOrder: Integer
    # icon: String
    media_type: Annotated[str, Alias("mediaType")]
    # provider: str
    # settings
    # created_at: Annotated[int, Alias("createdAt")]
    # last_update: Annotated[int, Alias("lastUpdate")]


@dataclass
class ABSDeviceInfo(BaseModel):
    """ABSDeviceInfo. No variants.

    https://api.audiobookshelf.org/#device-info-parameters
    https://api.audiobookshelf.org/#device-info
    https://github.com/advplyr/audiobookshelf/blob/master/server/objects/DeviceInfo.js#L3
    """

    device_id: Annotated[str, Alias("deviceId")] = ""
    client_name: Annotated[str, Alias("clientName")] = ""
    client_version: Annotated[str, Alias("clientVersion")] = ""
    manufacturer: str = ""
    model: str = ""
    # sdkVersion # meant for an Android client


### Author: https://api.audiobookshelf.org/#author


@dataclass
class ABSAuthorMinified(BaseModel):
    """ABSAuthorMinified.

    https://api.audiobookshelf.org/#author
    """

    id_: Annotated[str, Alias("id")]
    name: str


@dataclass
class ABSAuthor(ABSAuthorMinified):
    """ABSAuthor."""

    # asin: str | None
    description: str | None
    # image_path: Annotated[str | None, Alias("imagePath")]
    # added_at: Annotated[int, Alias("addedAt")]  # ms epoch
    # updated_at: Annotated[int, Alias("updatedAt")]  # ms epoch


@dataclass
class ABSAuthorExpanded(ABSAuthor):
    """ABSAuthorExpanded."""

    num_books: Annotated[int, Alias("numBooks")]


### Series: https://api.audiobookshelf.org/#series


@dataclass
class _ABSSeriesBase(BaseModel):
    """_ABSSeriesBase."""

    id_: Annotated[str, Alias("id")]
    name: str


@dataclass
class ABSSeries(_ABSSeriesBase):
    """ABSSeries."""

    description: str | None
    # added_at: Annotated[int, Alias("addedAt")]  # ms epoch
    # updated_at: Annotated[int, Alias("updatedAt")]  # ms epoch


@dataclass
class ABSSeriesNumBooks(_ABSSeriesBase):
    """ABSSeriesNumBooks."""

    name_ignore_prefix: Annotated[str, Alias("nameIgnorePrefix")]
    library_item_ids: Annotated[list[str], Alias("libraryItemIds")]
    num_books: Annotated[int, Alias("numBooks")]


@dataclass
class ABSSeriesSequence(BaseModel):
    """Series Sequence.

    https://api.audiobookshelf.org/#series
    """

    id_: Annotated[str, Alias("id")]
    name: str
    sequence: str | None


# another variant, ABSSeriesBooks is further down


###  https://api.audiobookshelf.org/#media-progress


@dataclass
class ABSMediaProgress(BaseModel):
    """ABSMediaProgress."""

    id_: Annotated[str, Alias("id")]
    library_item_id: Annotated[str, Alias("libraryItemId")]
    episode_id: Annotated[str, Alias("episodeId")]
    duration: float  # seconds
    progress: float  # percent 0->1
    current_time: Annotated[float, Alias("currentTime")]  # seconds
    is_finished: Annotated[bool, Alias("isFinished")]
    # hide_from_continue_listening: Annotated[bool, Alias("hideFromContinueListening")]
    # last_update: Annotated[int, Alias("lastUpdate")]  # ms epoch
    # started_at: Annotated[int, Alias("startedAt")]  # ms epoch
    # finished_at: Annotated[int | None, Alias("finishedAt")]  # ms epoch


# two additional progress variants, 'with media' book and podcast, further down.


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
    # series_hide_from_continue_listening: Annotated[
    #     list[str], Alias("seriesHideFromContinueListening")
    # ]
    # bookmarks: list[ABSAudioBookmark]
    # is_active: Annotated[bool, Alias("isActive")]
    # is_locked: Annotated[bool, Alias("isLocked")]
    # last_seen: Annotated[int | None, Alias("lastSeen")]
    # created_at: Annotated[int, Alias("createdAt")]
    # permissions: ABSUserPermissions
    libraries_accessible: Annotated[list[str], Alias("librariesAccessible")]

    # this seems to be missing
    # item_tags_accessible: Annotated[list[str], Alias("itemTagsAccessible")]


# two additional user variants do exist


class ABSPlayMethod(Enum):
    """Playback method in playback session."""

    DIRECT_PLAY = 0
    DIRECT_STREAM = 1
    TRANSCODE = 2
    LOCAL = 3


### https://api.audiobookshelf.org/#playback-session


@dataclass
class ABSPlaybackSession(BaseModel):
    """ABSPlaybackSession."""

    id_: Annotated[str, Alias("id")]
    # user_id: Annotated[str, Alias("userId")]
    # library_id: Annotated[str, Alias("libraryId")]
    library_item_id: Annotated[str, Alias("libraryItemId")]
    episode_id: Annotated[str | None, Alias("episodeId")]
    media_type: Annotated[str, Alias("mediaType")]
    # media_metadata: Annotated[ABSPodcastMetaData | ABSAudioBookMetaData, Alias("mediaMetadata")]
    # chapters: list[ABSAudioBookChapter]
    display_title: Annotated[str, Alias("displayTitle")]
    # display_author: Annotated[str, Alias("displayAuthor")]
    # cover_path: Annotated[str, Alias("coverPath")]
    # duration: float
    # 0: direct play, 1: direct stream, 2: transcode, 3: local
    # play_method: Annotated[ABSPlayMethod, Alias("playMethod")]
    # media_player: Annotated[str, Alias("mediaPlayer")]
    # device_info: Annotated[ABSDeviceInfo, Alias("deviceInfo")]
    # server_version: Annotated[str, Alias("serverVersion")]
    # YYYY-MM-DD
    # date: str
    # day_of_week: Annotated[str, Alias("dayOfWeek")]
    # time_listening: Annotated[float, Alias("timeListening")]  # s
    # start_time: Annotated[float, Alias("startTime")]  # s
    # current_time: Annotated[float, Alias("currentTime")]  # s
    # started_at: Annotated[int, Alias("startedAt")]  # ms since Unix Epoch
    # updated_at: Annotated[int, Alias("updatedAt")]  # ms since Unix Epoch


@dataclass
class ABSPlaybackSessionExpanded(ABSPlaybackSession):
    """ABSPlaybackSessionExpanded."""

    audio_tracks: Annotated[list[ABSAudioTrack], Alias("audioTracks")]

    # videoTrack:
    # libraryItem:


### https://api.audiobookshelf.org/#podcast-metadata


@dataclass
class ABSPodcastMetadata(BaseModel):
    """ABSPodcastMetadata."""

    title: str | None
    author: str | None
    description: str | None
    release_date: Annotated[str | None, Alias("releaseDate")]
    genres: list[str] | None
    # feed_url: Annotated[str | None, Alias("feedUrl")]
    # image_url: Annotated[str | None, Alias("imageUrl")]
    # itunes_page_url: Annotated[str | None, Alias("itunesPageUrl")]
    # itunes_id: Annotated[int | None, Alias("itunesId")]
    # itunes_artist_id: Annotated[int | None, Alias("itunesArtistId")]
    explicit: bool
    language: str | None
    # type_: Annotated[str | None, Alias("type")]


@dataclass
class ABSPodcastMetadataMinified(ABSPodcastMetadata):
    """ABSPodcastMetadataMinified."""

    # title_ignore_prefix: Annotated[str, Alias("titleIgnorePrefix")]


ABSPodcastMetaDataExpanded = ABSPodcastMetadataMinified

### https://api.audiobookshelf.org/#podcast-episode


@dataclass
class ABSPodcastEpisode(BaseModel):
    """ABSPodcastEpisode."""

    library_item_id: Annotated[str, Alias("libraryItemId")]
    id_: Annotated[str, Alias("id")]
    index: int | None
    # audio_file: # not needed for mass application
    published_at: Annotated[int | None, Alias("publishedAt")]  # ms posix epoch
    added_at: Annotated[int | None, Alias("addedAt")]  # ms posix epoch
    updated_at: Annotated[int | None, Alias("updatedAt")]  # ms posix epoch
    # season: str = ""
    episode: str = ""
    # episode_type: Annotated[str, Alias("episodeType")] = ""
    title: str = ""
    subtitle: str = ""
    description: str = ""
    # enclosure: str = ""
    pub_date: Annotated[str, Alias("pubDate")] = ""
    # guid: str = ""
    # chapters


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
    # updated_at: Annotated[int | None, Alias("updatedAt")]  # ms posix epoch
    audio_track: Annotated[ABSAudioTrack, Alias("audioTrack")]
    # size: int  # in bytes
    # season: str = ""
    episode: str = ""
    # episode_type: Annotated[str, Alias("episodeType")] = ""
    title: str = ""
    subtitle: str = ""
    description: str = ""
    # enclosure: str = ""
    # pub_date: Annotated[str, Alias("pubDate")] = ""
    # guid: str = ""
    # chapters
    duration: float = 0.0


@dataclass
class _ABSPodcastBase(BaseModel):
    """_ABSPodcastBase."""

    cover_path: Annotated[str, Alias("coverPath")]


### https://api.audiobookshelf.org/#podcast


@dataclass
class ABSPodcast(_ABSPodcastBase):
    """ABSPodcast."""

    metadata: ABSPodcastMetadata
    library_item_id: Annotated[str, Alias("libraryItemId")]
    tags: list[str]
    episodes: list[ABSPodcastEpisode]


@dataclass
class ABSPodcastMinified(_ABSPodcastBase):
    """ABSPodcastMinified."""

    metadata: ABSPodcastMetadataMinified
    # size: int  # bytes
    num_episodes: Annotated[int, Alias("numEpisodes")] = 0


@dataclass
class ABSPodcastExpanded(_ABSPodcastBase):
    """ABSPodcastEpisodeExpanded."""

    size: int  # bytes
    metadata: ABSPodcastMetaDataExpanded
    episodes: list[ABSPodcastEpisodeExpanded]


### https://api.audiobookshelf.org/#book-metadata


@dataclass
class _ABSBookMetadataBase(BaseModel):
    """_ABSBookMetadataBase."""

    title: str
    subtitle: str
    genres: list[str] | None
    published_year: Annotated[str | None, Alias("publishedYear")]
    published_date: Annotated[str | None, Alias("publishedDate")]
    publisher: str | None
    description: str | None
    # isbn: str | None
    # asin: str | None
    language: str | None
    explicit: bool


@dataclass
class ABSBookMetadata(_ABSBookMetadataBase):
    """ABSBookMetadata."""

    authors: list[ABSAuthorMinified]
    narrators: list[str]
    series: list[ABSSeriesSequence]


@dataclass
class ABSBookMetadataMinified(_ABSBookMetadataBase):
    """ABSBookMetadataMinified."""

    # these are normally there
    # title_ignore_prefix: Annotated[str, Alias("titleIgnorePrefix")]
    author_name: Annotated[str, Alias("authorName")]
    # author_name_lf: Annotated[str, Alias("authorNameLF")]
    narrator_name: Annotated[str, Alias("narratorName")]
    series_name: Annotated[str, Alias("seriesName")]


@dataclass
class ABSBookMetadataExpanded(ABSBookMetadata, ABSBookMetadataMinified):
    """ABSAudioBookMetaDataExpanded."""


### https://api.audiobookshelf.org/#book


@dataclass
class _ABSBookBase(BaseModel):
    """_ABSBookBase."""

    tags: list[str]
    cover_path: Annotated[str | None, Alias("coverPath")]


@dataclass
class ABSBook(_ABSBookBase):
    """ABSBook."""

    library_item_id: Annotated[str, Alias("libraryItemId")]
    metadata: ABSBookMetadata
    # audioFiles
    chapters: list[ABSBookChapter]
    # ebookFile


@dataclass
class ABSBookMinified(_ABSBookBase):
    """ABSBookBase."""

    metadata: ABSBookMetadataMinified
    # num_tracks: Annotated[int, Alias("numTracks")]
    # num_audiofiles: Annotated[int, Alias("numAudioFiles")]
    num_chapters: Annotated[int, Alias("numChapters")]
    duration: float  # in s
    # size: int  # in bytes
    # ebookFormat


@dataclass
class ABSBookExpanded(_ABSBookBase):
    """ABSBookExpanded."""

    library_item_id: Annotated[str, Alias("libraryItemId")]
    metadata: ABSBookMetadataExpanded
    chapters: list[ABSBookChapter]
    duration: float
    size: int  # bytes
    tracks: list[ABSAudioTrack]


### https://api.audiobookshelf.org/#library-item


@dataclass
class _ABSLibraryItemBase(BaseModel):
    """_ABSLibraryItemBase."""

    id_: Annotated[str, Alias("id")]
    # ino: str
    # library_id: Annotated[str, Alias("libraryId")]
    # folder_id: Annotated[str, Alias("folderId")]
    # path: str
    # relative_path: Annotated[str, Alias("relPath")]
    # is_file: Annotated[bool, Alias("isFile")]
    # last_modified_ms: Annotated[int, Alias("mtimeMs")]  # epoch
    # last_changed_ms: Annotated[int, Alias("ctimeMs")]  # epoch
    # birthtime_ms: Annotated[int, Alias("birthtimeMs")]  # epoch
    # added_at: Annotated[int, Alias("addedAt")]  # ms epoch
    # updated_at: Annotated[int, Alias("updatedAt")]  # ms epoch
    # is_missing: Annotated[bool, Alias("isMissing")]
    # is_invalid: Annotated[bool, Alias("isInvalid")]
    media_type: Annotated[str, Alias("mediaType")]


@dataclass
class _ABSLibraryItem(_ABSLibraryItemBase):
    """ABSLibraryItem."""

    # last_scan: Annotated[int | None, Alias("lastScan")]  # ms epoch
    # scan_version: Annotated[str | None, Alias("scanVersion")]
    # libraryFiles


@dataclass
class ABSLibraryItemBook(_ABSLibraryItem):
    """ABSLibraryItemBook."""

    media: ABSBook


@dataclass
class ABSLibraryItemBookSeries(ABSLibraryItemBook):
    """ABSLibraryItemNormalBookSeries.

    Special class, when having the scheme of SeriesBooks, see
    https://api.audiobookshelf.org/#series, it gets an extra
    sequence key.
    """

    sequence: int


@dataclass
class ABSLibraryItemPodcast(_ABSLibraryItem):
    """ABSLibraryItemPodcast."""

    media: ABSPodcast


@dataclass
class _ABSLibraryItemMinified(_ABSLibraryItemBase):
    """ABSLibraryItemMinified."""

    num_files: Annotated[int, Alias("numFiles")]
    size: int  # bytes


@dataclass
class ABSLibraryItemMinifiedBook(_ABSLibraryItemMinified):
    """ABSLibraryItemMinifiedBook."""

    media: ABSBookMinified


@dataclass
class ABSLibraryItemMinifiedPodcast(_ABSLibraryItemMinified):
    """ABSLibraryItemMinifiedBook."""

    media: ABSPodcastMinified


@dataclass
class _ABSLibraryItemExpanded(_ABSLibraryItemBase):
    """ABSLibraryItemExpanded."""

    size: int  # bytes


@dataclass
class ABSLibraryItemExpandedBook(_ABSLibraryItemExpanded):
    """ABSLibraryItemExpanded."""

    media: ABSBookExpanded


@dataclass
class ABSLibraryItemExpandedPodcast(_ABSLibraryItemExpanded):
    """ABSLibraryItemExpanded."""

    media: ABSPodcastExpanded


# extra classes down here so they can make proper references


@dataclass
class ABSSeriesBooks(_ABSSeriesBase):
    """ABSSeriesBooks."""

    added_at: Annotated[int, Alias("addedAt")]  # ms epoch
    # name_ignore_prefix: Annotated[str, Alias("nameIgnorePrefix")]
    # name_ignore_prefix_sort: Annotated[str, Alias("nameIgnorePrefixSort")]
    # type_: Annotated[str, Alias("type")]
    books: list[ABSLibraryItemBookSeries]
    total_duration: Annotated[float, Alias("totalDuration")]  # s


@dataclass
class ABSMediaProgressWithMediaBook(ABSMediaProgress):
    """ABSMediaProgressWithMediaBook."""

    media: ABSBookExpanded


@dataclass
class ABSMediaProgressWithMediaPodcast(ABSMediaProgress):
    """ABSMediaProgressWithMediaBook."""

    media: ABSPodcastExpanded
    episode: ABSPodcastEpisode


### Response to API Requests


@dataclass
class ABSLoginResponse(BaseModel):
    """ABSLoginResponse."""

    user: ABSUser

    # this seems to be missing
    # user_default_library_id: Annotated[str, Alias("defaultLibraryId")]


@dataclass
class ABSLibrariesResponse(BaseModel):
    """ABSLibrariesResponse."""

    libraries: list[ABSLibrary]


@dataclass
class ABSSessionsResponse(BaseModel):
    """Response to GET http://abs.example.com/api/me/listening-sessions."""

    total: int
    num_pages: Annotated[int, Alias("numPages")]
    items_per_page: Annotated[int, Alias("itemsPerPage")]
    sessions: list[ABSPlaybackSession]


@dataclass
class ABSAuthorsResponse(BaseModel):
    """ABSAuthorsResponse."""

    authors: list[ABSAuthorExpanded]


@dataclass
class ABSLibrariesItemsMinifiedBookResponse(BaseModel):
    """ABSLibrariesItemsResponse.

    https://api.audiobookshelf.org/#get-a-library-39-s-items
    No matter what options I append to the request, I always end up with
    minified items. Maybe a bug in abs. If that would be fixed, there is
    potential for reduced in API calls.
    """

    results: list[ABSLibraryItemMinifiedBook]


@dataclass
class ABSLibrariesItemsMinifiedPodcastResponse(BaseModel):
    """ABSLibrariesItemsResponse.

    see above.
    """

    results: list[ABSLibraryItemMinifiedPodcast]


### Requests to API we can make


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


@dataclass
class ABSSessionUpdate(BaseModel):
    """
    ABSSessionUpdate.

    Can be used as optional data to sync or closing request.
    unit is seconds
    """

    current_time: Annotated[float, Alias("currentTime")]
    time_listened: Annotated[float, Alias("timeListened")]
    duration: float
