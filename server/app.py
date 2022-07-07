import falcon


class FilesResource:
    def on_get(self, req, resp):
        resp.status = falcon.HTTP_OK
        resp.media = [
            {"id": 1, "name": "Some video", "description": "Test"},
            {"id": 2, "name": "Another video", "description": "Testing"}
        ]

    def on_post(self, req, resp):
        file_url = req.media["url"]

        resp.status = falcon.HTTP_ACCEPTED
        resp.media = {
            "url": file_url,
            "taskid": 1
        }


app = falcon.App()
app.add_route("/files", FilesResource())


# TODO proper local dev setup
from pathlib import Path
cwd = Path(__file__).parent
app.add_static_route("/", cwd.parent / "ui" / "public")
