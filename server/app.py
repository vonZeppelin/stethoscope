import sys
import oci

from aiohttp import web
from typing import Optional

from db import create_session
from object_store import ObjectStore
from view import FeedView, FilesView


oci_config = oci.config.from_file("oci/oci.conf")
db_session = create_session(
    oci_config["db_user"],
    oci_config["db_password"],
    oci_config["db_dsn"]
)
object_store = ObjectStore(oci_config)
feed_view = FeedView(db_session, object_store)
files_view = FilesView(db_session, object_store)


async def build_app(ui_dir: Optional[str] = None):
    app = web.Application()

    app.router.add_get("/feed", feed_view.get_feed)
    app.router.add_get("/feed/{episode_id}", feed_view.get_media_link)
    app.router.add_get("/files", files_view.list_files)
    app.router.add_post("/files", files_view.add_file)
    app.router.add_delete("/files/{file_id}", files_view.delete_file)

    if ui_dir:
        app.router.add_static("/", ui_dir)

    return app


if __name__ == "__main__":
    _, ui_dir = sys.argv
    web.run_app(build_app(ui_dir))
