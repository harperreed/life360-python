import logging
from typing import Any, Optional, cast

import aiohttp

from .exceptions import *

_PROTOCOL = "https://"
_HOST = "api.life360.com"
_BASE_URL = f"{_PROTOCOL}{_HOST}"
_BASE_CMD = f"{_BASE_URL}/v3/"
_TOKEN_URL = f"{_BASE_CMD}oauth2/token.json"
_CIRCLES_URL = f"{_BASE_CMD}circles.json"
_CIRCLE_URL_FMT = f"{_BASE_CMD}circles/{{circle_id}}"
_CIRCLE_MEMBERS_URL_FMT = f"{_CIRCLE_URL_FMT}/members"
_CIRCLE_PLACES_URL_FMT = f"{_CIRCLE_URL_FMT}/places"

_LOGGER = logging.getLogger(__name__)

CLIENT_TOKEN = (
    "cFJFcXVnYWJSZXRyZTRFc3RldGhlcnVmcmVQdW1hbUV4dWNyRU"
    "h1YzptM2ZydXBSZXRSZXN3ZXJFQ2hBUHJFOTZxYWtFZHI0Vg=="
)
HTTP_FORBIDDEN = 403


class Life360:
    """Life360 API."""

    _timeout: Optional[aiohttp.ClientTimeout] = None

    def __init__(
        self,
        session: Optional[aiohttp.ClientSession] = None,
        timeout: Optional[float] = None,
        authorization: Optional[str] = None,
    ) -> None:
        """Initialize API.

        timeout controls total timeout.
        timeout = None -> default timeout,
        timeout = 0 -> disable timeout
        """
        if not session:
            session = aiohttp.ClientSession()
        self._session = session
        if timeout is not None:
            self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._authorization = authorization

    async def get_authorization(self, username: str, password: str) -> str:
        """Get authorization string from username & password."""
        resp_json = await self._request(
            method="post",
            url=_TOKEN_URL,
            authorization=f"Basic {CLIENT_TOKEN}",
            data={"grant_type": "password", "username": username, "password": password},
            msg="Error while getting authorization token",
        )

        try:
            self._authorization = (
                f"{resp_json['token_type']} {resp_json['access_token']}"
            )
        except KeyError:
            raise Life360Error(
                f"Unexpected response while getting authorization token: {resp_json}"
            )

        return self._authorization

    async def get_circles(self) -> list[dict[str, Any]]:
        """Get basic data about all Circles."""
        return (await self._get(_CIRCLES_URL))["circles"]

    async def get_circle(self, circle_id: str) -> list[dict[str, Any]]:
        """Get details for given Circle."""
        return await self._get(_CIRCLE_URL_FMT.format(circle_id=circle_id))

    async def get_circle_members(self, circle_id: str) -> list[dict[str, Any]]:
        """Get details for Members in given Circle."""
        return (await self._get(_CIRCLE_MEMBERS_URL_FMT.format(circle_id=circle_id)))[
            "members"
        ]

    async def get_circle_places(self, circle_id: str) -> list[dict[str, Any]]:
        """Get details for Places in given Circle."""
        return (await self._get(_CIRCLE_PLACES_URL_FMT.format(circle_id=circle_id)))[
            "places"
        ]

    async def _get(self, url: str) -> Any:
        """Get URL."""
        if not self._authorization:
            raise Life360Error("No authorization. Call get_authorization")
        return await self._request(method="get", url=url)

    async def _request(
        self,
        *,
        method: str,
        url: str,
        authorization: Optional[str] = None,
        data: Optional[dict[str, Any]] = None,
        msg: Optional[str] = None,
    ) -> Any:
        """Make a request to server."""
        if not msg:
            msg = f"Error {method.upper()}({url})"

        kwargs = {
            "headers": {
                "Accept": "application/json",
                "cache-control": "no-cache",
                "Authorization": authorization
                if authorization
                else self._authorization,
            },
        }
        if data is not None:
            kwargs["data"] = data
        if self._timeout is not None:
            kwargs["timeout"] = self._timeout

        resp_json = {}
        try:
            resp = cast(
                aiohttp.ClientResponse,
                await getattr(self._session, method)(url, **kwargs),
            )
            resp_json = await resp.json()
            resp.raise_for_status()
        except aiohttp.ClientResponseError as exc:
            _LOGGER.debug("%s: %s", msg, exc)
            # Try to return a useful error message.
            err_msg = resp_json.get("errorMessage", "").lower() or str(exc)
            if resp.status == HTTP_FORBIDDEN:
                raise LoginError(err_msg)
            raise CommError(err_msg)

        return resp_json
