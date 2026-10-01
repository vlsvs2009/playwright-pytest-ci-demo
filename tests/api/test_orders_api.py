import pytest

from tests.support import schemas
from tests.support.api_client import OrdersApi
from tests.support.data import SEEDED_CUSTOMERS, order_payload

pytestmark = pytest.mark.api


@pytest.mark.smoke
def test_list_orders_returns_seed_data(api: OrdersApi):
    response = api.list()

    assert response.status_code == 200
    body = response.json()
    schemas.assert_schema(body, schemas.ORDER_LIST)
    assert body["count"] == len(body["items"]) == 3
    assert [order["customer"] for order in body["items"]] == SEEDED_CUSTOMERS


@pytest.mark.smoke
def test_create_order_and_read_it_back(api: OrdersApi):
    payload = order_payload(price=249.9, status="in_progress")

    created = api.create(payload)

    assert created.status_code == 201
    order = created.json()
    schemas.assert_schema(order, schemas.ORDER)
    assert {k: order[k] for k in payload} == payload
    assert api.get(order["id"]).json() == order


def test_create_order_normalizes_input(api: OrdersApi):
    payload = order_payload(customer="  Jane Doe  ", price=10.456)
    del payload["status"]

    order = api.create_ok(payload)

    assert order["customer"] == "Jane Doe"  # surrounding whitespace trimmed
    assert order["price"] == 10.46  # rounded to cents
    assert order["status"] == "new"  # default applied


def test_update_order_status(api: OrdersApi):
    order = api.create_ok(order_payload())

    response = api.update(order["id"], {"status": "done"})

    assert response.status_code == 200
    updated = response.json()
    schemas.assert_schema(updated, schemas.ORDER)
    assert updated["status"] == "done"
    assert {k: v for k, v in updated.items() if k != "status"} == {k: v for k, v in order.items() if k != "status"}


def test_delete_order(api: OrdersApi):
    order = api.create_ok(order_payload())

    assert api.delete(order["id"]).status_code == 204

    response = api.get(order["id"])
    assert response.status_code == 404
    schemas.assert_schema(response.json(), schemas.ERROR)
    assert order["id"] not in [o["id"] for o in api.list().json()["items"]]


@pytest.mark.parametrize("status", ["new", "in_progress", "done"])
def test_filter_orders_by_status(api: OrdersApi, status: str):
    api.create_ok(order_payload(status=status))

    response = api.list(status=status)

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 2  # one seeded + one created
    assert {order["status"] for order in items} == {status}
