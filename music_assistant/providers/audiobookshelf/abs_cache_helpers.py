"""Cache Helpers.

These are not ABS Schema classes, but are
used when syncing the library for caching.
"""

from dataclasses import dataclass, field

from mashumaro import DataClassDictMixin
from music_assistant_models.media_items import UniqueList


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


@dataclass
class CacheablePodcastLibraries(DataClassDictMixin):
    """PodcastLibraries."""

    libraries: UniqueList[PodcastLibrary] = field(default_factory=UniqueList[PodcastLibrary])


@dataclass
class CacheableAudiobookLibraries(DataClassDictMixin):
    """AudiobookLibraries."""

    libraries: UniqueList[AudiobookLibrary] = field(default_factory=UniqueList[AudiobookLibrary])
