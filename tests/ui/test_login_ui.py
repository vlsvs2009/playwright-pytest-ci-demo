import pytest
from playwright.sync_api import expect

from tests.pages import LoginPage, OrdersPage
from tests.support.settings import DEMO_PASSWORD, DEMO_USERNAME

pytestmark = pytest.mark.ui


@pytest.mark.smoke
def test_login_with_valid_credentials_opens_orders(login_page: LoginPage):
    login_page.login(DEMO_USERNAME, DEMO_PASSWORD)

    orders = OrdersPage(login_page.page)
    orders.expect_loaded()
    expect(orders.current_user).to_have_text(DEMO_USERNAME)
    expect(orders.rows).to_have_count(3)


def test_login_with_wrong_password_shows_error(login_page: LoginPage):
    login_page.login(DEMO_USERNAME, "wrong-password")

    expect(login_page.error).to_have_text("Invalid username or password.")
    expect(login_page.heading).to_be_visible()


def test_sign_out_returns_to_login(login_page: LoginPage):
    # Fresh login: signing out revokes the token, so the shared storage state is not used here.
    login_page.login(DEMO_USERNAME, DEMO_PASSWORD)
    orders = OrdersPage(login_page.page)
    orders.expect_loaded()

    orders.sign_out()

    login_page.expect_visible()
    login_page.page.reload()
    login_page.expect_visible()
