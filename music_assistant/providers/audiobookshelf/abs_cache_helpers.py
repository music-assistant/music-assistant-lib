"""Cache Helpers.

These are not ABS Schema classes, but are
used when syncing the library for caching.
"""

from dataclasses import dataclass, field

from mashumaro import DataClassDictMixin
from music_assistant_models.media_items import UniqueList


@dataclass
class Series(DataClassDictMixin):
    """Series."""

    id_: str
    name: str = ""
    books: UniqueList[str] = field(default_factory=UniqueList[str])


@dataclass
class Author(DataClassDictMixin):
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
class PodcastLibrary(_Library):
    """PodcastLibrary."""


@dataclass
class AudiobookLibrary(_Library):
    """AudiobookLibrary."""

    authors: dict[str, Author] = field(default_factory=dict)
    series: dict[str, Series] = field(default_factory=dict)


@dataclass
class CacheablePodcastLibraries(DataClassDictMixin):
    """PodcastLibraries."""

    # id: PodcastLibrary
    libraries: dict[str, PodcastLibrary] = field(default_factory=dict)


@dataclass
class CacheableAudiobookLibraries(DataClassDictMixin):
    """AudiobookLibraries."""

    libraries: dict[str, AudiobookLibrary] = field(default_factory=dict)
