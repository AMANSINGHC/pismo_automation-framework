"""Small, dependency-free assertion helpers shared by the test modules."""

from http import HTTPStatus
from datetime import datetime
from typing import Any, Mapping
from src.utils.transport.api_response import ApiResponse


def assert_status(response: ApiResponse, expected: HTTPStatus) -> None:
    """Assert the response status, reporting the request and body when it differs."""
    assert response.status_code == expected, (
        f"Expected status {expected} but got {response.status_code} "
        f"for {response.method} {response.url}\nbody: {response.body!r}"
    )


def assert_shape(payload: Any, spec: Mapping[str, Any]) -> None:
    """Assert that ``payload`` is a JSON object holding every field of ``spec``."""
    assert isinstance(payload, Mapping), (
        f"Expected a JSON object, got {type(payload).__name__}: {payload!r}"
    )

    missing = sorted(field for field in spec if field not in payload)
    assert not missing, f"Missing fields: {missing}; payload: {payload!r}"

    mismatched = {
        field: f"got {type(payload[field]).__name__}, expected {expected.__name__}"
        for field, expected in spec.items()
        if not _matches_type(payload[field], expected)
    }
    assert not mismatched, f"Unexpected field types: {mismatched}; payload: {payload!r}"


def assert_iso8601(value: Any) -> datetime:
    """Assert an ISO-8601 date-time string, returning the parsed value."""
    assert isinstance(value, str), (
        f"Expected an ISO-8601 date-time string, got {type(value).__name__}: {value!r}"
    )
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AssertionError(f"{value!r} is not a valid ISO-8601 date-time: {exc}") from exc
    assert parsed.tzinfo is not None, f"{value!r} carries no timezone information"
    return parsed


def _matches_type(value: Any, expected: type) -> bool:
    """``bool`` never counts as ``int``; ``float`` accepts any JSON number."""
    if expected is float:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected is int:
        return isinstance(value, int) and not isinstance(value, bool)
    return isinstance(value, expected)
