"""Helper for parsing and using audible api."""

import hashlib
import html
import json
import re
from typing import Any
from urllib.parse import parse_qs, urlparse

import audible
import audible.register
from audible import AsyncClient
from music_assistant_models.enums import (
    ContentType,
    ImageType,
    MediaType,
    StreamType,
)
from music_assistant_models.errors import LoginFailed
from music_assistant_models.media_items import (
    Audiobook,
    AudioFormat,
    MediaItemChapter,
    MediaItemImage,
    ProviderMapping,
    UniqueList,
)
from music_assistant_models.streamdetails import StreamDetails

from music_assistant.mass import MusicAssistant

CACHE_DOMAIN = "audible"
CACHE_CATEGORY_API = "api"
CACHE_CATEGORY_AUDIOBOOK = "audiobook"
CACHE_CATEGORY_CHAPTERS = "chapters"


class AudibleHelper:
    """Helper for parsing and using audible api."""

    mass: MusicAssistant
    client: AsyncClient
    provider_domain: str
    provider_instance: str

    def __init__(
        self,
        mass: MusicAssistant,
        client: AsyncClient,
        provider_domain: str,
        provider_instance: str,
    ):
        """Initialize the Audible Helper."""
        self.mass = mass
        self.client = client
        self.provider_domain = provider_domain
        self.provider_instance = provider_instance

    async def get_library(self):
        """Fetch the user's library with pagination."""
        response_groups = [
            "contributors",
            "media",
            "product_attrs",
            "product_desc",
            "product_details",
            "product_extended_attrs",
        ]

        page = 1
        page_size = 50

        while True:
            library = await self._call_api(
                "library",
                response_groups=",".join(response_groups),
                page=page,
                num_results=page_size,
            )

            items = library.get("items", [])
            if not items:
                break

            for audiobook_data in items:
                asin = audiobook_data.get("asin")
                cached_book = await self.mass.cache.get(
                    key=asin, base_key=CACHE_DOMAIN, category=CACHE_CATEGORY_AUDIOBOOK, default=None
                )

                if cached_book is not None:
                    album = await self._parse_audiobook(cached_book)
                    yield album
                else:
                    album = await self._parse_audiobook(audiobook_data)
                    yield album

            # Check if we've reached the end
            total_items = library.get("total_results", 0)
            if page * page_size >= total_items:
                break

            page += 1

    async def get_audiobook(self, asin: str, use_cache=True) -> Audiobook:
        """Fetch the audiobook by asin."""
        if use_cache:
            cached_book = await self.mass.cache.get(
                key=asin, base_key=CACHE_DOMAIN, category=CACHE_CATEGORY_AUDIOBOOK, default=None
            )
            if cached_book is not None:
                return await self._parse_audiobook(cached_book)
        response = await self._call_api(
            f"library/{asin}",
            response_groups="""
                contributors, media, price, product_attrs, product_desc, product_details,
                product_extended_attrs,is_finished
                """,
        )

        if response is None:
            return None
        await self.mass.cache.set(
            key=asin,
            base_key=CACHE_DOMAIN,
            category=CACHE_CATEGORY_AUDIOBOOK,
            data=response.get("item"),
        )
        return await self._parse_audiobook(response.get("item"))

    async def get_stream(self, asin: str) -> StreamDetails:
        """Get stream details for a track (audiobook chapter)."""
        chapters = await self._fetch_chapters(asin=asin)

        duration = sum(chapter["length_ms"] for chapter in chapters) / 1000

        playback_info = await self.client.post(
            f"content/{asin}/licenserequest",
            body={
                "quality": "High",
                "response_groups": """content_reference,certificate""",
                "consumption_type": "Streaming",
                "supported_media_features": {
                    "codecs": ["mp4a.40.2", "mp4a.40.42"],
                    "drm_types": [
                        "Hls",
                    ],
                },
                "spatial": False,
            },
        )
        size = (
            playback_info.get("content_license")
            .get("content_metadata")
            .get("content_reference")
            .get("content_size_in_bytes", 0)
        )

        m3u8_url = playback_info.get("content_license").get("license_response")
        acr = playback_info.get("content_license").get("acr")
        return StreamDetails(
            provider=self.provider_instance,
            size=size,
            item_id=f"{asin}",
            audio_format=AudioFormat(content_type=ContentType.AAC),
            media_type=MediaType.AUDIOBOOK,
            stream_type=StreamType.HTTP,
            path=m3u8_url,
            can_seek=True,
            duration=duration,
            data={"acr": acr},
        )

    async def _fetch_chapters(self, asin: str):
        chapters_data: list[Any] = await self.mass.cache.get(
            base_key=CACHE_DOMAIN, category=CACHE_CATEGORY_CHAPTERS, key=asin, default=[]
        )
        if not chapters_data:
            response = await self._call_api(
                f"content/{asin}/metadata",
                response_groups="chapter_info, always-returned, content_reference, content_url",
                chapter_titles_type="Flat",
            )
            chapters_data = response.get("content_metadata").get("chapter_info").get("chapters")
            await self.mass.cache.set(
                base_key=CACHE_DOMAIN,
                category=CACHE_CATEGORY_CHAPTERS,
                key=asin,
                data=chapters_data,
            )
        return chapters_data

    async def get_last_postion(self, asin):
        """Fetch last position of asin."""
        response = await self._call_api("annotations/lastpositions", asins=asin)
        return (
            response.get("asin_last_position_heard_annots")[0]
            .get("last_position_heard")
            .get("position_ms")
        )

    async def set_last_position(self, asin: str, pos: int):
        """Report last position."""

    async def _call_api(self: str, path: str, **kwargs):
        params_str = json.dumps(kwargs, sort_keys=True)
        params_hash = hashlib.md5(params_str.encode()).hexdigest()
        cache_key_with_params = f"{path}:{params_hash}"

        response = await self.mass.cache.get(
            key=cache_key_with_params, base_key=CACHE_DOMAIN, category="api"
        )
        if not response:
            response = await self.client.get(path, **kwargs)
            await self.mass.cache.set(
                key=cache_key_with_params, base_key=CACHE_DOMAIN, data=response
            )
        return response

    async def _parse_audiobook(self, audiobook_data) -> Audiobook:
        asin = audiobook_data.get("asin")
        title = audiobook_data.get("title")
        authors = []
        narrators = []
        for narrator in audiobook_data.get("narrators", []):
            narrators.append(narrator.get("name"))
        for author in audiobook_data.get("authors", []):
            authors.append(author.get("name"))
        chapters_data = await self._fetch_chapters(asin=asin)
        duration = sum(chapter["length_ms"] for chapter in chapters_data) / 1000
        book = Audiobook(
            item_id=asin,
            provider=self.provider_instance,
            name=title,
            duration=duration,
            provider_mappings={
                ProviderMapping(
                    item_id=asin,
                    provider_domain=self.provider_domain,
                    provider_instance=self.provider_instance,
                )
            },
            publisher=audiobook_data.get("publisher_name"),
            authors=UniqueList(authors),
            narrators=UniqueList(narrators),
        )
        book.metadata.copyright = audiobook_data.get("copyright")
        book.metadata.description = _html_to_txt(audiobook_data.get("extended_product_description"))
        book.metadata.languages = [audiobook_data.get("language")]
        book.metadata.release_date = audiobook_data.get("release_date")
        reviews = audiobook_data.get("editorial_reviews", [])
        if reviews:
            book.metadata.review = _html_to_txt(reviews[0])
        # book.metadata.preview = ""
        book.metadata.genres = [
            genre.replace("_", " ") for genre in audiobook_data.get("platinum_keywords")
        ]
        book.metadata.images = [
            MediaItemImage(
                type=ImageType.THUMB,
                path=audiobook_data.get("product_images").get("500"),
                provider=self.provider_instance,
                remotely_accessible=True,
            ),
            MediaItemImage(
                type=ImageType.CLEARART,
                path=audiobook_data.get("product_images").get("500"),
                provider=self.provider_instance,
                remotely_accessible=True,
            ),
        ]

        chapters = []
        for index, chapter_data in enumerate(chapters_data):
            start = int(chapter_data.get("start_offset_sec"))
            length = int(chapter_data.get("length_ms")) / 1000
            chapters.append(
                MediaItemChapter(
                    position=index, name=chapter_data.get("title"), start=start, end=start + length
                )
            )
        book.metadata.chapters = chapters
        book.resume_position_ms = await self.get_last_postion(asin=asin)
        return book

    def deregister(self):
        """Deregister this provider from Audible."""
        self.client.auth.deregister_device()


def _html_to_txt(html_text):
    txt = html.unescape(html_text)
    tags = re.findall("<[^>]+>", txt)
    for tag in tags:
        txt = txt.replace(tag, "")
    return txt


# Audible Authorization


def audible_get_auth_info(locale):
    """Generate the login URL and return code_verifier and serial."""
    locale_obj = audible.localization.Locale(locale)
    code_verifier = audible.login.create_code_verifier()
    # Build OAuth URL
    oauth_url, serial = audible.login.build_oauth_url(
        country_code=locale_obj.country_code,
        domain=locale_obj.domain,
        market_place_id=locale_obj.market_place_id,
        code_verifier=code_verifier,
        with_username=False,
    )
    return code_verifier.decode(), oauth_url, serial


def audible_custom_login(code_verifier, response_url, serial, locale):
    """Complete the authentication using the code_verifier, response_url, and serial."""
    auth = audible.Authenticator()
    auth.locale = audible.localization.Locale(locale)
    response_url_parsed = urlparse(response_url)
    parsed_qs = parse_qs(response_url_parsed.query)
    authorization_code = parsed_qs.get("openid.oa2.authorization_code")
    if not authorization_code:
        raise LoginFailed("Authorization code not found in the provided URL.")
    authorization_code = authorization_code[0]
    registration_data = audible.register.register(
        authorization_code=authorization_code,
        code_verifier=code_verifier.encode(),
        domain=auth.locale.domain,
        serial=serial,
    )
    auth._update_attrs(**registration_data)
    return auth
