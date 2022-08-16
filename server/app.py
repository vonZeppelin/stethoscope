import argparse
import asyncio
import pathlib

from aiohttp import web
from http import HTTPStatus
from pytube import YouTube

from db import Video, create_session
from object_store import save_audio_to_bucket


SESSION_KEY = "ORM_SESSION"


class FilesView(web.View):
    async def get(self) -> web.Response:
        def list_videos(next: str) -> list[dict]:
            db_session = self.request.app[SESSION_KEY]
            with db_session() as db:
                query = db.query(Video).order_by(Video.published.desc()).limit(5)
                return [
                    {
                        "id": v.id,
                        "title": v.title,
                        "description": v.description,
                        "thumbnail": v.thumbnail_url,
                        "duration": v.duration
                    }
                    for v in query.all()
                ]

        loop = asyncio.get_running_loop()
        videos = await loop.run_in_executor(
            None, list_videos, self.request.query.get("next")
        )
        return web.json_response({"files": videos, "next": None})

    async def post(self) -> web.Response:
        def save_audio_to_db(yt: YouTube):
            db_session = self.request.app[SESSION_KEY]
            with db_session() as db:
                video = Video(
                    id=yt.video_id,
                    title=yt.title,
                    description=yt.description,
                    published=yt.publish_date,
                    duration=yt.length,
                    thumbnail_url=yt.thumbnail_url
                )
                db.add(video)
                db.commit()

        loop = asyncio.get_running_loop()
        youtube = YouTube(
            (await self.request.json())["url"]
        )

        await loop.run_in_executor(None, save_audio_to_db, youtube)
        loop.create_task(save_audio_to_bucket(youtube))

        return web.json_response(
            {"id": youtube.video_id},
            status=HTTPStatus.ACCEPTED
        )

    async def delete(self):
        pass


parser = argparse.ArgumentParser()
parser.add_argument("--db-dsn", required=True)
parser.add_argument("--db-password", required=True)
parser.add_argument("--db-user", required=True)
parser.add_argument("--ui-dir", type=pathlib.Path, required=True)
args = parser.parse_args()

app = web.Application()
app.router.add_view("/files", FilesView)
app.router.add_static("/", args.ui_dir)
app[SESSION_KEY] = create_session(
    args.db_user, args.db_password, args.db_dsn
)

web.run_app(app)
