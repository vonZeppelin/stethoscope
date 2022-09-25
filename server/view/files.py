import asyncio

from aiohttp import web
from http import HTTPStatus
from pytube import YouTube, Stream as YoutubeStream
from typing import Dict, List

from firestore import Video
from objectstore import ObjectStore


class FilesView:
    def __init__(self, object_store: ObjectStore):
        self.object_store = object_store

    async def list_files(self, request: web.Request) -> web.Response:
        def list_videos(next: str) -> List[Dict]:
            query = Video.collection.order("-published").fetch(5)
            return [
                {
                    "id": v.id,
                    "title": v.title,
                    "description": v.description,
                    "thumbnail": v.thumbnail_url,
                    "duration": v.duration
                }
                for v in query
            ]

        loop = asyncio.get_running_loop()
        videos = await loop.run_in_executor(
            None, list_videos, request.query.get("next")
        )
        return web.json_response({"files": videos, "next": None})

    async def add_file(self, request: web.Request) -> web.Response:
        def save_audio_to_db(yt: YouTube) -> YoutubeStream:
            audio = yt.streams.get_audio_only()

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
            video.save()

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
