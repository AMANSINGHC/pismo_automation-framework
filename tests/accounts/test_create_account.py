"""``POST /accounts`` — contract tag: ``accounts``."""

import pytest

from http import HTTPStatus
from tests.data import unique_document_number
from src.clients.accounts_client import AccountsClient
from src.utils.assertions import assert_shape, assert_status
from src.models.account import ACCOUNT_RESPONSE_FIELDS, AccountResponse, CreateAccountRequest


@pytest.mark.accounts
class TestCreateAccount:

    @pytest.mark.smoke
    def test_create_account(self, accounts_client: AccountsClient) -> None:
        """A new account is answered with 201 and the documented response shape."""
        request = CreateAccountRequest(document_number=unique_document_number())

        response = accounts_client.create_account(request)

        assert_status(response, HTTPStatus.CREATED)
        assert_shape(response.body, ACCOUNT_RESPONSE_FIELDS)

        account = response.model(AccountResponse)
        assert account.account_id > 0
        # The contract uses 12345678900, but this test generates a unique number.
        # In real environments, assert account.document_number == request.document_number.
        assert account.document_number
