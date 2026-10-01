"""Shared fixtures and reporting hooks.

Isolation model
---------------
* Every pytest-xdist worker starts its own app server (session-scoped fixture,
  free port), so parallel workers never touch each other's data.
* Inside a worker tests run sequentially, and an autouse fixture restores the
  deterministic seed data before each test.
* UI tests reuse a storage state captured by one real UI login per worker.
"""

from __future__ import annotations

import base64
import shutil
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest
from playwright.sync_api import Browser, Page

from tests.pages import LoginPage, OrdersPage
from tests.support.api_client import OrdersApi, login
from tests.support.server import AppServer
from tests.support.settings import (
    DEMO_PASSWORD,
    DEMO_USERNAME,
    REPORTS_DIR,
    ROOT_DIR,
    SERVER_STARTUP_TIMEOUT_S,
)

# --------------------------------------------------------------------------- #
# App server & HTTP clients
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="session")
def app_server(worker_id: str) -> Iterator[AppServer]:
    """One isolated server per xdist worker ("master" when running without -n)."""
    server = AppServer(
        app_dir=ROOT_DIR,
        log_file=REPORTS_DIR / "logs" / f"server-{worker_id}.log",
        env={
            "APP_ENABLE_TEST_API": "1",
            "APP_DEMO_USERNAME": DEMO_USERNAME,
            "APP_DEMO_PASSWORD": DEMO_PASSWORD,
        },
        startup_timeout=SERVER_STARTUP_TIMEOUT_S,
    ).start()
    yield server
    server.stop()


@pytest.fixture(scope="session")
def base_url(app_server: AppServer) -> str:
    """Overrides pytest-base-url, so Playwright resolves page.goto("/") against our server."""
    return app_server.url


@pytest.fixture(scope="session")
def http(base_url: str) -> Iterator[httpx.Client]:
    """Anonymous HTTP client (no auth header)."""
    with httpx.Client(base_url=base_url, timeout=10) as client:
        yield client


@pytest.fixture(scope="session")
def auth_token(http: httpx.Client) -> str:
    return login(http, DEMO_USERNAME, DEMO_PASSWORD)


@pytest.fixture(scope="session")
def api(base_url: str, auth_token: str) -> Iterator[OrdersApi]:
    """Authenticated API client, also used to arrange data for UI tests."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    with httpx.Client(base_url=base_url, headers=headers, timeout=10) as client:
        yield OrdersApi(client)


@pytest.fixture(autouse=True)
def reset_data(http: httpx.Client) -> None:
    """Restore the seed data before every test (sessions/tokens are kept)."""
    http.post("/api/test/reset").raise_for_status()


# --------------------------------------------------------------------------- #
# Browser fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="session")
def auth_state(browser: Browser, base_url: str, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Log in through the real UI once per worker and save the storage state."""
    context = browser.new_context(base_url=base_url)
    page = context.new_page()
    LoginPage(page).open().login(DEMO_USERNAME, DEMO_PASSWORD)
    OrdersPage(page).expect_loaded()
    path = tmp_path_factory.mktemp("auth") / "storage-state.json"
    context.storage_state(path=path)
    context.close()
    return path


@pytest.fixture
def authed_page(new_context, auth_state: Path) -> Page:
    """A fresh, already signed-in page. Created via pytest-playwright's
    `new_context`, so tracing/screenshots-on-failure still apply."""
    context = new_context(storage_state=auth_state)
    return context.new_page()


@pytest.fixture
def orders_page(authed_page: Page) -> OrdersPage:
    return OrdersPage(authed_page).open()


@pytest.fixture
def login_page(page: Page) -> LoginPage:
    return LoginPage(page).open()


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="session", autouse=True)
def delete_output_dir() -> None:
    """Overrides pytest-playwright's per-worker cleanup, which could race between
    workers and delete a neighbour's failure artifacts. Cleanup happens once in
    the controller process instead (see pytest_configure)."""


def pytest_configure(config: pytest.Config) -> None:
    is_xdist_worker = hasattr(config, "workerinput")
    if not is_xdist_worker:
        shutil.rmtree(Path(config.getoption("--output")), ignore_errors=True)
        shutil.rmtree(REPORTS_DIR / "logs", ignore_errors=True)


REPORT_MARKERS = ("api", "ui", "smoke")


def pytest_html_report_title(report) -> None:
    report.title = "Service Orders — automated test run"


def pytest_html_results_table_header(cells: list) -> None:
    cells.insert(2, '<th class="sortable" data-column-type="markers">Markers</th>')


def pytest_html_results_table_row(report, cells: list) -> None:
    markers = " ".join(m for m in REPORT_MARKERS if m in report.keywords)
    cells.insert(2, f'<td class="col-markers">{markers}</td>')


@pytest.hookimpl(tryfirst=True)
def pytest_sessionfinish(session: pytest.Session) -> None:
    """Keep the report's environment table short. Runs in the controller after
    worker metadata has been merged and before pytest-html renders the report."""
    config = session.config
    if hasattr(config, "workerinput"):
        return
    try:
        from pytest_metadata.plugin import metadata_key
    except ImportError:
        return
    metadata = config.stash.get(metadata_key, {})
    for key in ("Plugins", "Packages", "Base URL", "JAVA_HOME"):
        metadata.pop(key, None)
    metadata["Browser"] = ", ".join(config.getoption("--browser") or ["chromium"])
    metadata["Parallel workers"] = str(getattr(config.option, "numprocesses", None) or 1)


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):
    """On UI test failure, embed a screenshot and the trace path into the HTML report."""
    report = yield
    page = item.funcargs.get("authed_page") or item.funcargs.get("page")
    if report.when != "call" or not report.failed or not isinstance(page, Page):
        return report

    from pytest_html import extras  # imported lazily: the plugin may be disabled

    report_extras = getattr(report, "extras", [])
    try:
        png = page.screenshot(full_page=True, timeout=5000)
        report_extras.append(extras.png(base64.b64encode(png).decode(), name="Screenshot at failure"))
    except Exception as exc:  # never let reporting hide the real failure
        report_extras.append(extras.text(f"Could not capture screenshot: {exc}", name="Screenshot"))
    output_path = item.funcargs.get("output_path")
    if output_path:
        trace = Path(output_path) / "trace.zip"
        if trace.is_relative_to(ROOT_DIR):
            trace = trace.relative_to(ROOT_DIR)
        report_extras.append(
            extras.text(f"python -m playwright show-trace {trace.as_posix()}", name="Playwright trace")
        )
    report.extras = report_extras
    return report
