"""Test we can parse Audiobookshelf models into Music Assistant models."""

import logging
import pathlib

import aiofiles
import pytest
from mashumaro.codecs.json import JSONDecoder
from syrupy.assertion import SnapshotAssertion

from music_assistant.providers.audiobookshelf.abs_schema import (
    ABSAuthorResponse,
    ABSAuthorsResponse,
    ABSLibrariesItemsMinifiedBookResponse,
    ABSLibrariesItemsMinifiedCollectionResponse,
    ABSLibrariesItemsMinifiedPodcastResponse,
    ABSLibrariesResponse,
    ABSLibraryItemExpandedBook,
    ABSLibraryItemExpandedPodcast,
    ABSLoginResponse,
    ABSMediaProgress,
    ABSPlaybackSessionExpanded,
    ABSUser,
)

FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"

AUTHOR_RESPONSE_FIXTURES = list(FIXTURES_DIR.glob("*/ABSAuthorResponse.json"))
AUTHORS_RESPONSE_FIXTURES = list(FIXTURES_DIR.glob("*/ABSAuthorsResponse.json"))
MINIFIED_BOOK_RESPONSE_FIXTURES = list(
    FIXTURES_DIR.glob("*/ABSLibrariesItemsMinifiedBookResponse_*.json")
)
MINIFIED_COLLECTION_RESPONSE_FIXTURES = list(
    FIXTURES_DIR.glob("*/ABSLibrariesItemsMinifiedCollectionResponse.json")
)
MINIFIED_PODCAST_RESPONSE_FIXTURES = list(
    FIXTURES_DIR.glob("*/ABSLibrariesItemsMinifiedPodcastResponse_*.json")
)
LIBRARIES_RESPONSE_FIXTURES = list(FIXTURES_DIR.glob("*/ABSLibrariesResponse.json"))
EXPANDED_BOOK_FIXTURES = list(FIXTURES_DIR.glob("*/ABSLibraryItemExpandedBook_*.json"))
EXPANDED_PODCAST_FIXTURES = list(FIXTURES_DIR.glob("*/ABSLibraryItemExpandedPodcast.json"))
LOGIN_RESPONSE_FIXTURES = list(FIXTURES_DIR.glob("*/ABSLoginResponse.json"))
MEDIA_PROGRESS_FIXTURES = list(FIXTURES_DIR.glob("*/ABSMediaProgress_*.json"))
PLAYBACK_SESSION_EXPANDED_FIXTURES = list(FIXTURES_DIR.glob("*/ABSPlaybackSessionExpanded.json"))
USER_FIXTURES = list(FIXTURES_DIR.glob("*/ABSUser.json"))

AUTHOR_RESPONSE_DECODER = JSONDecoder(ABSAuthorResponse)
AUTHORS_RESPONSE_DECODER = JSONDecoder(ABSAuthorsResponse)
MINIFIED_BOOK_RESPONSE_DECODER = JSONDecoder(ABSLibrariesItemsMinifiedBookResponse)
MINIFIED_COLLECTION_RESPONSE_DECODER = JSONDecoder(ABSLibrariesItemsMinifiedCollectionResponse)
MINIFIED_PODCAST_RESPONSE_DECODER = JSONDecoder(ABSLibrariesItemsMinifiedPodcastResponse)
LIBRARIES_RESPONSE_DECODER = JSONDecoder(ABSLibrariesResponse)
EXPANDED_BOOK_DECODER = JSONDecoder(ABSLibraryItemExpandedBook)
EXPANDED_PODCAST_DECODER = JSONDecoder(ABSLibraryItemExpandedPodcast)
LOGIN_RESPONSE_DECODER = JSONDecoder(ABSLoginResponse)
MEDIA_PROGRESS_DECODER = JSONDecoder(ABSMediaProgress)
PLAYBACK_SESSION_EXPANDED_DECODER = JSONDecoder(ABSPlaybackSessionExpanded)
USER_DECODER = JSONDecoder(ABSUser)


_LOGGER = logging.getLogger(__name__)


# tuple: input, expected output
@pytest.mark.parametrize("json_file", AUTHOR_RESPONSE_FIXTURES)
async def test_parse_author_response(json_file: pathlib.Path, snapshot: SnapshotAssertion) -> None:
    """Author response."""
    async with aiofiles.open(json_file) as fp:
        raw_data = AUTHOR_RESPONSE_DECODER.decode(await fp.read())


@pytest.mark.parametrize("json_file", AUTHORS_RESPONSE_FIXTURES)
async def test_parse_authors_response(json_file: pathlib.Path, snapshot: SnapshotAssertion) -> None:
    """Authors response."""
    async with aiofiles.open(json_file) as fp:
        raw_data = AUTHORS_RESPONSE_DECODER.decode(await fp.read())


@pytest.mark.parametrize("json_file", MINIFIED_BOOK_RESPONSE_FIXTURES)
async def test_parse_minified_book_response(
    json_file: pathlib.Path, snapshot: SnapshotAssertion
) -> None:
    """Minified book response."""
    async with aiofiles.open(json_file) as fp:
        raw_data = MINIFIED_BOOK_RESPONSE_DECODER.decode(await fp.read())


@pytest.mark.parametrize("json_file", MINIFIED_COLLECTION_RESPONSE_FIXTURES)
async def test_parse_minified_collection_response(
    json_file: pathlib.Path, snapshot: SnapshotAssertion
) -> None:
    """Minified collection response."""
    async with aiofiles.open(json_file) as fp:
        raw_data = MINIFIED_COLLECTION_RESPONSE_DECODER.decode(await fp.read())


@pytest.mark.parametrize("json_file", MINIFIED_PODCAST_RESPONSE_FIXTURES)
async def test_parse_minified_podcast_response(
    json_file: pathlib.Path, snapshot: SnapshotAssertion
) -> None:
    """Minified podcast response."""
    async with aiofiles.open(json_file) as fp:
        raw_data = MINIFIED_PODCAST_RESPONSE_DECODER.decode(await fp.read())


@pytest.mark.parametrize("json_file", LIBRARIES_RESPONSE_FIXTURES)
async def test_parse_libraries_response(
    json_file: pathlib.Path, snapshot: SnapshotAssertion
) -> None:
    """Libraries response."""
    async with aiofiles.open(json_file) as fp:
        raw_data = LIBRARIES_RESPONSE_DECODER.decode(await fp.read())


@pytest.mark.parametrize("json_file", EXPANDED_BOOK_FIXTURES)
async def test_parse_expanded_book(json_file: pathlib.Path, snapshot: SnapshotAssertion) -> None:
    """Expanded Book."""
    async with aiofiles.open(json_file) as fp:
        raw_data = EXPANDED_BOOK_DECODER.decode(await fp.read())


@pytest.mark.parametrize("json_file", EXPANDED_PODCAST_FIXTURES)
async def test_parse_expanded_podcast(json_file: pathlib.Path, snapshot: SnapshotAssertion) -> None:
    """Expanded Podcast."""
    async with aiofiles.open(json_file) as fp:
        raw_data = EXPANDED_PODCAST_DECODER.decode(await fp.read())


@pytest.mark.parametrize("json_file", LOGIN_RESPONSE_FIXTURES)
async def test_parse_login_response(json_file: pathlib.Path, snapshot: SnapshotAssertion) -> None:
    """Login response."""
    async with aiofiles.open(json_file) as fp:
        raw_data = LOGIN_RESPONSE_DECODER.decode(await fp.read())


@pytest.mark.parametrize("json_file", MEDIA_PROGRESS_FIXTURES)
async def test_parse_media_progress(json_file: pathlib.Path, snapshot: SnapshotAssertion) -> None:
    """Media progress."""
    async with aiofiles.open(json_file) as fp:
        raw_data = MEDIA_PROGRESS_DECODER.decode(await fp.read())


@pytest.mark.parametrize("json_file", PLAYBACK_SESSION_EXPANDED_FIXTURES)
async def test_parse_playback_session_expanded(
    json_file: pathlib.Path, snapshot: SnapshotAssertion
) -> None:
    """Playback session."""
    async with aiofiles.open(json_file) as fp:
        raw_data = PLAYBACK_SESSION_EXPANDED_DECODER.decode(await fp.read())


@pytest.mark.parametrize("json_file", USER_FIXTURES)
async def test_parse_user(json_file: pathlib.Path, snapshot: SnapshotAssertion) -> None:
    """User."""
    _LOGGER.debug(f"Parsing file {json_file}")
    async with aiofiles.open(json_file) as fp:
        raw_data = USER_DECODER.decode(await fp.read())
