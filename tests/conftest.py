"""Shared fixtures: the HTTP layer, the service clients, and the state they need."""

import pytest

from http import HTTPStatus
from collections.abc import Iterator
from src.config.settings import Settings
from tests.data import unique_document_number
from src.clients.accounts_client import AccountsClient
from src.utils.transport.http_client import HttpClient
from src.utils.assertions import assert_shape, assert_status
from src.clients.transactions_client import TransactionsClient
from src.models.account import ACCOUNT_RESPONSE_FIELDS, AccountResponse, CreateAccountRequest


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
    """An account created through the API and shared by tests requiring existing state.
    
    It is session-scoped and shared, so anything counting transactions on it would 
    count the other tests' writes too.
    """
    return _created_account(accounts_client)


@pytest.fixture
def dedicated_account(accounts_client: AccountsClient) -> AccountResponse:
    """Create a fresh account for the current test to isolate account state."""
    return _created_account(accounts_client)


def _created_account(accounts_client: AccountsClient) -> AccountResponse:
    """Create an account over the API, asserting the documented creation response."""
    request = CreateAccountRequest(
        document_number=unique_document_number()
    )
    response = accounts_client.create_account(request)

    assert_status(response, HTTPStatus.CREATED)
    assert_shape(response.body, ACCOUNT_RESPONSE_FIELDS)

    account = response.model(AccountResponse)
    assert account.account_id > 0
    assert account.document_number == request.document_number
    
    return account
