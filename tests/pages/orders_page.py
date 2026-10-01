from playwright.sync_api import Locator, Page, expect


class OrdersPage:
    STATUS_LABELS = {"new": "New", "in_progress": "In progress", "done": "Done"}

    def __init__(self, page: Page):
        self.page = page
        self.heading = page.get_by_role("heading", name="Service Orders")
        self.current_user = page.get_by_test_id("current-user")
        self.sign_out_button = page.get_by_role("button", name="Sign out")

        # New order form
        self.customer_input = page.get_by_label("Customer")
        self.service_input = page.get_by_label("Service")
        self.price_input = page.get_by_label("Price")
        self.status_input = page.get_by_label("Status", exact=True)
        self.add_button = page.get_by_role("button", name="Add order")
        self.form_error = page.get_by_test_id("form-error")

        # List
        self.status_filter = page.get_by_label("Filter by status")
        self.table = page.get_by_role("table", name="Orders")
        self.rows = page.get_by_test_id("order-row")
        self.customer_cells = self.rows.get_by_test_id("order-customer")
        self.count = page.get_by_test_id("orders-count")
        self.empty_state = page.get_by_test_id("empty-state")

    # ---- navigation / state ----
    def open(self) -> "OrdersPage":
        self.page.goto("/")
        self.expect_loaded()
        return self

    def expect_loaded(self) -> None:
        expect(self.heading).to_be_visible()
        expect(self.table).to_have_attribute("aria-busy", "false")

    # ---- actions ----
    def create_order(self, customer: str, service: str, price: str | float, status: str = "new") -> None:
        self.customer_input.fill(customer)
        self.service_input.fill(service)
        self.price_input.fill(str(price))
        self.status_input.select_option(status)
        self.add_button.click()

    def filter_by(self, status: str | None) -> None:
        self.status_filter.select_option(status or "")

    def row(self, customer: str) -> Locator:
        return self.rows.filter(has=self.page.get_by_test_id("order-customer").get_by_text(customer, exact=True))

    def mark_done(self, customer: str) -> None:
        self.row(customer).get_by_role("button", name="Mark done").click()

    def delete(self, customer: str) -> None:
        self.row(customer).get_by_role("button", name="Delete").click()

    def sign_out(self) -> None:
        self.sign_out_button.click()

    # ---- queries ----
    def status_badge(self, customer: str) -> Locator:
        return self.row(customer).get_by_test_id("order-status")

    def order_id(self, customer: str) -> int:
        return int(self.row(customer).get_attribute("data-order-id"))
