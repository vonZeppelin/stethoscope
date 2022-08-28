import asyncio

from aiohttp import web
from datetime import timedelta, timezone
from podgen import Podcast, Media
from sqlalchemy.orm import sessionmaker
from yarl import URL

from db import Video
from object_store import ObjectStore


class FeedView:
    def __init__(self, db_session: sessionmaker, object_store: ObjectStore):
        self.db_session = db_session
        self.object_store = object_store

    async def get_feed(self, request: web.Request):
        def generate_rss_feed() -> str:
            website_url = URL.build(
                scheme=request.url.scheme, host=request.url.host
            )
            podcast = Podcast(
                name="Leonid's Stethoscope",
                description="Podcast from Youtube videos",
                website=str(website_url),
                explicit=False
            )

            with self.db_session() as db:
                query = db.query(Video).order_by(Video.published.desc())
                for v in query:
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

            return podcast.rss_str(minimize=True)

        loop = asyncio.get_running_loop()
        feed = await loop.run_in_executor(None, generate_rss_feed)
        return web.Response(text=feed, content_type="application/rss+xml")

    async def get_media_link(self, request: web.Request):
        episode_id = request.match_info["episode_id"]
        audio_url = await self.object_store.get_audio_url(episode_id)

        raise web.HTTPPermanentRedirect(audio_url)
