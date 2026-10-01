import httpx
import pytest

from tests.support import schemas
from tests.support.api_client import login
from tests.support.settings import DEMO_PASSWORD, DEMO_USERNAME

pytestmark = pytest.mark.api


@pytest.mark.smoke
def test_health_endpoint_is_public(http: httpx.Client):
    response = http.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.smoke
def test_login_returns_bearer_token(http: httpx.Client):
    response = http.post("/api/auth/login", json={"username": DEMO_USERNAME, "password": DEMO_PASSWORD})

    assert response.status_code == 200
    schemas.assert_schema(response.json(), schemas.TOKEN)


@pytest.mark.parametrize(
    "username, password",
    [
        pytest.param(DEMO_USERNAME, "wrong-password", id="wrong-password"),
        pytest.param("nobody@example.com", DEMO_PASSWORD, id="unknown-user"),
    ],
)
def test_login_rejects_invalid_credentials(http: httpx.Client, username: str, password: str):
    response = http.post("/api/auth/login", json={"username": username, "password": password})

    assert response.status_code == 401
    schemas.assert_schema(response.json(), schemas.ERROR)
    assert response.json()["detail"] == "Invalid username or password"


@pytest.mark.parametrize(
    "method, path, headers",
    [
        pytest.param("POST", "/api/orders", {}, id="create-without-token"),
        pytest.param("GET", "/api/orders", {"Authorization": "Bearer not-a-real-token"}, id="list-unknown-token"),
    ],
)
def test_orders_endpoints_require_valid_token(http: httpx.Client, method: str, path: str, headers: dict):
    response = http.request(method, path, headers=headers, json={} if method == "POST" else None)

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_logout_revokes_token(http: httpx.Client):
    # A dedicated token: revoking the shared session token would break other tests.
    token = login(http, DEMO_USERNAME, DEMO_PASSWORD)
    headers = {"Authorization": f"Bearer {token}"}
    assert http.get("/api/orders", headers=headers).status_code == 200

    assert http.post("/api/auth/logout", headers=headers).status_code == 204
    assert http.get("/api/orders", headers=headers).status_code == 401
