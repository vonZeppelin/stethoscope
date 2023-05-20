import asyncio
from datetime import datetime
from http import HTTPStatus

from aiohttp import web
from pytube import YouTube
from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from db import Video
from objectstore import ObjectStore


class FilesView:
    def __init__(
        self,
        db_session: async_sessionmaker,
        object_store: ObjectStore
    ):
        self._db_session = db_session
        self._object_store = object_store

    async def list_files(self, request: web.Request) -> web.Response:
        # TODO handle next
        video_ids = request.query.getall("id", [])
        async with self._db_session() as db:
            if video_ids:
                videos = select(Video).where(Video.id.in_(video_ids))
            else:
                videos = select(Video).order_by(desc(Video.created))
            videos = await db.stream_scalars(videos)
            files = [
                {
                    "id": v.id,
                    "title": v.title,
                    "description": v.description,
                    "thumbnail": v.thumbnail_url,
                    "duration": v.duration
                }
                async for v in videos
            ]

        return web.json_response({"files": files, "next": None})

    async def add_file(self, request: web.Request) -> web.Response:
        async def save_audio(yt: YouTube) -> None:
            filesize, mime_type = await self._object_store.save_audio(yt)

            video = Video(
                id=yt.video_id,
                title=yt.title,
                description=yt.description or "",
                created=datetime.now(),
                published=yt.publish_date,
                duration=yt.length,
                thumbnail_url=yt.thumbnail_url,
                audio_size=filesize,
                audio_type=mime_type
            )
            async with self._db_session.begin() as db:
                db.add(video)

        youtube = YouTube(
            (await request.json())["url"]
        )
        async with self._db_session() as db:
            existing_video = await db.get(Video, youtube.video_id)
        if existing_video:
            return_status = HTTPStatus.CONFLICT
        else:
            asyncio.create_task(save_audio(youtube))
            return_status = HTTPStatus.ACCEPTED
        return web.json_response(
            {"id": youtube.video_id},
            status=return_status
        )

    async def delete_file(self, request: web.Request) -> web.Response:
        file_id = request.match_info["file_id"]
        async with self._db_session.begin() as db:
            await asyncio.gather(
                self._object_store.delete_audio(file_id),
                db.execute(
                    delete(Video).where(Video.id == file_id)
                )
            )
        return web.json_response({"id": file_id})
