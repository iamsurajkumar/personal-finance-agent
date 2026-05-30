"""In-memory order tracker — mock for when Alpaca isn't reachable."""

import uuid
from datetime import datetime
from typing import Optional


class OrderService:
    """Tracks orders in memory. Replaced by Alpaca API in production."""

    def __init__(self):
        self._orders: dict[str, dict] = {}

    def create(self, symbol: str, side: str, quantity: int, price: float) -> str:
        """Record a filled order, return its id."""
        order_id = str(uuid.uuid4())[:8]
        self._orders[order_id] = {
            "id": order_id,
            "symbol": symbol.upper(),
            "side": side,
            "quantity": quantity,
            "fill_price": price,
            "status": "filled",
            "filled_at": datetime.now().isoformat(),
        }
        return order_id

    def get(self, order_id: str) -> Optional[dict]:
        """Look up an order by id."""
        return self._orders.get(order_id)

    def list_all(self) -> list[dict]:
        """Return all orders, most recent first."""
        return sorted(
            self._orders.values(),
            key=lambda o: o.get("filled_at", ""),
            reverse=True,
        )
