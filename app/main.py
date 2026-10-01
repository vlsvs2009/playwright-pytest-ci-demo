"""Service Orders demo app: a small REST API plus a vanilla JS front end.

Run locally:  uvicorn app.main:app --reload
"""

import secrets
import threading
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Response, status
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles

from .config import Settings, get_settings
from .models import Credentials, Order, OrderCreate, OrderList, OrderUpdate, Status, Token
from .store import OrderStore

STATIC_DIR = Path(__file__).parent / "static"


class SessionStore:
    """Opaque bearer tokens kept in memory. Not reset by the test reset endpoint."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._tokens: dict[str, str] = {}

    def issue(self, username: str) -> str:
        token = secrets.token_urlsafe(32)
        with self._lock:
            self._tokens[token] = username
        return token

    def resolve(self, token: str) -> str | None:
        with self._lock:
            return self._tokens.get(token)

    def revoke(self, token: str) -> None:
        with self._lock:
            self._tokens.pop(token, None)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    store = OrderStore()
    sessions = SessionStore()
    bearer = HTTPBearer(auto_error=False)

    def current_token(
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    ) -> str:
        if credentials is None or sessions.resolve(credentials.credentials) is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return credentials.credentials

    app = FastAPI(title="Service Orders (demo)", version="1.0.0")
    api = APIRouter(prefix="/api")
    protected = APIRouter(prefix="/api", dependencies=[Depends(current_token)])

    @api.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok", "instance": settings.instance_id}

    @api.post("/auth/login", tags=["auth"])
    def login(credentials: Credentials) -> Token:
        valid_user = secrets.compare_digest(credentials.username, settings.demo_username)
        valid_password = secrets.compare_digest(credentials.password, settings.demo_password)
        if not (valid_user and valid_password):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
        return Token(access_token=sessions.issue(credentials.username))

    @protected.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT, tags=["auth"])
    def logout(token: Annotated[str, Depends(current_token)]) -> Response:
        sessions.revoke(token)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @protected.get("/orders", tags=["orders"])
    def list_orders(status_filter: Annotated[Status | None, Query(alias="status")] = None) -> OrderList:
        items = store.list(status_filter)
        return OrderList(items=items, count=len(items))

    @protected.post("/orders", status_code=status.HTTP_201_CREATED, tags=["orders"])
    def create_order(payload: OrderCreate) -> Order:
        return store.create(payload)

    @protected.get("/orders/{order_id}", tags=["orders"])
    def get_order(order_id: int) -> Order:
        return _found(store.get(order_id))

    @protected.patch("/orders/{order_id}", tags=["orders"])
    def update_order(order_id: int, payload: OrderUpdate) -> Order:
        return _found(store.update(order_id, payload))

    @protected.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["orders"])
    def delete_order(order_id: int) -> Response:
        if not store.delete(order_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Order not found")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    app.include_router(api)
    app.include_router(protected)

    if settings.enable_test_api:
        # Test-only hook: restores the deterministic seed data between tests.
        @app.post("/api/test/reset", status_code=status.HTTP_204_NO_CONTENT, tags=["test"])
        def reset() -> Response:
            store.reset()
            return Response(status_code=status.HTTP_204_NO_CONTENT)

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    return app


def _found(order: Order | None) -> Order:
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


app = create_app()
