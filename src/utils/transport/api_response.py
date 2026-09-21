"""Uniform, transport-agnostic view of one HTTP call."""

import requests

from dataclasses import dataclass
from typing import Any, Mapping, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class ApiResponse:
    """What the service clients hand back to the tests.

    Tests assert on ``status_code``, ``body`` or the parsed ``model``; the raw
    ``requests.Response`` stays available as an escape hatch.
    """

    method: str
    url: str
    status_code: int
    headers: Mapping[str, str]
    body: Any
    elapsed_ms: float
    raw: requests.Response

    def model(self, model_type: type[T]) -> T:
        """Parse the body into a typed model from :mod:`src.models`."""
        return model_type.from_payload(self.body)  # type: ignore[attr-defined]
