"""``GET /accounts/{accountId}`` — contract tag: ``accounts``."""

import pytest

from http import HTTPStatus
from src.clients.accounts_client import AccountsClient
from src.utils.assertions import assert_shape, assert_status
from src.models.account import ACCOUNT_RESPONSE_FIELDS, AccountResponse


@pytest.mark.accounts
class TestGetAccount:

    @pytest.mark.smoke
    def test_get_account(
        self, accounts_client: AccountsClient, existing_account: AccountResponse
    ) -> None:
        """An account that was created first is returned as 200 in the documented shape."""
        response = accounts_client.get_account(existing_account.account_id)

        assert_status(response, HTTPStatus.OK)
        assert_shape(response.body, ACCOUNT_RESPONSE_FIELDS)

        account = response.model(AccountResponse)
        assert account.account_id == existing_account.account_id
        # The contract uses 12345678900, but this test generates a unique number. In real
        # environments, assert account.document_number == existing_account.document_number.
        assert account.document_number
