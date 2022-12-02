import asyncio

from aiohttp import web
from datetime import timedelta, timezone
from podgen import Podcast, Media
from typing import Iterator

from firestore import Video
from objectstore import ObjectStore


class FeedView:
    def __init__(self, website: str, object_store: ObjectStore):
        self.website = website
        self.object_store = object_store

    async def get_feed(self, request: web.Request) -> web.Response:
        def generate_rss_feed() -> str:
            podcast = Podcast(
                name="Leonid's Stethoscope",
                description="Podcast from Youtube videos",
                website=self.website,
                explicit=False
            )

            query: Iterator[Video] = Video.collection.order("-created").fetch()
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
        episode_id: str = request.match_info["episode_id"]
        audio_url = await self.object_store.get_audio_url(episode_id)

        raise web.HTTPPermanentRedirect(audio_url)
