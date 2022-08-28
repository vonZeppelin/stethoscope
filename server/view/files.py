import asyncio

from aiohttp import web
from http import HTTPStatus
from pytube import YouTube, Stream as YoutubeStream
from sqlalchemy.orm import sessionmaker
from typing import Dict, List

from db import Video
from object_store import ObjectStore


class FilesView:
    def __init__(self, db_session: sessionmaker, object_store: ObjectStore):
        self.db_session = db_session
        self.object_store = object_store

    async def list_files(self, request: web.Request) -> web.Response:
        def list_videos(next: str) -> List[Dict]:
            with self.db_session() as db:
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
            None, list_videos, request.query.get("next")
        )
        return web.json_response({"files": videos, "next": None})

    async def add_file(self, request: web.Request) -> web.Response:
        def save_audio_to_db(yt: YouTube) -> YoutubeStream:
            audio = yt.streams.get_audio_only()

            with self.db_session() as db:
                video = Video(
                    id=yt.video_id,
                    title=yt.title,
                    description=yt.description,
                    published=yt.publish_date,
                    duration=yt.length,
                    thumbnail_url=yt.thumbnail_url,
                    audio_size=audio.filesize,
                    audio_type=audio.mime_type
                )
                db.add(video)
                db.commit()

            return audio

        loop = asyncio.get_running_loop()
        youtube = YouTube(
            (await request.json())["url"]
        )

        audio_stream = await loop.run_in_executor(
            None, save_audio_to_db, youtube
        )
        loop.create_task(
            self.object_store.save_audio(youtube.video_id, audio_stream)
        )

        return web.json_response(
            {"id": youtube.video_id},
            status=HTTPStatus.ACCEPTED
        )

    async def delete_file(self, request: web.Request) -> web.Response:
        file_id = request.match_info["file_id"]
