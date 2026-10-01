"""Test data builders. Unique names keep assertions unambiguous."""

import uuid
from typing import Any

# Matches the seed data restored by POST /api/test/reset.
SEEDED_CUSTOMERS = ["Sam Lee", "Maria Lopez", "Alex Carter"]  # newest first


def unique(prefix: str) -> str:
    return f"{prefix} {uuid.uuid4().hex[:6]}"


def order_payload(**overrides: Any) -> dict[str, Any]:
    payload = {
        "customer": unique("Customer"),
        "service": "Wheel alignment",
        "price": 89.5,
        "status": "new",
    }
    payload.update(overrides)
    return payload
