"""Schema definition of Audiobookshelf.

https://api.audiobookshelf.org/
"""

from dataclasses import dataclass


class ABSSchema:
    """For Type Hinting."""


@dataclass(init=False)
class ABSAudioTrack(ABSSchema):
    """ABS audioTrack.

    https://api.audiobookshelf.org/#audio-track
    """

    index: int
    start_offset: float = 0.0
    duration: float = 0.0
    title: str = ""
    content_url: str = ""
    mime_type: str = ""
    # metadata: # not needed for mass application


@dataclass(init=False)
class ABSPodcastEpisodeExpanded(ABSSchema):
    """ABSPodcastEpisode.

    https://api.audiobookshelf.org/#podcast-episode
    """

    library_item_id: str
    id_: str
    index: int
    # audio_file: # not needed for mass application
    published_at: int  # ms posix epoch
    added_at: int  # ms posix epoch
    updated_at: int  # ms posix epoch
    audio_track: ABSAudioTrack
    size: int  # in bytes
    season: str = ""
    episode: str = ""
    episode_type: str = ""
    title: str = ""
    subtitle: str = ""
    description: str = ""
    enclosure: str = ""
    pub_date: str = ""
    guid: str = ""
    # chapters
    duration: float = 0.0


@dataclass(init=False)
class ABSPodcastMetaData(ABSSchema):
    """PodcastMetaData https://api.audiobookshelf.org/?shell#podcasts."""

    title: str | None
    author: str | None
    description: str | None
    release_date: str | None
    genres: list[str]
    feed_url: str | None
    image_url: str | None
    itunes_page_url: str | None
    itunes_id: int | None
    itunes_artist_id: int | None
    explicit: bool
    language: str | None
    type_: str | None


@dataclass(init=False)
class ABSPodcastMedia(ABSSchema):
    """ABSPodcastMedia."""

    metadata: ABSPodcastMetaData
    cover_path: str
    episodes: list[ABSPodcastEpisodeExpanded]
    num_episodes: int = 0


@dataclass(init=False)
class ABSPodcast(ABSSchema):
    """ABSPodcast.

    Depending on endpoint we get different results. This class does not
    fully reflect https://api.audiobookshelf.org/#podcast.
    """

    id_: str
    media: ABSPodcastMedia


@dataclass(init=False)
class ABSAuthorMinified(ABSSchema):
    """ABSAuthor.

    https://api.audiobookshelf.org/#author
    """

    id_: str
    name: str


@dataclass(init=False)
class ABSSeriesSequence(ABSSchema):
    """Series Sequence.

    https://api.audiobookshelf.org/#series
    """

    id_: str
    name: str
    sequence: str | None


@dataclass(init=False)
class ABSAudioBookMetaData(ABSSchema):
    """ABSAudioBookMetaData.

    https://api.audiobookshelf.org/#book-metadata
    """

    title: str
    subtitle: str
    authors: list[ABSAuthorMinified]
    narrators: list[str]
    series: list[ABSSeriesSequence]
    genres: list[str]
    published_year: str | None
    published_date: str | None
    publisher: str | None
    description: str | None
    isbn: str | None
    asin: str | None
    language: str | None
    explicit: bool


@dataclass(init=False)
class ABSAudioBookChapter(ABSSchema):
    """
    ABSAudioBookChapter.

    https://api.audiobookshelf.org/#book-chapter
    """

    id_: int
    start: float
    end: float
    title: str


@dataclass(init=False)
class ABSAudioBookMedia(ABSSchema):
    """ABSAudioBookMedia.

    Helper class due to API endpoint used.
    """

    metadata: ABSAudioBookMetaData
    cover_path: str
    chapters: list[ABSAudioBookChapter]
    duration: float
    tracks: list[ABSAudioTrack]


@dataclass(init=False)
class ABSAudioBook(ABSSchema):
    """ABSAudioBook.

    Depending on endpoint we get different results. This class does not
    full reflect https://api.audiobookshelf.org/#book.
    """

    id_: str
    media: ABSAudioBookMedia


@dataclass(init=False)
class ABSMediaProgress(ABSSchema):
    """ABSMediaProgress.

    https://api.audiobookshelf.org/#media-progress
    """

    id_: str
    library_item_id: str
    episode_id: str
    duration: float  # seconds
    progress: float  # percent 0->1
    current_time: float  # seconds
    is_finished: bool
    hide_from_continue_listening: bool
    last_update: int  # ms epoch
    started_at: int  # ms epoch
    finished_at: int  # ms epoch


@dataclass(init=False)
class ABSAudioBookmark(ABSSchema):
    """ABSAudioBookmark."""

    library_item_id: str
    title: str
    time: float  # seconds
    created_at: int  # unix epoch ms


@dataclass(init=False)
class ABSUser(ABSSchema):
    """ABSUser.

    only attributes we need for mass
    https://api.audiobookshelf.org/#user
    """

    id_: str
    token: str
    username: str
    media_progress: list[ABSMediaProgress]
    bookmarks: list[ABSAudioBookmark]


@dataclass
class ABSLibrary(ABSSchema):
    """ABSLibrary.

    Only attributes we need
    """

    id_: str
    name: str
