"""Thin wrapper over the REST API. Returns raw httpx responses so tests own the assertions."""

from typing import Any

import httpx


def login(client: httpx.Client, username: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    response.raise_for_status()
    return response.json()["access_token"]


class OrdersApi:
    def __init__(self, client: httpx.Client):
        self.client = client

    def list(self, status: str | None = None) -> httpx.Response:
        params = {"status": status} if status else None
        return self.client.get("/api/orders", params=params)

    def create(self, payload: dict[str, Any]) -> httpx.Response:
        return self.client.post("/api/orders", json=payload)

    def get(self, order_id: int) -> httpx.Response:
        return self.client.get(f"/api/orders/{order_id}")

    def update(self, order_id: int, payload: dict[str, Any]) -> httpx.Response:
        return self.client.patch(f"/api/orders/{order_id}", json=payload)

    def delete(self, order_id: int) -> httpx.Response:
        return self.client.delete(f"/api/orders/{order_id}")

    # Convenience for arranging test data (fails fast if setup itself breaks).
    def create_ok(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self.create(payload)
        assert response.status_code == 201, response.text
        return response.json()
