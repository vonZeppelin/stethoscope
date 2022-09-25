import asyncio
import janus

from aiohttp import ClientSession
from aiohttp.hdrs import CONTENT_LENGTH, CONTENT_TYPE
from datetime import timedelta
from google.cloud.storage import Client, Bucket
from google.oauth2.service_account import Credentials
from pytube import Stream as YoutubeStream
from typing import Optional


BUCKET_NAME = "stethoscope-2022"
FIFTEEN_MIN = timedelta(minutes=15)


class _FakeBuffer:
    def __init__(self, sync_q: janus.SyncQueue[Optional[bytes]]):
        self.sync_q = sync_q

    def stream_to_buffer(self, stream: YoutubeStream):
        stream.stream_to_buffer(self)
        self.sync_q.put(None)

    def write(self, data: bytes):
        self.sync_q.put(data)


class ObjectStore:
    def __init__(self, credentials: Credentials):
        self._object_store = Client(credentials=credentials)

    async def save_audio(self, video_id: str, audio_stream: YoutubeStream):
        loop = asyncio.get_running_loop()

        object_write_url = await loop.run_in_executor(
            None, self._get_presign_url, video_id, "PUT"
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

    async def delete_audio(self, video_id: str):
        loop = asyncio.get_running_loop()

        await loop.run_in_executor(None, self._delete_blob, video_id)

    async def get_audio_url(self, audio_id: str) -> str:
        loop = asyncio.get_running_loop()

        object_read_url = await loop.run_in_executor(
            None, self._get_presign_url, audio_id, "GET"
        )

        return object_read_url

    @staticmethod
    async def _chunked_stream(stream: YoutubeStream):
        queue = janus.Queue[Optional[bytes]](maxsize=5)
        buffer = _FakeBuffer(queue.sync_q)
        loop = asyncio.get_running_loop()

        loop.run_in_executor(None, buffer.stream_to_buffer, stream)

        while True:
            chunk = await queue.async_q.get()
            if chunk is None:
                break
            else:
                yield chunk

        queue.close()
        await queue.wait_closed()

    def _get_presign_url(self, name: str, method: str) -> str:
        bucket: Bucket = self._object_store.bucket(BUCKET_NAME)
        blob = bucket.blob(name)

        return blob.generate_signed_url(
            method=method, version="v4", expiration=FIFTEEN_MIN
        )

    def _delete_blob(self, name: str):
        bucket: Bucket = self._object_store.bucket(BUCKET_NAME)
        blob = bucket.blob(name)
        blob.delete()
