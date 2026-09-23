"""Wire shapes and operation-type semantics for APIs exposed by ``transactions`` service."""

from enum import Enum, IntEnum
from typing import Any, Mapping
from dataclasses import dataclass, fields


class OperationType(IntEnum):
    """Operation type IDs documented in the ``POST /transactions`` summary."""

    NORMAL_PURCHASE = 1
    INSTALLMENT_PURCHASE = 2
    WITHDRAWAL = 3
    CREDIT_VOUCHER = 4


class TransactionType(str, Enum):
    """How the ``type`` field spells the direction the money moved."""

    DEBIT = "debit"
    CREDIT = "credit"


@dataclass(frozen=True)
class CreateTransactionRequest:
    account_id: int
    amount: float
    operation_type_id: int | OperationType

    def to_payload(self) -> dict[str, Any]:
        return {
            "account_id": self.account_id,
            "amount": self.amount,
            "operation_type_id": int(self.operation_type_id),
        }


@dataclass(frozen=True)
class TransactionResponse:

    transaction_id: int
    account_id: int
    amount: float
    operation_type_id: int
    type: str
    event_date: str

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "TransactionResponse":
        return cls(
            transaction_id=payload["transaction_id"],
            account_id=payload["account_id"],
            amount=payload["amount"],
            operation_type_id=payload["operation_type_id"],
            type=payload["type"],
            event_date=payload["event_date"],
        )


TRANSACTION_RESPONSE_FIELDS: Mapping[str, Any] = {
    f.name: f.type for f in fields(TransactionResponse)
}
