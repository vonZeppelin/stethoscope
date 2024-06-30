from datetime import datetime, timedelta, timezone
from typing import AsyncIterable, Callable
from urllib.parse import quote

from aiohttp import web
from feedgen.feed import FeedGenerator
from sqlalchemy import null, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from db import Catalog
from objectstore import ObjectStore


class FeedView:
    def __init__(
        self,
        website: str,
        db_session: async_sessionmaker,
        object_store: ObjectStore
    ):
        self._website = website
        self._db_session = db_session
        self._object_store = object_store

    async def get_youtube_feed(self, request: web.Request) -> web.Response:
        def media_link(episode):
            return str(
                request.url
                .with_scheme("https")
                .with_path(f"/media/{episode.id}")
            )

        def pub_date(_, episode):
            return episode.published.replace(
                tzinfo=timezone.utc
            )

        podcast = FeedGenerator()
        podcast.load_extension("podcast")
        podcast.link(href=self._website, rel="self")
        podcast.title("Leonid's Stethoscope")
        podcast.description("Turns Youtube videos into podcast")
        podcast.logo(f"{self._website}/logo.jpg")

        async with self._db_session() as db:
            items = await db.stream_scalars(
                select(Catalog)
                .where(Catalog.parent_id == null())
                .where(~Catalog.children.any())
                .order_by(Catalog.created)
            )
            await self._add_episodes(
                podcast, items, pub_date, media_link
            )

        return web.Response(
            body=podcast.rss_str(),
            content_type="application/rss+xml"
        )

    async def get_audiobook_feed(self, request: web.Request) -> web.Response:
        def media_link(episode):
            media_id = quote(
                f"{episode.parent_id}/{episode.id}", safe=""
            )
            return str(
                request.url
                .with_scheme("https")
                .with_path(f"/media/{media_id}", encoded=True)
            )

        def pub_date(idx, episode):
            published = episode.published.replace(
                tzinfo=timezone.utc
            )
            return published + timedelta(hours=idx)

        book_id = request.match_info["book_id"]
        async with self._db_session() as db:
            book = await db.get(Catalog, book_id)
            podcast = FeedGenerator()
            podcast.load_extension("podcast")
            podcast.link(href=self._website, rel="self")
            podcast.title(book.title)
            podcast.description(book.description)
            items = await db.stream_scalars(
                select(Catalog)
                .where(Catalog.parent_id == book_id)
                .order_by(Catalog.filename)
            )
            await self._add_episodes(
                podcast, items, pub_date, media_link
            )

        return web.Response(
            body=podcast.rss_str(),
            content_type="application/rss+xml"
        )

    async def get_media_url(self, request: web.Request):
        episode_id = request.match_info["episode_id"]
        media_link = await self._object_store.get_object_url(episode_id)

        raise web.HTTPPermanentRedirect(media_link)

    @staticmethod
    async def _add_episodes(
            podcast: FeedGenerator,
            items: AsyncIterable[Catalog],
            pub_date_maker: Callable[[int, Catalog], datetime],
            media_link_maker: Callable[[Catalog], str]
    ):
        idx = 0
        async for i in items:
            episode = podcast.add_entry()
            episode.id(i.id)
            episode.title(i.title)
            episode.description(i.description)
            episode.published(pub_date_maker(idx, i))
            episode.enclosure(
                url=media_link_maker(i),
                length=i.audio_size,
                type=i.audio_type
            )
            episode.podcast.itunes_duration(i.duration)
            # TODO episode.podcast.itunes_image(i.thumbnail_url)

            idx += 1
