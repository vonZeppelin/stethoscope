import io
from dataclasses import dataclass

import mutagen
from requests import Session


@dataclass(frozen=True)
class FileInfo:
    size: int
    duration: int
    mime_type: str
    tags: mutagen.Tags


class _RemoteFile:

    def __init__(self, session: Session, file_url: str):
        self._file_url = file_url
        self._session = session
        self._offset = 0
        self._size = -1

    def read(self, count: int = -1) -> bytes:
        if count == 0:
            return b''
        if count < 0:
            end = self.size() - 1
        else:
            end = self._offset + count - 1

        request_headers = {"Range": f"bytes={self._offset}-{end}"}
        response = self._session.get(self._file_url, headers=request_headers)
        if not response.ok:
            raise IOError("IO error")
        self._offset += len(response.content)
        return response.content

    def tell(self) -> int:
        return self.seek(0, io.SEEK_CUR)

    def seek(self, offset: int, whence: int = 0) -> int:
        if whence == io.SEEK_SET:
            self._offset = offset
        elif whence == io.SEEK_CUR:
            self._offset += offset
        elif whence == io.SEEK_END:
            self._offset = self.size() + offset
        else:
            raise IOError("Invalid whence")
        return self._offset

    def size(self) -> int:
        if self._size < 0:
            response = self._session.head(self._file_url)
            if response.ok:
                self._size = int(response.headers["Content-Length"])
            else:
                raise IOError("Couldn't determine size")
        return self._size

    def write(self, data):
        raise NotImplementedError

    def truncate(self, size: int = None):
        raise NotImplementedError

    def flush(self):
        raise NotImplementedError

    def fileno(self):
        raise NotImplementedError


def get_file_info(file_url: str) -> FileInfo:
    with Session() as sess:
        remote_file = _RemoteFile(sess, file_url)
        mutagen_file = mutagen.File(remote_file, easy=True)
    return FileInfo(
        size=remote_file.size(),
        duration=int(mutagen_file.info.length),
        mime_type=mutagen_file.mime[0],
        tags=mutagen_file.tags
    )
