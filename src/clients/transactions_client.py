"""Service client for the ``transactions`` service."""

from http import HTTPMethod
from functools import partial
from src.utils.concurrency import run_concurrently
from src.clients.base_client import BaseServiceClient
from src.utils.transport.api_response import ApiResponse
from src.models.transaction import CreateTransactionRequest

TRANSACTIONS_PATH = "/transactions"

IDEMPOTENCY_KEY_HEADER = "Idempotency-Key"


class TransactionsClient(BaseServiceClient):

    def create_transaction(
        self, request: CreateTransactionRequest, *, idempotency_key: str | None = None
    ) -> ApiResponse:
        """Record a financial operation against an existing account.

        The response comes back untouched, so the caller asserts the status it
        expects; ``idempotency_key`` adds the assumption's header, and only when
        the caller passes one.
        """
        headers = {IDEMPOTENCY_KEY_HEADER: idempotency_key} if idempotency_key else None
        return self._send(
            HTTPMethod.POST, TRANSACTIONS_PATH, payload=request.to_payload(), headers=headers
        )

    def create_transaction_concurrently(
        self,
        request: CreateTransactionRequest,
        *,
        idempotency_key: str,
        attempts: int,
    ) -> list[ApiResponse]:
        """Send one transaction `attempts` times in flight under a single key."""
        return run_concurrently(
            [
                partial(self.create_transaction, request, idempotency_key=idempotency_key)
                for _ in range(attempts)
            ]
        )
