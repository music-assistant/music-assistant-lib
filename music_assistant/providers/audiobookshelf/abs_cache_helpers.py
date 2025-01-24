"""Cache Helpers.

These are not ABS Schema classes, but are
used when syncing the library for caching.
"""

from dataclasses import dataclass, field

from mashumaro import DataClassDictMixin
from music_assistant_models.media_items import UniqueList


@dataclass
class _SCBase(DataClassDictMixin):
    id_: str
    name: str = ""
    books: UniqueList[str] = field(default_factory=UniqueList[str])


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
    books: UniqueList[str] = field(default_factory=UniqueList[str])
    series: UniqueList[str] = field(default_factory=UniqueList[str])


@dataclass
class _Library(DataClassDictMixin):
    """Helper class to store ABSLibrary, and the ids of the items associated."""

    id_: str
    name: str = ""
    item_ids: UniqueList[str] = field(default_factory=UniqueList[str])


@dataclass
class CachePodcastLibrary(_Library):
    """PodcastLibrary."""


@dataclass
class CacheAudiobookLibrary(_Library):
    """AudiobookLibrary."""

    authors: dict[str, CacheAuthor] = field(default_factory=dict)
    series: dict[str, CacheSeries] = field(default_factory=dict)
    collections: dict[str, CacheCollection] = field(default_factory=dict)


@dataclass
class CachePodcastLibraries(DataClassDictMixin):
    """PodcastLibraries."""

    # id: PodcastLibrary
    libraries: dict[str, CachePodcastLibrary] = field(default_factory=dict)


@dataclass
class CacheAudiobookLibraries(DataClassDictMixin):
    """AudiobookLibraries."""

    libraries: dict[str, CacheAudiobookLibrary] = field(default_factory=dict)
