"""Contract tests for documented request-validation error responses.

Each test violates one documented request field type and asserts only the
documented HTTP status and `handler.errorResponse` response shape.

The contract does not bind error-message text, so messages are intentionally
not asserted.

The documented 404 and 405 responses, and malformed-JSON behavior, are excluded
because the current Prism mock cannot exercise them with the documented
`errorResponse` shape. Those limitations are documented in the C3b findings.
"""

import pytest

from http import HTTPStatus
from src.models.error import ERROR_RESPONSE_FIELDS
from src.models.account import CreateAccountRequest
from src.clients.accounts_client import AccountsClient
from src.models.transaction import CreateTransactionRequest
from src.utils.assertions import assert_shape, assert_status
from src.clients.transactions_client import TransactionsClient

# Deliberately violate the documented request field types.
NON_STRING_DOCUMENT_NUMBER = 123
NON_INTEGER_PATH_ACCOUNT_ID = "not-an-integer"
NON_INTEGER_BODY_ACCOUNT_ID = "not-an-integer"

DOCUMENTED_AMOUNT = 50
DOCUMENTED_OPERATION_TYPE_ID = 1


@pytest.mark.contract
@pytest.mark.mock_compatible
class TestErrorResponsesContract:

    @pytest.mark.accounts
    @pytest.mark.negative
    def test_create_account_with_invalid_document_number_type(
        self, accounts_client: AccountsClient
    ) -> None:
        """Oracle: CONTRACT — documented 400 + errorResponse for invalid field type."""
        request = CreateAccountRequest(
            document_number=NON_STRING_DOCUMENT_NUMBER
        )

        response = accounts_client.create_account(request)

        assert_status(response, HTTPStatus.BAD_REQUEST)
        assert_shape(response.body, ERROR_RESPONSE_FIELDS)

    @pytest.mark.accounts
    @pytest.mark.negative
    def test_get_account_with_invalid_id_type(self, accounts_client: AccountsClient) -> None:
        """Oracle: CONTRACT — documented 400 + errorResponse for invalid path type."""
        response = accounts_client.get_account(
            NON_INTEGER_PATH_ACCOUNT_ID
        )

        assert_status(response, HTTPStatus.BAD_REQUEST)
        assert_shape(response.body, ERROR_RESPONSE_FIELDS)

    @pytest.mark.transactions
    @pytest.mark.negative
    def test_create_transaction_with_invalid_account_id_type(
        self, transactions_client: TransactionsClient
    ) -> None:
        """Oracle: CONTRACT — documented 422 + errorResponse for invalid field type."""
        request = CreateTransactionRequest(
            account_id=NON_INTEGER_BODY_ACCOUNT_ID,  # type: ignore[arg-type]
            amount=DOCUMENTED_AMOUNT,
            operation_type_id=DOCUMENTED_OPERATION_TYPE_ID,
        )

        response = transactions_client.create_transaction(request)

        assert_status(response, HTTPStatus.UNPROCESSABLE_ENTITY)
        assert_shape(response.body, ERROR_RESPONSE_FIELDS)
