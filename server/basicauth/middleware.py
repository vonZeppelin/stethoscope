from aiohttp import hdrs, web, BasicAuth
from typing import Callable, Dict, Iterable


def basic_auth_middleware(
        urls: Iterable[str],
        auth_dict: Dict[str, str],
        hash_strategy: Callable[[str], str] = lambda x: x
):
    @web.middleware
    async def middleware(request: web.Request, handler) -> web.StreamResponse:
        if request.method != hdrs.METH_OPTIONS:
            for url in urls:
                if not request.path.startswith(url):
                    continue

                auth_header = request.headers.get(hdrs.AUTHORIZATION, "")
                if _check_access(auth_dict, auth_header, hash_strategy):
                    return await handler(request)
                else:
                    raise web.HTTPUnauthorized(
                        headers={hdrs.WWW_AUTHENTICATE: "Basic"}
                    )

        return await handler(request)

    return middleware


def _check_access(
        auth_dict: Dict[str, str],
        auth_header: str,
        hash_strategy: Callable[[str], str] = lambda x: x
) -> bool:
    try:
        creds = BasicAuth.decode(auth_header)
    except ValueError:
        return False

    hashed_stored_password = auth_dict.get(creds.login)
    hashed_request_password = hash_strategy(creds.password)

    return hashed_stored_password == hashed_request_password
