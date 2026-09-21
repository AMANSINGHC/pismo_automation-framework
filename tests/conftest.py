"""Shared fixtures: the HTTP layer, the service clients, and the state they need."""

import pytest

from http import HTTPStatus
from collections.abc import Iterator
from src.config.settings import Settings
from tests.data import unique_document_number
from src.utils.transport.http_client import HttpClient
from src.clients.accounts_client import AccountsClient
from src.clients.transactions_client import TransactionsClient
from src.models.account import AccountResponse, CreateAccountRequest


@pytest.fixture(scope="session")
def http_client(settings: Settings) -> Iterator[HttpClient]:
    """The shared HTTP layer, bound to the selected environment."""
    client = HttpClient(settings)
    yield client
    client.close()


@pytest.fixture(scope="session")
def accounts_client(http_client: HttpClient) -> AccountsClient:
    """Client for the contract's `accounts` tag."""
    return AccountsClient(http_client)


@pytest.fixture(scope="session")
def transactions_client(http_client: HttpClient) -> TransactionsClient:
    """Client for the contract's `transactions` tag."""
    return TransactionsClient(http_client)


@pytest.fixture(scope="session")
def existing_account(accounts_client: AccountsClient) -> AccountResponse:
    """An account that really exists, created over the API before the tests run."""
    response = accounts_client.create_account(
        CreateAccountRequest(document_number=unique_document_number())
    )

    if response.status_code != HTTPStatus.CREATED:
        raise RuntimeError(
            f"Could not create the account this run needs: expected {HTTPStatus.CREATED} "
            f"from {response.method} {response.url}, got {response.status_code}\n"
            f"body: {response.body!r}"
        )

    return response.model(AccountResponse)
