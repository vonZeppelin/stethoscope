import asyncio
from datetime import datetime, timedelta
from typing import AsyncIterable, Dict, Optional, Tuple

from aiohttp import ClientSession
from aiohttp.hdrs import CONTENT_LENGTH, CONTENT_TYPE
import janus
import oci
from oci.object_storage.models import CreatePreauthenticatedRequestDetails
from pytube import Stream as YoutubeStream, YouTube


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
    def __init__(self, oci_config: Dict[str, str]):
        self.object_store = oci.object_storage.ObjectStorageClient(oci_config)
        self.bucket_namespace: str = self.object_store.get_namespace().data

    async def save_audio(self, yt: YouTube) -> Tuple[int, str]:
        audio_stream, object_write_request = await asyncio.gather(
            asyncio.to_thread(lambda: yt.streams.get_audio_only()),
            asyncio.to_thread(
                self.object_store.create_preauthenticated_request,
                self.bucket_namespace,
                BUCKET_NAME,
                CreatePreauthenticatedRequestDetails(
                    name=yt.video_id,
                    object_name=yt.video_id,
                    access_type=CreatePreauthenticatedRequestDetails.ACCESS_TYPE_OBJECT_WRITE,
                    time_expires=datetime.utcnow() + ONE_DAY
                )
            )
        )

        async with ClientSession() as http:
            await http.put(
                self.object_store.base_client.endpoint + object_write_request.data.access_uri,
                data=self._chunked_stream(audio_stream),
                headers={
                    CONTENT_LENGTH: str(audio_stream.filesize),
                    CONTENT_TYPE: audio_stream.mime_type
                }
            )

        return audio_stream.filesize, audio_stream.mime_type

    async def delete_audio(self, video_id: str):
        try:
            await asyncio.to_thread(
                self.object_store.delete_object,
                self.bucket_namespace,
                BUCKET_NAME,
                video_id
            )
        except oci.exceptions.ServiceError as e:
            if e.status != 404:
                raise

    async def get_audio_url(self, audio_id: str) -> str:
        object_read_request = await asyncio.to_thread(
            self.object_store.create_preauthenticated_request,
            self.bucket_namespace,
            BUCKET_NAME,
            CreatePreauthenticatedRequestDetails(
                name=audio_id,
                object_name=audio_id,
                access_type=CreatePreauthenticatedRequestDetails.ACCESS_TYPE_OBJECT_READ,
                time_expires=datetime.utcnow() + ONE_DAY,
            )
        )

        return self.object_store.base_client.endpoint + object_read_request.data.access_uri

    @staticmethod
    async def _chunked_stream(stream: YoutubeStream) -> AsyncIterable[bytes]:
        queue = janus.Queue[Optional[bytes]](maxsize=5)
        buffer = _FakeBuffer(queue.sync_q)

        stream_to_buffer_task = asyncio.create_task(
            asyncio.to_thread(buffer.stream_to_buffer, stream)
        )

        while chunk := await queue.async_q.get():
            yield chunk

        await stream_to_buffer_task
        queue.close()
        await queue.wait_closed()
