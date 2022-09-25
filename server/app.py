import aiohttp_cors
import sys

from aiohttp import web
from google.oauth2.service_account import Credentials
from typing import Optional

from firestore import init_firestore
from objectstore import ObjectStore
from view import FeedView, FilesView


UI_HOST_URL = "https://stethoscope.lbogdanov.dev"

gcloud_credentials = Credentials.from_service_account_file(
    "cloud-creds.json"
)
init_firestore(gcloud_credentials)
object_store = ObjectStore(gcloud_credentials)
feed_view = FeedView(UI_HOST_URL, object_store)
files_view = FilesView(object_store)


async def healthcheck(_: web.Request) -> web.Response:
    return web.Response(text="OK")


async def build_app(ui_dir: Optional[str] = None):
    app = web.Application()
    cors_opts = {
        UI_HOST_URL: aiohttp_cors.ResourceOptions(
            allow_credentials=True, allow_headers="*", allow_methods="*"
        )
    }
    cors = aiohttp_cors.setup(app)

    cors.add(
        app.router.add_get("/files", files_view.list_files),
        cors_opts
    )
    cors.add(
        app.router.add_post("/files", files_view.add_file),
        cors_opts
    )
    cors.add(
        app.router.add_delete("/files/{file_id}", files_view.delete_file),
        cors_opts
    )

    app.router.add_get("/feed", feed_view.get_feed)
    app.router.add_get("/feed/{episode_id}", feed_view.get_media_link)
    app.router.add_get("/health", healthcheck)

    if ui_dir:
        app.router.add_static("/", ui_dir)

    return app


if __name__ == "__main__":
    _, ui_dir = sys.argv
    web.run_app(build_app(ui_dir))
