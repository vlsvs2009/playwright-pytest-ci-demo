import pytest
from playwright.sync_api import expect

from tests.pages import OrdersPage
from tests.support.api_client import OrdersApi
from tests.support.data import SEEDED_CUSTOMERS, order_payload, unique

pytestmark = pytest.mark.ui


@pytest.mark.smoke
def test_create_order(orders_page: OrdersPage):
    customer = unique("Customer")

    orders_page.create_order(customer, "Full detailing", "249.90", status="in_progress")

    row = orders_page.row(customer)
    expect(row).to_be_visible()
    expect(row.get_by_test_id("order-service")).to_have_text("Full detailing")
    expect(row.get_by_test_id("order-price")).to_have_text("$249.90")
    expect(orders_page.status_badge(customer)).to_have_text("In progress")
    expect(orders_page.count).to_have_text("4 orders")
    expect(orders_page.customer_input).to_be_empty()


def test_create_order_shows_validation_messages(orders_page: OrdersPage):
    orders_page.create_order(customer=" ", service="Oil change", price="0")

    expect(orders_page.form_error).to_contain_text("Customer name must be at least 2 characters.")
    expect(orders_page.form_error).to_contain_text("Price must be greater than 0.")
    expect(orders_page.customer_input).to_have_attribute("aria-invalid", "true")
    expect(orders_page.price_input).to_have_attribute("aria-invalid", "true")
    expect(orders_page.rows).to_have_count(3)


def test_filter_orders_by_status(orders_page: OrdersPage):
    orders_page.filter_by("done")
    expect(orders_page.customer_cells).to_have_text(["Maria Lopez"])

    orders_page.filter_by("in_progress")
    expect(orders_page.customer_cells).to_have_text(["Sam Lee"])

    orders_page.filter_by(None)
    expect(orders_page.customer_cells).to_have_text(SEEDED_CUSTOMERS)


def test_mark_order_done(orders_page: OrdersPage, api: OrdersApi):
    orders_page.mark_done("Alex Carter")

    expect(orders_page.status_badge("Alex Carter")).to_have_text("Done")
    expect(orders_page.row("Alex Carter").get_by_role("button", name="Mark done")).to_have_count(0)
    # Cross-check the backend state, not just the UI.
    order_id = orders_page.order_id("Alex Carter")
    assert api.get(order_id).json()["status"] == "done"


def test_delete_order(orders_page: OrdersPage):
    orders_page.delete("Sam Lee")

    expect(orders_page.row("Sam Lee")).to_have_count(0)
    expect(orders_page.count).to_have_text("2 orders")


def test_created_order_persists_after_reload(orders_page: OrdersPage):
    customer = unique("Customer")
    orders_page.create_order(customer, "Tyre change", 60)
    expect(orders_page.row(customer)).to_be_visible()

    orders_page.page.reload()

    orders_page.expect_loaded()
    expect(orders_page.row(customer)).to_be_visible()
    expect(orders_page.count).to_have_text("4 orders")


def test_order_created_via_api_is_visible_in_ui(api: OrdersApi, authed_page):
    # Arrange through the API (fast), assert through the UI.
    order = api.create_ok(order_payload(service="Engine diagnostics", status="done"))

    orders_page = OrdersPage(authed_page).open()

    expect(orders_page.row(order["customer"]).get_by_test_id("order-service")).to_have_text("Engine diagnostics")
    expect(orders_page.status_badge(order["customer"])).to_have_text("Done")
