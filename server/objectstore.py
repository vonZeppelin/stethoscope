import aiofiles
import aiofiles.ospath
import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, UTC
import os
import tempfile
from typing import AsyncIterable, Dict

from aiohttp import ClientSession
from aiohttp.hdrs import CONTENT_LENGTH, CONTENT_TYPE
import oci
from oci.object_storage.models import CreatePreauthenticatedRequestDetails


BUCKET_NAME = "stethoscope-2022"
ONE_DAY = timedelta(days=1)
ONE_HOUR = timedelta(hours=1)


@dataclass
class YoutubeAudio:
    id: str
    title: str
    description: str
    duration: int
    size: int
    published: datetime
    thumbnail_url: str
    mime_type: str


class ObjectStore:
    def __init__(self, oci_config: Dict[str, str]):
        self.object_store = oci.object_storage.ObjectStorageClient(oci_config)
        self.bucket_namespace: str = self.object_store.get_namespace().data

    async def save_youtube_audio(self, youtube_url: str) -> YoutubeAudio:
        yt_dlp = [
            "yt-dlp", "--netrc", "--netrc-location", "/etc/stethoscope/"
        ]
        with tempfile.TemporaryDirectory() as tmp_dir:
            audiofile = os.path.join(tmp_dir, "audiotrack")

            youtube_info_proc, youtube_audio_proc = await asyncio.gather(
                asyncio.create_subprocess_exec(
                    *yt_dlp,
                    "--dump-json",
                    youtube_url,
                    stdout=asyncio.subprocess.PIPE
                ),
                asyncio.create_subprocess_exec(
                    *yt_dlp,
                    "--format",
                    "ba[ext=m4a]",
                    "--output",
                    audiofile,
                    youtube_url,
                    stdout=asyncio.subprocess.DEVNULL
                )
            )
            (youtube_info_json, _), _ = await asyncio.gather(
                youtube_info_proc.communicate(), youtube_audio_proc.wait()
            )
            youtube_info = json.loads(youtube_info_json)
            youtube_audio = YoutubeAudio(
                id=youtube_info["id"],
                title=youtube_info["title"],
                description=youtube_info["description"],
                duration=youtube_info["duration"],
                size=await aiofiles.ospath.getsize(audiofile),
                published=datetime.fromtimestamp(youtube_info["epoch"], UTC),
                thumbnail_url=youtube_info["thumbnail"],
                mime_type="audio/mp4"
            )

            object_write_request = await asyncio.to_thread(
                self.object_store.create_preauthenticated_request,
                self.bucket_namespace,
                BUCKET_NAME,
                CreatePreauthenticatedRequestDetails(
                    name=youtube_audio.id,
                    object_name=youtube_audio.id,
                    access_type=CreatePreauthenticatedRequestDetails.ACCESS_TYPE_OBJECT_WRITE,
                    time_expires=datetime.utcnow() + ONE_HOUR
                )
            )
            async with ClientSession() as http:
                await http.put(
                    object_write_request.data.full_path,
                    # TODO stream from yt-dlp stdout
                    data=self._file_sender(audiofile),
                    headers={
                        CONTENT_LENGTH: str(youtube_audio.size),
                        CONTENT_TYPE: youtube_audio.mime_type
                    }
                )

        return youtube_audio

    async def save_book_chapter(self, book_id: str, chapter_id: str) -> str:
        object_write_request = await asyncio.to_thread(
            self.object_store.create_preauthenticated_request,
            self.bucket_namespace,
            BUCKET_NAME,
            CreatePreauthenticatedRequestDetails(
                name=chapter_id,
                object_name=f"{book_id}/{chapter_id}",
                access_type=CreatePreauthenticatedRequestDetails.ACCESS_TYPE_OBJECT_WRITE,
                time_expires=datetime.utcnow() + ONE_HOUR
            )
        )
        return object_write_request.data.full_path

    async def delete_object(self, object_id: str):
        try:
            await asyncio.to_thread(
                self.object_store.delete_object,
                self.bucket_namespace,
                BUCKET_NAME,
                object_id
            )
        except oci.exceptions.ServiceError as e:
            if e.status != 404:
                raise

    async def get_object_url(self, object_id: str) -> str:
        object_read_request = await asyncio.to_thread(
            self.object_store.create_preauthenticated_request,
            self.bucket_namespace,
            BUCKET_NAME,
            CreatePreauthenticatedRequestDetails(
                name=object_id,
                object_name=object_id,
                access_type=CreatePreauthenticatedRequestDetails.ACCESS_TYPE_OBJECT_READ,
                time_expires=datetime.utcnow() + ONE_DAY
            )
        )

        return object_read_request.data.full_path

    @staticmethod
    async def _file_sender(file) -> AsyncIterable[bytes]:
        async with aiofiles.open(file, "rb") as f:
            while chunk := await f.read(1024 * 1024):
                yield chunk
