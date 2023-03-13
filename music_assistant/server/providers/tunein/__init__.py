"""Tune-In musicprovider support for MusicAssistant."""
from __future__ import annotations

from collections.abc import AsyncGenerator
from time import time

from asyncio_throttle import Throttler

from music_assistant.common.helpers.util import create_sort_name
from music_assistant.common.models.enums import ProviderFeature
from music_assistant.common.models.errors import LoginFailed, MediaNotFoundError
from music_assistant.common.models.media_items import (
    ContentType,
    ImageType,
    MediaItemImage,
    MediaType,
    ProviderMapping,
    Radio,
    StreamDetails,
)
from music_assistant.constants import CONF_USERNAME
from music_assistant.server.helpers.audio import get_radio_stream
from music_assistant.server.helpers.playlists import fetch_playlist
from music_assistant.server.helpers.tags import parse_tags
from music_assistant.server.models.music_provider import MusicProvider

SUPPORTED_FEATURES = (
    ProviderFeature.LIBRARY_RADIOS,
    ProviderFeature.BROWSE,
)


class TuneInProvider(MusicProvider):
    """Provider implementation for Tune In."""

    _throttler: Throttler

    @property
    def supported_features(self) -> tuple[ProviderFeature, ...]:
        """Return the features supported by this Provider."""
        return SUPPORTED_FEATURES

    async def setup(self) -> None:
        """Handle async initialization of the provider."""
        self._throttler = Throttler(rate_limit=1, period=1)

        if not self.config.get_value(CONF_USERNAME):
            raise LoginFailed("Username is invalid")
        if "@" in self.config.get_value(CONF_USERNAME):
            self.logger.warning(
                "Emailadress detected instead of username, "
                "it is advised to use the tunein username instead of email."
            )

    async def get_library_radios(self) -> AsyncGenerator[Radio, None]:
        """Retrieve library/subscribed radio stations from the provider."""

        async def parse_items(items: list[dict], folder: str = None) -> AsyncGenerator[Radio, None]:
            for item in items:
                item_type = item.get("type", "")
                if item_type == "audio":
                    if "preset_id" not in item:
                        continue
                    # each radio station can have multiple streams add each one as different quality
                    stream_info = await self.__get_data("Tune.ashx", id=item["preset_id"])
                    for stream in stream_info["body"]:
                        yield await self._parse_radio(item, stream, folder)
                elif item_type == "link" and item.get("item") == "url":
                    # custom url
                    yield await self._parse_radio(item)
                elif item_type == "link":
                    # stations are in sublevel (new style)
                    if sublevel := await self.__get_data(item["URL"], render="json"):
                        async for subitem in parse_items(sublevel["body"], item["text"]):
                            yield subitem
                elif item.get("children"):
                    # stations are in sublevel (old style ?)
                    async for subitem in parse_items(item["children"], item["text"]):
                        yield subitem

        data = await self.__get_data("Browse.ashx", c="presets")
        if data and "body" in data:
            async for item in parse_items(data["body"]):
                yield item

    async def get_radio(self, prov_radio_id: str) -> Radio:
        """Get radio station details."""
        if not prov_radio_id.startswith("http"):
            prov_radio_id, media_type = prov_radio_id.split("--", 1)
            params = {"c": "composite", "detail": "listing", "id": prov_radio_id}
            result = await self.__get_data("Describe.ashx", **params)
            if result and result.get("body") and result["body"][0].get("children"):
                item = result["body"][0]["children"][0]
                stream_info = await self.__get_data("Tune.ashx", id=prov_radio_id)
                for stream in stream_info["body"]:
                    if stream["media_type"] != media_type:
                        continue
                    return await self._parse_radio(item, stream)
        # fallback - e.g. for handle custom urls ...
        async for radio in self.get_library_radios():
            if radio.item_id == prov_radio_id:
                return radio
        return None

    async def _parse_radio(
        self, details: dict, stream: dict | None = None, folder: str | None = None
    ) -> Radio:
        """Parse Radio object from json obj returned from api."""
        if "name" in details:
            name = details["name"]
        else:
            # parse name from text attr
            name = details["text"]
            if " | " in name:
                name = name.split(" | ")[1]
            name = name.split(" (")[0]

        if stream is None:
            # custom url (no stream object present)
            url = details["URL"]
            item_id = url
            media_info = await parse_tags(url)
            content_type = ContentType.try_parse(media_info.format)
            bit_rate = media_info.bit_rate
        else:
            url = stream["url"]
            item_id = f'{details["preset_id"]}--{stream["media_type"]}'
            content_type = ContentType.try_parse(stream["media_type"])
            bit_rate = stream.get("bitrate", 128)  # TODO !

        radio = Radio(item_id=item_id, provider=self.domain, name=name)
        radio.add_provider_mapping(
            ProviderMapping(
                item_id=item_id,
                provider_domain=self.domain,
                provider_instance=self.instance_id,
                content_type=content_type,
                bit_rate=bit_rate,
                details=url,
            )
        )
        # preset number is used for sorting (not present at stream time)
        preset_number = details.get("preset_number")
        if preset_number and folder:
            radio.sort_name = f'{folder}-{details["preset_number"]}'
        elif preset_number:
            radio.sort_name = details["preset_number"]
        radio.sort_name += create_sort_name(name)
        if "text" in details:
            radio.metadata.description = details["text"]
        # images
        if img := details.get("image"):
            radio.metadata.images = [MediaItemImage(ImageType.THUMB, img)]
        if img := details.get("logo"):
            radio.metadata.images = [MediaItemImage(ImageType.LOGO, img)]
        return radio

    async def get_stream_details(self, item_id: str) -> StreamDetails:
        """Get streamdetails for a radio station."""
        if item_id.startswith("http"):
            # custom url
            return StreamDetails(
                provider=self.domain,
                item_id=item_id,
                content_type=ContentType.UNKNOWN,
                media_type=MediaType.RADIO,
                data=item_id,
            )
        item_id, media_type = item_id.split("--", 1)
        stream_info = await self.__get_data("Tune.ashx", id=item_id)
        for stream in stream_info["body"]:
            if stream["media_type"] != media_type:
                continue
            # check if the radio stream is not a playlist
            url = stream["url"]
            if url.endswith("m3u8") or url.endswith("m3u") or url.endswith("pls"):
                playlist = await fetch_playlist(self.mass, url)
                url = playlist[0]
            return StreamDetails(
                provider=self.domain,
                item_id=item_id,
                content_type=ContentType(stream["media_type"]),
                media_type=MediaType.RADIO,
                data=url,
                expires=time() + 24 * 3600,
            )
        raise MediaNotFoundError(f"Unable to retrieve stream details for {item_id}")

    async def get_audio_stream(
        self, streamdetails: StreamDetails, seek_position: int = 0  # noqa: ARG002
    ) -> AsyncGenerator[bytes, None]:
        """Return the audio stream for the provider item."""
        async for chunk in get_radio_stream(self.mass, streamdetails.data, streamdetails):
            yield chunk

    async def __get_data(self, endpoint: str, **kwargs):
        """Get data from api."""
        if endpoint.startswith("http"):
            url = endpoint
        else:
            url = f"https://opml.radiotime.com/{endpoint}"
            kwargs["formats"] = "ogg,aac,wma,mp3"
            kwargs["username"] = self.config.get_value(CONF_USERNAME)
            kwargs["partnerId"] = "1"
            kwargs["render"] = "json"
        async with self._throttler:
            async with self.mass.http_session.get(url, params=kwargs, verify_ssl=False) as response:
                result = await response.json()
                if not result or "error" in result:
                    self.logger.error(url)
                    self.logger.error(kwargs)
                    result = None
                return result
