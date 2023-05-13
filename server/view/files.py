import asyncio

from aiohttp import web
from datetime import datetime
from fireo.utils import utils
from http import HTTPStatus
from pytube import YouTube

from firestore import Video
from objectstore import ObjectStore

from typing import Dict, List


class FilesView:
    def __init__(self, object_store: ObjectStore):
        self._object_store = object_store

    async def list_files(self, request: web.Request) -> web.Response:
        # TODO handle next
        def list_videos() -> List[Dict]:
            video_ids = request.query.getall("id", [])
            if video_ids:
                videos = Video.collection.get_all(
                    [
                        utils.get_key(Video.collection_name, v)
                        for v in video_ids
                    ]
                )
            else:
                videos = Video.collection.order("-created").fetch(5)

            return [
                {
                    "id": v.id,
                    "title": v.title,
                    "description": v.description,
                    "thumbnail": v.thumbnail_url,
                    "duration": v.duration
                }
                for v in videos if v
            ]

        files = await asyncio.to_thread(list_videos)
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
            await asyncio.to_thread(video.save)

        youtube = YouTube(
            (await request.json())["url"]
        )
        asyncio.create_task(save_audio(youtube))
        return web.json_response(
            {"id": youtube.video_id},
            status=HTTPStatus.ACCEPTED
        )

    async def delete_file(self, request: web.Request) -> web.Response:
        file_id = request.match_info["file_id"]
        await asyncio.gather(
            self._object_store.delete_audio(file_id),
            asyncio.to_thread(
                Video.collection.delete,
                utils.get_key(Video.collection_name, file_id)
            )
        )
        return web.json_response({"id": file_id})
