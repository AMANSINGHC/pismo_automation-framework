"""``GET /accounts/{accountId}`` — contract tag: ``accounts``."""

import pytest

from http import HTTPStatus
from tests.data import NON_EXISTENT_ACCOUNT_ID
from src.clients.accounts_client import AccountsClient
from src.utils.assertions import assert_shape, assert_status
from src.models.error import ERROR_RESPONSE_FIELDS, ErrorResponse
from src.models.account import ACCOUNT_RESPONSE_FIELDS, AccountResponse

ACCOUNT_NOT_FOUND_ERROR = "account not found"


@pytest.mark.accounts
class TestGetAccount:

    @pytest.mark.pre_release
    def test_get_existing_account(
        self, accounts_client: AccountsClient, existing_account: AccountResponse
    ) -> None:
        """An account that was created first is returned as 200 in the documented shape."""
        response = accounts_client.get_account(existing_account.account_id)

        assert_status(response, HTTPStatus.OK)
        assert_shape(response.body, ACCOUNT_RESPONSE_FIELDS)

        account = response.model(AccountResponse)
        assert account.account_id == existing_account.account_id
        assert account.document_number == existing_account.document_number

    @pytest.mark.smoke
    @pytest.mark.negative
    def test_get_unknown_account(self, accounts_client: AccountsClient) -> None:
        """An account_id that does not exist is answered with 404 and the error shape."""
        response = accounts_client.get_account(NON_EXISTENT_ACCOUNT_ID)

        assert_status(response, HTTPStatus.NOT_FOUND)
        assert_shape(response.body, ERROR_RESPONSE_FIELDS)

        error = response.model(ErrorResponse)
        assert error.error == ACCOUNT_NOT_FOUND_ERROR
