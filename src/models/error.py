"""Wire shape of the contract's ``handler.errorResponse`` definition."""

from typing import Any, Mapping
from dataclasses import dataclass, fields


@dataclass(frozen=True)
class ErrorResponse:

    error: str

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "ErrorResponse":
        return cls(error=payload["error"])


ERROR_RESPONSE_FIELDS: Mapping[str, Any] = {f.name: f.type for f in fields(ErrorResponse)}
