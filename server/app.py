import sys

from aiohttp import web
from google.oauth2.service_account import Credentials
from typing import Optional

from firestore import init_firestore
from objectstore import ObjectStore
from view import FeedView, FilesView


gcloud_credentials = Credentials.from_service_account_file(
    "cloud-creds.json"
)
init_firestore(gcloud_credentials)
object_store = ObjectStore(gcloud_credentials)
feed_view = FeedView(object_store)
files_view = FilesView(object_store)


async def healthcheck(_: web.Request) -> web.Response:
    return web.Response(text="OK")


async def build_app(ui_dir: Optional[str] = None):
    app = web.Application()
    app.add_routes(
        [
            web.get("/api/files", files_view.list_files),
            web.post("/api/files", files_view.add_file),
            web.delete("/api/files/{file_id}", files_view.delete_file),
            web.get("/api/feed", feed_view.get_feed),
            web.get("/api/feed/{episode_id}", feed_view.get_media_link),
            web.get("/api/health", healthcheck)
        ]
    )
    if ui_dir:
        app.add_routes([web.static("/", ui_dir)])

    return app


if __name__ == "__main__":
    _, ui_dir = sys.argv
    web.run_app(build_app(ui_dir))
