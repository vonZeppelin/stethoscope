import asyncio
import janus

from aiohttp import ClientSession
from aiohttp.hdrs import CONTENT_LENGTH, CONTENT_TYPE
from datetime import timedelta
from google.cloud.exceptions import NotFound
from google.cloud.storage import Client, Bucket
from google.oauth2.service_account import Credentials
from pytube import Stream as YoutubeStream, YouTube

from typing import AsyncIterable, Optional, Tuple


BUCKET_NAME = "stethoscope-2022"
ONE_DAY = timedelta(days=1)


class _FakeBuffer:
    def __init__(self, sync_q: janus.SyncQueue[Optional[bytes]]):
        self._sync_q = sync_q

    def stream_to_buffer(self, stream: YoutubeStream):
        stream.stream_to_buffer(self)
        self._sync_q.put(None)

    def write(self, data: bytes):
        self._sync_q.put(data)


class ObjectStore:
    def __init__(self, credentials: Credentials):
        self._object_store = Client(credentials=credentials)

    async def save_audio(self, yt: YouTube) -> Tuple[int, str]:
        audio_stream, object_write_url = await asyncio.gather(
            asyncio.to_thread(lambda: yt.streams.get_audio_only()),
            asyncio.to_thread(self._get_presign_url, yt.video_id, "PUT")
        )

        async with ClientSession() as http:
            await http.put(
                object_write_url,
                data=self._chunked_stream(audio_stream),
                headers={
                    CONTENT_LENGTH: str(audio_stream.filesize),
                    CONTENT_TYPE: audio_stream.mime_type
                }
            )

        return audio_stream.filesize, audio_stream.mime_type

    async def delete_audio(self, video_id: str):
        await asyncio.to_thread(self._delete_blob, video_id)

    async def get_audio_url(self, audio_id: str) -> str:
        object_read_url = await asyncio.to_thread(
            self._get_presign_url, audio_id, "GET"
        )

        return object_read_url

    @staticmethod
    async def _chunked_stream(stream: YoutubeStream) -> AsyncIterable[bytes]:
        queue = janus.Queue[Optional[bytes]](maxsize=5)
        buffer = _FakeBuffer(queue.sync_q)

        # asyncio.to_thread is not working here for some reason
        stream_to_buffer_task = asyncio.get_running_loop().run_in_executor(
            None, buffer.stream_to_buffer, stream
        )

        while chunk := await queue.async_q.get():
            yield chunk

        await stream_to_buffer_task
        queue.close()
        await queue.wait_closed()

    def _get_presign_url(self, name: str, method: str) -> str:
        bucket: Bucket = self._object_store.bucket(BUCKET_NAME)
        blob = bucket.blob(name)

        return blob.generate_signed_url(
            method=method, version="v4", expiration=ONE_DAY
        )

    def _delete_blob(self, name: str):
        bucket: Bucket = self._object_store.bucket(BUCKET_NAME)
        blob = bucket.blob(name)
        try:
            blob.delete()
        except NotFound:
            pass
