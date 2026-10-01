"""Thread-safe in-memory storage. Data lives only as long as the process."""

import threading
from datetime import UTC, datetime

from .models import Order, OrderCreate, OrderUpdate, Status

SEED_ORDERS = (
    OrderCreate(customer="Alex Carter", service="Brake pad replacement", price=120.0, status=Status.new),
    OrderCreate(customer="Maria Lopez", service="Oil change", price=45.0, status=Status.done),
    OrderCreate(customer="Sam Lee", service="Interior detailing", price=150.0, status=Status.in_progress),
)


class OrderStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._orders: dict[int, Order] = {}
        self._next_id = 1
        self.reset()

    def reset(self) -> None:
        """Drop all data and restore the deterministic seed set."""
        with self._lock:
            self._orders = {}
            self._next_id = 1
        for seed in SEED_ORDERS:
            self.create(seed)

    def list(self, status: Status | None = None) -> list[Order]:
        with self._lock:
            orders = sorted(self._orders.values(), key=lambda o: o.id, reverse=True)
        return [o for o in orders if status is None or o.status == status]

    def get(self, order_id: int) -> Order | None:
        with self._lock:
            return self._orders.get(order_id)

    def create(self, data: OrderCreate) -> Order:
        with self._lock:
            order = Order(
                id=self._next_id,
                created_at=datetime.now(UTC),
                **data.model_dump(),
            )
            self._orders[order.id] = order
            self._next_id += 1
            return order

    def update(self, order_id: int, patch: OrderUpdate) -> Order | None:
        with self._lock:
            current = self._orders.get(order_id)
            if current is None:
                return None
            updated = current.model_copy(update=patch.model_dump(exclude_unset=True, exclude_none=True))
            self._orders[order_id] = updated
            return updated

    def delete(self, order_id: int) -> bool:
        with self._lock:
            return self._orders.pop(order_id, None) is not None
