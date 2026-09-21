"""Reusable, domain-free HTTP layer.

This module lives in ``src/utils/transport`` on purpose: it can be promoted into
a shared test-infrastructure package later without touching the service clients.
"""

import requests

from http import HTTPMethod
from typing import Any, Mapping
from urllib.parse import urljoin
from src.config.settings import Settings


class HttpClient:
    """One ``requests.Session`` bound to the base URL of the active environment."""

    def __init__(self, settings: Settings, session: requests.Session | None = None) -> None:
        self._settings = settings
        self._session = session or requests.Session()
        self._session.headers.update(dict(settings.headers))

    def request(
        self,
        method: HTTPMethod,
        path: str,
        *,
        json_body: Mapping[str, Any] | None = None,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> requests.Response:
        """Perform one HTTP call and return the untouched ``requests`` response.

        ``method`` is an :class:`http.HTTPMethod`; it is normalised to the
        uppercase token that goes on the wire. A transport failure is neither
        retried nor wrapped nor logged, so ``requests``' own exception reaches
        the caller as-is.
        """
        method = str(method).upper()
        url = self._url(path)
        request_headers = {**dict(self._settings.headers), **(headers or {})}
        request_timeout = timeout if timeout is not None else self._settings.timeout_s

        return self._session.request(
            method,
            url,
            json=json_body,
            params=params,
            headers=request_headers,
            timeout=request_timeout,
            allow_redirects=False,
        )

    def close(self) -> None:
        self._session.close()

    def _url(self, path: str) -> str:
        if path.startswith(("http://", "https://")):
            return path
        return urljoin(f"{self._settings.base_url}/", path.lstrip("/"))
