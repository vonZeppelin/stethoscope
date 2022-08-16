import asyncio
import janus
import oci

from aiohttp import ClientSession
from aiohttp.hdrs import CONTENT_LENGTH, CONTENT_TYPE
from datetime import datetime, timedelta
from oci.object_storage.models import CreatePreauthenticatedRequestDetails
from pytube import YouTube, Stream as YoutubeStream
from typing import Optional


BUCKET_NAME = "stethoscope"

object_store = oci.object_storage.ObjectStorageClient(
    oci.config.from_file("oci.conf")
)
bucket_namespace: str = object_store.get_namespace().data


class _FakeBuffer:
    def __init__(self, sync_q: janus.SyncQueue[Optional[bytes]]):
        self.sync_q = sync_q

    def stream_to_buffer(self, stream: YoutubeStream):
        stream.stream_to_buffer(self)
        self.sync_q.put(None)

    def write(self, data: bytes):
        self.sync_q.put(data)


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


async def save_audio_to_bucket(youtube: YouTube):
    loop = asyncio.get_running_loop()

    object_write_request = await loop.run_in_executor(
        None,
        object_store.create_preauthenticated_request,
        bucket_namespace,
        BUCKET_NAME,
        CreatePreauthenticatedRequestDetails(
            name=youtube.video_id,
            object_name=youtube.video_id,
            access_type=CreatePreauthenticatedRequestDetails.ACCESS_TYPE_OBJECT_WRITE,
            time_expires=datetime.utcnow() + timedelta(minutes=15)
        )
    )
    object_write_url = object_store.base_client.endpoint + object_write_request.data.access_uri
    audio_stream = await loop.run_in_executor(
        None, lambda: youtube.streams.get_audio_only()
    )

    async with ClientSession() as http:
        await http.put(
            object_write_url,
            data=_chunked_stream(audio_stream),
            headers={
                CONTENT_LENGTH: str(audio_stream.filesize),
                CONTENT_TYPE: audio_stream.mime_type
            }
        )
