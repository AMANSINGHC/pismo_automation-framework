"""Service client for the ``accounts`` service."""

from http import HTTPMethod
from src.models.account import CreateAccountRequest
from src.clients.base_client import BaseServiceClient
from src.utils.transport.api_response import ApiResponse

ACCOUNTS_PATH = "/accounts"


class AccountsClient(BaseServiceClient):

    def create_account(self, request: CreateAccountRequest) -> ApiResponse:
        """Create a cardholder account.

        The response comes back untouched, so the caller asserts the status it
        expects.
        """
        return self._send(HTTPMethod.POST, ACCOUNTS_PATH, payload=request.to_payload())

    def get_account(self, account_id: int) -> ApiResponse:
        """Return a single account by its numeric ID."""
        return self._send(HTTPMethod.GET, f"{ACCOUNTS_PATH}/{account_id}")
