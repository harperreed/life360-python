import asyncio
from contextlib import AbstractAsyncContextManager, suppress
import logging
import re
from types import TracebackType
from typing import Any, Optional, Union, cast

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
_MEMBER_UPDATE_URL_FMT = f"{_CIRCLE_MEMBERS_URL_FMT}/{{member_id}}/request"
_RETRY_EXCEPTIONS = (aiohttp.ClientConnectionError, asyncio.TimeoutError)

_URL_REDACTION = (re.compile(r"(circles/)[a-zA-Z0-9-]+/"), r"\1REDACTED/")
_URL_REDACTIONS = (_URL_REDACTION,)
_EXC_REPR_REDACTIONS = (
    _URL_REDACTION,
    (re.compile(r"('Bearer )[^']+'"), r"\1REDACTED'"),
    (re.compile(r"('L360-ETag': ')[^']*'"), r"\1REDACTED'"),
)
_LOGGER = logging.getLogger(__name__)

CLIENT_TOKEN = (
    "cFJFcXVnYWJSZXRyZTRFc3RldGhlcnVmcmVQdW1hbUV4dWNyRU"
    "h1YzptM2ZydXBSZXRSZXN3ZXJFQ2hBUHJFOTZxYWtFZHI0Vg=="
)
HTTP_FORBIDDEN = 403
HTTP_BAD_GATEWAY = 502
HTTP_SERVICE_UNAVAILABLE = 503
HTTP_GATEWAY_TIME_OUT = 504

RETRY_CLIENT_RESPONSE_ERRORS = (
    HTTP_BAD_GATEWAY,
    HTTP_SERVICE_UNAVAILABLE,
    HTTP_GATEWAY_TIME_OUT,
)


def _redact(s, redactions):
    """Redact string."""
    result = s
    for pat, repl in redactions:
        result = pat.sub(repl, result)
    return result


def _retry(exc):
    """Determine if request should be retried."""
    if isinstance(exc, _RETRY_EXCEPTIONS):
        return True
    return (
        isinstance(exc, aiohttp.ClientResponseError)
        and exc.status in RETRY_CLIENT_RESPONSE_ERRORS
    )


class Life360(AbstractAsyncContextManager):
    """Life360 API."""

    _timeout: Optional[aiohttp.ClientTimeout] = None

    def __init__(
        self,
        *,
        session: Optional[aiohttp.ClientSession] = None,
        timeout: Optional[Union[float, aiohttp.ClientTimeout]] = None,
        max_retries: Optional[int] = None,
        authorization: Optional[str] = None,
    ) -> None:
        """Initialize API.

        timeout controls total timeout.
        timeout = None -> default timeout,
        timeout = 0 -> disable timeout
        """
        self._session_provided = bool(session)
        if not session:
            session = aiohttp.ClientSession()
        self._session: Optional[aiohttp.ClientSession] = session
        if isinstance(timeout, float):
            self._timeout = aiohttp.ClientTimeout(total=timeout)
        elif isinstance(timeout, aiohttp.ClientTimeout):
            self._timeout = timeout
        self._max_attempts = max_retries + 1 if max_retries else 1
        self._authorization = authorization

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> Optional[bool]:
        """Exit context manager."""
        await self.close()
        return await super().__aexit__(exc_type, exc_value, traceback)

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

    async def update_location(
        self, circle_id: str, member_id: str
    ) -> list[dict[str, Any]]:
        """Request location update for Member."""
        return await self._post(
            _MEMBER_UPDATE_URL_FMT.format(circle_id=circle_id, member_id=member_id),
            {"type": "location"},
        )

    async def close(self) -> None:
        """Close."""
        if not self._session:
            return
        if not self._session_provided:
            await self._session.close()
        self._session = None

    async def _get(self, url: str) -> Any:
        """Get URL."""
        if not self._authorization:
            raise Life360Error("No authorization. Call get_authorization")
        return await self._request(method="get", url=url)

    async def _post(self, url: str, data: Optional[dict[str, Any]] = None) -> Any:
        """Get URL."""
        if not self._authorization:
            raise Life360Error("No authorization. Call get_authorization")
        return await self._request(method="post", url=url, data=data)

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
        if not self._session:
            raise Life360Error("Object is closed")

        if not msg:
            msg = f"Error {method.upper()}({_redact(url, _URL_REDACTIONS)})"

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

        for attempt in range(1, self._max_attempts + 1):
            status = None
            resp_json = {}
            try:
                resp = cast(
                    aiohttp.ClientResponse,
                    await getattr(self._session, method)(url, **kwargs),
                )
                status = resp.status
                if not resp.ok:
                    with suppress(Exception):
                        resp_json = await resp.json()
                    resp.raise_for_status()
                resp_json = await resp.json()
            except Exception as exc:
                _LOGGER.debug(
                    "%s, attempt %i: %s",
                    msg,
                    attempt,
                    _redact(repr(exc), _EXC_REPR_REDACTIONS),
                )
                if not _retry(exc) or attempt == self._max_attempts:
                    # Try to return a useful error message.
                    if not (err_msg := resp_json.get("errorMessage", "").lower()):
                        err_msg = exc.__class__.__name__
                        if exc_args := _redact(str(exc), _URL_REDACTIONS):
                            err_msg += f": {exc_args}"
                    if status == HTTP_FORBIDDEN:
                        raise LoginError(err_msg)
                    raise CommError(err_msg)
            else:
                return resp_json
