"""Shared plumbing for the per-resource service clients."""

import requests

from http import HTTPMethod
from typing import Any, Mapping
from src.utils.transport.http_client import HttpClient
from src.utils.transport.api_response import ApiResponse


class BaseServiceClient:
    """One HTTP call in, one :class:`ApiResponse` out."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def _send(
        self,
        method: HTTPMethod,
        path: str,
        *,
        payload: Mapping[str, Any] | None = None,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> ApiResponse:
        """Send one request and return the response, whatever its status."""
        response = self._http.request(
            method, path, json_body=payload, params=params, headers=headers
        )
        return ApiResponse(
            method=str(method).upper(),
            url=response.url,
            status_code=response.status_code,
            headers=dict(response.headers),
            body=_parse_body(response),
            elapsed_ms=response.elapsed.total_seconds() * 1000,
            raw=response,
        )


def _parse_body(response: requests.Response) -> Any:
    """Decode the body as JSON, falling back to the raw text for non-JSON replies."""
    try:
        return response.json()
    except ValueError:
        return response.text or None
