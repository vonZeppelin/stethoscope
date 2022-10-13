import asyncio

from aiohttp import web
from fireo.utils import utils
from http import HTTPStatus
from pytube import YouTube
from typing import Dict, List

from firestore import Video
from objectstore import ObjectStore


class FilesView:
    def __init__(self, object_store: ObjectStore):
        self.object_store = object_store

    async def list_files(self, request: web.Request) -> web.Response:
        # TODO handle next
        def list_videos() -> List[Dict]:
            video_ids = request.query.getall("id", [])
            if video_ids:
                videos = Video.collection.get_all(
                    map(
                        lambda v_id: utils.generateKeyFromId(Video, v_id),
                        video_ids
                    )
                )
            else:
                videos = Video.collection.order("-published").fetch(5)

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

        loop = asyncio.get_running_loop()
        files = await loop.run_in_executor(None, list_videos)
        return web.json_response({"files": files, "next": None})

    async def add_file(self, request: web.Request) -> web.Response:
        loop = asyncio.get_running_loop()

        async def save_audio(yt: YouTube):
            filesize, mime_type = await self.object_store.save_audio(yt)

            video = Video(
                id=yt.video_id,
                title=yt.title,
                description=yt.description,
                published=yt.publish_date,
                duration=yt.length,
                thumbnail_url=yt.thumbnail_url,
                audio_size=filesize,
                audio_type=mime_type
            )
            await loop.run_in_executor(None, video.save)

        youtube = YouTube(
            (await request.json())["url"]
        )
        loop.create_task(save_audio(youtube))
        return web.json_response(
            {"id": youtube.video_id},
            status=HTTPStatus.ACCEPTED
        )

    async def delete_file(self, request: web.Request) -> web.Response:
        loop = asyncio.get_running_loop()

        file_id = request.match_info["file_id"]
        await asyncio.gather(
            self.object_store.delete_audio(file_id),
            loop.run_in_executor(
                None,
                Video.collection.delete,
                utils.generateKeyFromId(Video, file_id)
            )
        )
        return web.json_response({"id": file_id})
