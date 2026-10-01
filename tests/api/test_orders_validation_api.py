import pytest

from tests.support import schemas
from tests.support.api_client import OrdersApi
from tests.support.data import order_payload

pytestmark = pytest.mark.api


@pytest.mark.parametrize(
    "overrides, field, error_type",
    [
        pytest.param({"customer": "   "}, "customer", "string_too_short", id="blank-customer"),
        pytest.param({"price": 0}, "price", "greater_than", id="zero-price"),
        pytest.param({"price": "abc"}, "price", "float_parsing", id="non-numeric-price"),
        pytest.param({"status": "archived"}, "status", "enum", id="unknown-status"),
        pytest.param({"discount": 10}, "discount", "extra_forbidden", id="unexpected-field"),
    ],
)
def test_create_order_rejects_invalid_payload(api: OrdersApi, overrides: dict, field: str, error_type: str):
    response = api.create(order_payload(**overrides))

    assert response.status_code == 422
    body = response.json()
    schemas.assert_schema(body, schemas.VALIDATION_ERROR)
    assert [(err["loc"][-1], err["type"]) for err in body["detail"]] == [(field, error_type)]
    # Nothing was persisted.
    assert api.list().json()["count"] == 3
