"""Service client for the ``transactions`` service."""

from http import HTTPMethod
from src.clients.base_client import BaseServiceClient
from src.utils.transport.api_response import ApiResponse
from src.models.transaction import CreateTransactionRequest

TRANSACTIONS_PATH = "/transactions"


class TransactionsClient(BaseServiceClient):

    def create_transaction(self, request: CreateTransactionRequest) -> ApiResponse:
        """Record a financial operation against an existing account.

        The response comes back untouched, so the caller asserts the status it
        expects.
        """
        return self._send(HTTPMethod.POST, TRANSACTIONS_PATH, payload=request.to_payload())
