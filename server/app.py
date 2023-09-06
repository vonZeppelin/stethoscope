import asyncio
import os

from aiohttp import web
import aiohttp_cors
import oci

from basicauth import basic_auth_middleware
from db import create_session
from objectstore import ObjectStore
from view import FeedView, FilesView

UI_HOST_URL = "https://stethoscope.lbogdanov.dev"


async def healthcheck(_: web.Request) -> web.Response:
    return web.Response(text="OK")


async def build_app():
    db_session = await create_session(os.getenv("DB_FILE"))
    oci_config = await asyncio.to_thread(
        oci.config.from_file, os.getenv("OCI_CONFIG_FILE")
    )
    user, password = os.getenv("BASIC_AUTH").split(":", 1)

    app = web.Application(
        middlewares=[
            basic_auth_middleware(["/files"], {user: password})
        ]
    )
    object_store = ObjectStore(oci_config)
    feed_view = FeedView(UI_HOST_URL, db_session, object_store)
    files_view = FilesView(db_session, object_store)

    app.router.add_get("/youtube/feed", feed_view.get_youtube_feed)
    app.router.add_get("/book/{book_id}/feed", feed_view.get_audiobook_feed)
    app.router.add_get("/media/{episode_id}", feed_view.get_media_url)
    app.router.add_get("/health", healthcheck)

    cors_opts = {
        UI_HOST_URL: aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            allow_headers="*",
            allow_methods="*"
        )
    }
    cors = aiohttp_cors.setup(app)
    cors.add(
        app.router.add_get("/files", files_view.list_files),
        cors_opts
    )
    cors.add(
        app.router.add_delete("/files/{file_id}", files_view.delete_file),
        cors_opts
    )
    cors.add(
        app.router.add_post("/files/youtube/add", files_view.add_youtube),
        cors_opts
    )
    cors.add(
        app.router.add_post("/files/book/add", files_view.start_book_upload),
        cors_opts
    )
    cors.add(
        app.router.add_post("/files/book/{book_id}/add_chapter", files_view.upload_book_chapter),
        cors_opts
    )
    cors.add(
        app.router.add_post("/files/book/{book_id}/complete", files_view.complete_book_upload),
        cors_opts
    )

    if ui_dir := os.getenv("UI_PATH"):
        app.router.add_static("/", ui_dir)

    return app


if __name__ == "__main__":
    web.run_app(build_app())
