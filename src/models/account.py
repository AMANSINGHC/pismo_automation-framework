"""Wire shapes for request and response bodies for APIs exposed by ``accounts`` service."""

from typing import Any, Mapping
from dataclasses import dataclass, fields


@dataclass(frozen=True)
class CreateAccountRequest:

    document_number: str

    def to_payload(self) -> dict[str, Any]:
        return {"document_number": self.document_number}


@dataclass(frozen=True)
class AccountResponse:

    account_id: int
    document_number: str

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "AccountResponse":
        return cls(
            account_id=payload["account_id"],
            document_number=payload["document_number"],
        )


ACCOUNT_RESPONSE_FIELDS: Mapping[str, Any] = {f.name: f.type for f in fields(AccountResponse)}
