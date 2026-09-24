"""Contract test for POST /transactions.

Oracle: CONTRACT — expectations are backed by the OpenAPI contract:
documented status and response shape.
"""

import pytest

from http import HTTPStatus
from src.utils.assertions import assert_shape, assert_status
from src.clients.transactions_client import TransactionsClient
from src.models.transaction import TRANSACTION_RESPONSE_FIELDS, CreateTransactionRequest

# The contract's own example request:
# account_id=1, amount=50, operation_type_id=1.
DOCUMENTED_AMOUNT = 50
DOCUMENTED_ACCOUNT_ID = 1
DOCUMENTED_OPERATION_TYPE_ID = 1


@pytest.mark.contract
@pytest.mark.transactions
@pytest.mark.mock_compatible
class TestTransactionsContract:

    @pytest.mark.smoke
    def test_create_transaction_documented_response(
        self, transactions_client: TransactionsClient
    ) -> None:
        """Validate the documented POST /transactions success response."""
        request = CreateTransactionRequest(
            account_id=DOCUMENTED_ACCOUNT_ID,
            amount=DOCUMENTED_AMOUNT,
            operation_type_id=DOCUMENTED_OPERATION_TYPE_ID,
        )

        response = transactions_client.create_transaction(request)

        assert_status(response, HTTPStatus.CREATED)
        assert_shape(response.body, TRANSACTION_RESPONSE_FIELDS)
