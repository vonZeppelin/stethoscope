import asyncio
from http import HTTPStatus

from aiohttp import web
import nanoid
from pytube import YouTube
from pytube.exceptions import RegexMatchError
from sqlalchemy import desc, func, null, select
from sqlalchemy.orm import aliased, joinedload
from sqlalchemy.ext.asyncio import async_sessionmaker

from db import Catalog
from objectstore import ObjectStore
from remotefile import get_file_info


class FilesView:
    def __init__(
            self,
            db_session: async_sessionmaker,
            object_store: ObjectStore
    ):
        self._db_session = db_session
        self._object_store = object_store

    async def list_files(self, request: web.Request) -> web.Response:
        async with self._db_session() as db:
            catalog_parent = aliased(Catalog, name="catalog_parent")
            catalog_items = (
                select(catalog_parent, func.count(Catalog.id) == 0)
                .outerjoin(Catalog, catalog_parent.id == Catalog.parent_id)
                # exclude book chapters
                .where(catalog_parent.parent_id == null())
                # exclude not fully downloaded/uploaded files
                .where(catalog_parent.title != null())
                .group_by(catalog_parent.id)
                .order_by(desc(catalog_parent.created))
            )
            if ids := request.query.getall("id", []):
                catalog_items = catalog_items.having(catalog_parent.id.in_(ids))
            files = [
                {
                    "id": item.id,
                    "title": item.title,
                    "description": item.description,
                    "thumbnail": item.thumbnail_url,
                    "duration": item.duration,
                    "type": "youtube" if is_youtube else "audiobook"
                }
                async for item, is_youtube in await db.stream(catalog_items)
            ]

        return web.json_response({"files": files})

    async def delete_file(self, request: web.Request) -> web.Response:
        parent_id = request.match_info["file_id"]
        async with self._db_session.begin() as db:
            parent = await db.get(
                Catalog,
                parent_id,
                options=[joinedload(Catalog.children)]
            )

            async with asyncio.TaskGroup() as tg:
                if parent.children:
                    for child in parent.children:
                        tg.create_task(
                            self._object_store.delete_object(
                                f"{parent_id}/{child.id}"
                            )
                        )
                else:
                    tg.create_task(
                        self._object_store.delete_object(parent_id)
                    )
            await db.delete(parent)

        return web.json_response({"id": parent_id})

    async def add_youtube(self, request: web.Request) -> web.Response:
        async def save_audio(yt: YouTube) -> None:
            filesize, mime_type = await self._object_store.save_youtube_audio(yt)

            video = Catalog(
                id=yt.video_id,
                title=yt.title,
                description=yt.description,
                filename=yt.video_id,
                published=yt.publish_date,
                duration=yt.length,
                thumbnail_url=yt.thumbnail_url,
                audio_size=filesize,
                audio_type=mime_type
            )
            async with self._db_session.begin() as db:
                db.add(video)

        try:
            youtube = YouTube((await request.json())["url"])
        except RegexMatchError:
            raise web.HTTPBadRequest(text="Invalid YouTube link")

        async with self._db_session() as db:
            existing_video = await db.get(Catalog, youtube.video_id)
        if existing_video:
            raise web.HTTPConflict(text="Link already downloaded")

        asyncio.create_task(save_audio(youtube))
        return web.json_response(
            {"id": youtube.video_id, "type": "youtube"},
            status=HTTPStatus.ACCEPTED
        )

    async def start_book_upload(self, _: web.Request) -> web.Response:
        book_id = nanoid.generate(size=11)
        async with self._db_session.begin() as db:
            db.add(
                Catalog(
                    id=book_id,
                    filename=book_id,
                    thumbnail_url="audiobook.jpg"
                )
            )

        return web.json_response(
            {"id": book_id},
            status=HTTPStatus.CREATED
        )

    async def upload_book_chapter(self, request: web.Request) -> web.Response:
        book_id = request.match_info["book_id"]
        async with self._db_session.begin() as db:
            book = await db.get(
                Catalog,
                book_id,
                options=[joinedload(Catalog.children)]
            )
            if not book:
                raise web.HTTPBadRequest(text=f"Book '{book_id}' not found")
            chapter_id = nanoid.generate(size=11)
            chapter_filename = (await request.json())["filename"]
            book_part = Catalog(
                id=chapter_id,
                parent_id=book_id,
                filename=chapter_filename
            )
            db.add(book_part)
            book.children.append(book_part)
            await db.merge(book)

        upload_url = await self._object_store.save_book_chapter(
            book_id, chapter_id
        )
        return web.json_response(
            {"id": chapter_id, "url": upload_url},
            status=HTTPStatus.CREATED
        )

    async def complete_book_upload(self, request: web.Request) -> web.Response:
        book_id = request.match_info["book_id"]
        async with self._db_session.begin() as db:
            book = await db.get(Catalog, book_id)
            if book:
                chapters_count = await db.scalar(
                    select(func.count(Catalog.id))
                    .where(Catalog.parent_id == book_id)
                )
                if chapters_count > 0:
                    asyncio.create_task(self._tag_book(book_id))
                else:
                    await db.delete(book)
                    raise web.HTTPBadRequest(
                        text=f"Book '{book_id}' has no chapters"
                    )
            else:
                raise web.HTTPBadRequest(text=f"Book '{book_id}' not found")

        return web.json_response(
            {"id": book_id, "type": "audiobook"},
            status=HTTPStatus.ACCEPTED
        )

    async def _tag_book(self, book_id: str) -> None:
        async with self._db_session.begin() as db:
            book = await db.get(
                Catalog, book_id, options=[joinedload(Catalog.children)]
            )
            book_duration = 0
            book_title = None
            book_author = None
            for chapter in book.children:
                chapter_url = await self._object_store.get_object_url(
                    f"{book_id}/{chapter.id}"
                )
                file_info = await asyncio.to_thread(
                    get_file_info, chapter_url
                )

                book_duration += file_info.duration
                book_title = file_info.tags["album"][0]
                book_author = file_info.tags["artist"][0]

                chapter.title = file_info.tags["title"][0]
                chapter.description = f"{book_author}. {book_title}"
                chapter.duration = file_info.duration
                chapter.audio_size = file_info.size
                chapter.audio_type = file_info.mime_type
                await db.merge(chapter)

            book.title = book_title
            book.description = book_author
            book.duration = book_duration

        await db.merge(book)
