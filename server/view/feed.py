from datetime import timedelta, timezone
import warnings

from aiohttp import web
from podgen import Media, NotSupportedByItunesWarning, Podcast
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from db import Video
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

    async def get_feed(self, request: web.Request) -> web.Response:
        with warnings.catch_warnings(
            action="ignore",
            category=NotSupportedByItunesWarning
        ):
            podcast = Podcast(
                name="Leonid's Stethoscope",
                description="Podcast from Youtube videos",
                website=self._website,
                explicit=False
            )
            async with self._db_session() as db:
                videos = await db.stream_scalars(
                    select(Video).order_by(Video.created)
                )
                async for v in videos:
                    episode = podcast.add_episode()
                    episode.id = v.id
                    episode.title = v.title
                    episode.long_summary = v.description
                    episode.publication_date = v.published.replace(
                        tzinfo=timezone.utc
                    )
                    episode.image = v.thumbnail_url
                    episode.media = Media(
                        url=str(request.url / v.id),
                        size=v.audio_size,
                        type=v.audio_type,
                        duration=timedelta(seconds=v.duration)
                    )

        return web.Response(
            text=podcast.rss_str(minimize=True),
            content_type="application/rss+xml"
        )

    async def get_media_link(self, request: web.Request):
        episode_id: str = request.match_info["episode_id"]
        audio_url = await self._object_store.get_audio_url(episode_id)

        raise web.HTTPPermanentRedirect(audio_url)
