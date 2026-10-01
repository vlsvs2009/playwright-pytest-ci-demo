from playwright.sync_api import Page, expect


class LoginPage:
    def __init__(self, page: Page):
        self.page = page
        self.heading = page.get_by_role("heading", name="Sign in")
        self.username = page.get_by_label("Username")
        self.password = page.get_by_label("Password")
        self.submit_button = page.get_by_role("button", name="Sign in")
        self.error = page.get_by_test_id("login-error")

    def open(self) -> "LoginPage":
        self.page.goto("/")
        self.expect_visible()
        return self

    def expect_visible(self) -> None:
        expect(self.heading).to_be_visible()

    def login(self, username: str, password: str) -> None:
        self.username.fill(username)
        self.password.fill(password)
        self.submit_button.click()
