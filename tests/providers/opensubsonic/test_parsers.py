"""Test we can parse Jellyfin models into Music Assistant models."""

import json
import pathlib

import aiofiles
import pytest
from libopensonic.media.artist import Artist, ArtistInfo
from syrupy.assertion import SnapshotAssertion

from music_assistant.providers.opensubsonic.parsers import parse_artist

FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"
ARTIST_FIXTURES = list(FIXTURES_DIR.glob("artists/*.artist.json"))


@pytest.mark.parametrize("example", ARTIST_FIXTURES, ids=lambda val: str(val.stem))
async def test_parse_artists(example: pathlib.Path, snapshot: SnapshotAssertion) -> None:
    """Test we can parse artists."""
    async with aiofiles.open(example) as fp:
        artist = Artist(json.loads(await fp.read()))

    parsed = parse_artist("xx-instance-id-xx", artist).to_dict()
    # sort external Ids to ensure they are always in the same order for snapshot testing
    parsed["external_ids"].sort()
    assert snapshot == parsed

    # Find the corresponding info file
    example_info = example.with_suffix("").with_suffix(".info.json")
    async with aiofiles.open(example_info) as fp:
        artist_info = ArtistInfo(json.loads(await fp.read()))

    parsed = parse_artist("xx-instance-id-xx", artist, artist_info).to_dict()
    # sort external Ids to ensure they are always in the same order for snapshot testing
    parsed["external_ids"].sort()
    assert snapshot == parsed
