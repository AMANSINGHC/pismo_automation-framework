"""Contract tests for POST /accounts and GET /accounts/{accountId}.

Oracle: CONTRACT — expectations are backed by the OpenAPI contract:
documented status codes and response shape.
"""

import pytest

from http import HTTPStatus
from tests.data import unique_document_number
from src.clients.accounts_client import AccountsClient
from src.utils.assertions import assert_shape, assert_status
from src.models.account import ACCOUNT_RESPONSE_FIELDS, CreateAccountRequest

# The contract's documented example account ID.
# Prism returns the documented response for this ID
DOCUMENTED_ACCOUNT_ID = 1


@pytest.mark.contract
@pytest.mark.accounts
@pytest.mark.mock_compatible
class TestAccountsContract:

    @pytest.mark.smoke
    def test_create_account_documented_response(
        self, accounts_client: AccountsClient
    ) -> None:
        """Validate the documented POST /accounts success response."""
        request = CreateAccountRequest(document_number=unique_document_number())

        response = accounts_client.create_account(request)

        assert_status(response, HTTPStatus.CREATED)
        assert_shape(response.body, ACCOUNT_RESPONSE_FIELDS)

    @pytest.mark.smoke
    def test_get_account_documented_response(
        self, accounts_client: AccountsClient
    ) -> None:
        """Validate the documented GET /accounts/{accountId} success response."""
        response = accounts_client.get_account(DOCUMENTED_ACCOUNT_ID)

        assert_status(response, HTTPStatus.OK)
        assert_shape(response.body, ACCOUNT_RESPONSE_FIELDS)
