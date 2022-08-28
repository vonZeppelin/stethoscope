import asyncio
import janus
import oci

from aiohttp import ClientSession
from aiohttp.hdrs import CONTENT_LENGTH, CONTENT_TYPE
from datetime import datetime, timedelta
from oci.object_storage.models import CreatePreauthenticatedRequestDetails
from pytube import Stream as YoutubeStream
from typing import Dict, Optional


BUCKET_NAME = "stethoscope"
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
    def __init__(self, oci_config: Dict[str, str]):
        self.object_store = oci.object_storage.ObjectStorageClient(oci_config)
        self.bucket_namespace: str = self.object_store.get_namespace().data

    async def save_audio(self, video_id: str, audio_stream: YoutubeStream):
        loop = asyncio.get_running_loop()

        object_write_request = await loop.run_in_executor(
            None,
            self.object_store.create_preauthenticated_request,
            self.bucket_namespace,
            BUCKET_NAME,
            CreatePreauthenticatedRequestDetails(
                name=video_id,
                object_name=video_id,
                access_type=CreatePreauthenticatedRequestDetails.ACCESS_TYPE_OBJECT_WRITE,
                time_expires=datetime.utcnow() + FIFTEEN_MIN
            )
        )
        object_write_url = self.object_store.base_client.endpoint + object_write_request.data.access_uri

        async with ClientSession() as http:
            await http.put(
                object_write_url,
                data=self._chunked_stream(audio_stream),
                headers={
                    CONTENT_LENGTH: str(audio_stream.filesize),
                    CONTENT_TYPE: audio_stream.mime_type
                }
            )

    async def get_audio_url(self, audio_id: str) -> str:
        loop = asyncio.get_running_loop()

        object_read_request = await loop.run_in_executor(
            None,
            self.object_store.create_preauthenticated_request,
            self.bucket_namespace,
            BUCKET_NAME,
            CreatePreauthenticatedRequestDetails(
                name=audio_id,
                object_name=audio_id,
                access_type=CreatePreauthenticatedRequestDetails.ACCESS_TYPE_OBJECT_READ,
                time_expires=datetime.utcnow() + FIFTEEN_MIN
            )
        )

        return self.object_store.base_client.endpoint + object_read_request.data.access_uri

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
