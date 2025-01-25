"""Cache Helpers.

These are not ABS Schema classes, but are
used when syncing the library for caching.
"""

from dataclasses import dataclass, field
from enum import StrEnum

from mashumaro import DataClassDictMixin
from music_assistant_models.media_items import UniqueList


class BrowseExtendedKeys(StrEnum):
    """BrowseExtendedKeys."""

    AUTHORS = "Authors"
    SERIES = "Series"
    COLLECTIONS = "Collections"
    AUDIOBOOKS = "Audiobooks"
    PODCASTS = "Podcasts"
    LIBRARIES = "Libraries"


@dataclass
class _SCBase(DataClassDictMixin):
    id_: str
    name: str = ""
    audiobooks: UniqueList[str] = field(default_factory=UniqueList[str])


@dataclass
class CacheSeries(_SCBase):
    """Series."""


@dataclass
class CacheCollection(_SCBase):
    """collections."""


@dataclass
class CacheAuthor(DataClassDictMixin):
    """Author."""

    id_: str
    name: str = ""
    audiobooks: UniqueList[str] = field(default_factory=UniqueList[str])
    series: UniqueList[str] = field(default_factory=UniqueList[str])


@dataclass
class _Library(DataClassDictMixin):
    """Helper class to store ABSLibrary, and the ids of the items associated."""

    id_: str
    name: str = ""


@dataclass
class CachePodcastLibrary(_Library):
    """PodcastLibrary."""

    podcasts: UniqueList[str] = field(default_factory=UniqueList[str])


@dataclass
class CacheAudiobookLibrary(_Library):
    """AudiobookLibrary.

    Here we keep what is specific to that single library
    """

    authors: dict[str, CacheAuthor] = field(default_factory=dict)
    series: dict[str, CacheSeries] = field(default_factory=dict)
    collections: dict[str, CacheCollection] = field(default_factory=dict)
    audiobooks: UniqueList[str] = field(default_factory=UniqueList[str])


@dataclass
class CachePodcastLibraries(DataClassDictMixin):
    """PodcastLibraries."""

    # id: PodcastLibrary
    libraries: dict[str, CachePodcastLibrary] = field(default_factory=dict)
    podcasts: UniqueList[str] = field(default_factory=UniqueList[str])


@dataclass
class CacheAudiobookLibraries(DataClassDictMixin):
    """AudiobookLibraries.

    Here we keep items from all libraries.
    """

    libraries: dict[str, CacheAudiobookLibrary] = field(default_factory=dict)
    series: dict[str, CacheSeries] = field(default_factory=dict)
    authors: dict[str, CacheAuthor] = field(default_factory=dict)
    collections: dict[str, CacheCollection] = field(default_factory=dict)
    audiobooks: UniqueList[str] = field(default_factory=UniqueList[str])
