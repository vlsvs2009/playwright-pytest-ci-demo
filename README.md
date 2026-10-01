# playwright-pytest-ci-demo

[![tests](https://github.com/vlsvs2009/playwright-pytest-ci-demo/actions/workflows/tests.yml/badge.svg)](https://github.com/vlsvs2009/playwright-pytest-ci-demo/actions/workflows/tests.yml)

A compact, production-style test automation project in Python: API and end-to-end UI tests for a small web app, running in parallel locally and in GitHub Actions, with one consolidated HTML report.

The repository ships its own system under test (a tiny "Service Orders" app), so the suite runs anywhere without depending on third-party demo sites.

## What it demonstrates

- **API tests** (pytest + httpx): CRUD, authentication (401), validation errors (422), not found (404), parametrized negative cases, JSON Schema contract checks with `jsonschema`.
- **UI end-to-end tests** (Playwright + pytest-playwright): Page Object pattern, role / label / `data-testid` locators, web-first assertions, no sleeps.
- **Fixtures**: app server started per worker on a free port, per-test data reset, authenticated API client, browser storage state reused across UI tests.
- **Parallel execution** with pytest-xdist (`-n auto`) and full per-worker isolation.
- **Reporting**: a single self-contained `reports/report.html` for the whole parallel run; Playwright trace and screenshot kept for failed tests only (the screenshot is also embedded in the report).
- **CI**: GitHub Actions on every push and pull request, report uploaded as a build artifact.

**Stack:** Python 3.12 · pytest · Playwright · pytest-xdist · pytest-html · httpx · jsonschema · FastAPI · GitHub Actions

## Project structure

```text
.
├── .github/workflows/tests.yml   # CI: install, run in parallel, upload report
├── app/                          # System under test
│   ├── main.py                   # REST API, bearer auth, test-only reset hook
│   ├── models.py                 # Pydantic models and validation rules
│   ├── store.py                  # Thread-safe in-memory store + seed data
│   ├── config.py                 # Settings from env (fake demo credentials)
│   └── static/                   # index.html, app.js, styles.css (with data-testid hooks)
├── tests/
│   ├── conftest.py               # Server per worker, clients, data reset, auth state, report hooks
│   ├── api/                      # API specs (auth, CRUD, validation)
│   ├── ui/                       # Playwright E2E specs (login, orders)
│   ├── pages/                    # Page Objects: LoginPage, OrdersPage
│   └── support/                  # Server launcher, API client, JSON schemas, data builders
├── pyproject.toml                # pytest config: markers, report, Playwright artifacts
├── requirements.txt              # Pinned dependencies
├── Makefile                      # Shortcuts: make test / test-api / test-ui / smoke / serve
└── LICENSE
```

## Run locally

Requires Python 3.11+.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && python -m playwright install chromium
pytest -n auto
```

Then open `reports/report.html`. The tests start the app themselves, so there is no server to run first.

| Command | Runs |
| --- | --- |
| `pytest -m api` | API tests only |
| `pytest -m ui` | UI tests only |
| `pytest -m smoke` | Critical-path subset |
| `pytest -m ui --headed --slowmo 300` | UI tests in a visible browser |
| `pytest --browser firefox` | Same suite in Firefox (after `python -m playwright install firefox`) |
| `make serve` | The demo app at http://127.0.0.1:8000 (login `demo@example.com` / `demo-password`, fake credentials) |

## How CI works

`.github/workflows/tests.yml` runs on pushes to `main`, on pull requests, and on demand:

1. Sets up Python 3.12 with pip caching and installs the pinned requirements.
2. Installs Chromium and its system dependencies (`python -m playwright install --with-deps chromium`); browser binaries are cached.
3. Runs `pytest -n auto`: API and UI tests together, spread across all runner cores.
4. Uploads `reports/` (HTML report, failure traces and screenshots, server logs) as the `test-report` artifact, always, including when tests fail.

## Design decisions

- **Page Objects** (`tests/pages/`). Specs read like user scenarios; locators and UI mechanics live in one place, so a UI change is a one-file fix.
- **Resilient locators.** Role and label locators first (they double as a basic accessibility check), `data-testid` for elements without a semantic role (rows, badges, counters). No CSS or XPath tied to layout.
- **No sleeps.** Playwright's web-first `expect(...)` assertions retry until the UI settles; the app marks the table `aria-busy` while loading and ignores stale list responses.
- **Isolated test data.** A test-only `POST /api/test/reset` endpoint (mounted only when `APP_ENABLE_TEST_API=1`) restores deterministic seed data before every test; generated records get unique names.
- **Parallel workers with no shared state.** Each xdist worker starts its own app server on a free port and confirms, via an instance id, that it reached its own process. `-n auto` is safe by construction, not by luck.
- **One consolidated report.** pytest-html merges results from all workers into one self-contained file, with a Markers column (api / ui / smoke).
- **Failure artifacts only.** `--tracing=retain-on-failure` and `--screenshot=only-on-failure` keep artifacts small; a failing UI test gets its screenshot and the `playwright show-trace` command attached in the report.
- **API tests as the fast safety net.** Validation, auth, and contract rules are covered at API level in milliseconds. UI tests focus on user journeys and use the API to arrange data when the UI itself is not under test.
- **Log in once per worker.** UI tests reuse a storage state captured from one real UI login per worker; the login flow itself still has dedicated specs.

## Test inventory

30 tests: 20 API, 10 UI (6 tagged `smoke`).

| Layer | File | Covers |
| --- | --- | --- |
| API | `tests/api/test_auth_api.py` | Health, login, invalid credentials, missing / unknown token, logout |
| API | `tests/api/test_orders_api.py` | Create, read, update, delete, input normalization, status filter |
| API | `tests/api/test_orders_validation_api.py` | 422 responses for invalid payloads (parametrized) |
| UI | `tests/ui/test_login_ui.py` | Login, wrong password, sign out |
| UI | `tests/ui/test_orders_ui.py` | Create, validation messages, filter, mark done, delete, persistence after reload, API-arranged data |

## About

Maintained by Vladimir Siur — QA Automation Lead / SDET. LinkedIn: [linkedin.com/in/vladimir-siur](https://www.linkedin.com/in/vladimir-siur)

Licensed under the [MIT License](LICENSE).
