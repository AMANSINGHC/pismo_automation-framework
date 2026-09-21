"""``POST /transactions`` — contract tag: ``transactions``."""

import pytest

from src.models.transaction import (
    TRANSACTION_RESPONSE_FIELDS,
    CreateTransactionRequest,
    OperationType,
    TransactionResponse,
)
from http import HTTPStatus
from src.models.account import AccountResponse
from src.clients.transactions_client import TransactionsClient
from src.utils.assertions import assert_iso8601, assert_shape, assert_status

PURCHASE_AMOUNT = 50.0


@pytest.mark.transactions
class TestCreateTransaction:
    """Smoke coverage for recording a financial operation."""

    @pytest.mark.smoke
    def test_create_transaction(
        self, transactions_client: TransactionsClient, existing_account: AccountResponse
    ) -> None:
        """A purchase against an existing account is accepted with 201 in the documented shape."""
        request = CreateTransactionRequest(
            account_id=existing_account.account_id,
            amount=PURCHASE_AMOUNT,
            operation_type_id=OperationType.NORMAL_PURCHASE,
        )

        response = transactions_client.create_transaction(request)

        assert_status(response, HTTPStatus.CREATED)
        assert_shape(response.body, TRANSACTION_RESPONSE_FIELDS)
        assert_iso8601(response.body["event_date"], field="event_date")

        transaction = response.model(TransactionResponse)
        # The contract does not explicitly define the financial sign/type for each operation.
        # Ideally, assertions should be based on that mapping.
        assert transaction.account_id == existing_account.account_id
        assert transaction.operation_type_id == OperationType.NORMAL_PURCHASE
        assert transaction.transaction_id > 0
        assert transaction.type
