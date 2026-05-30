"""Order tracker with JSON persistence — mock for when Alpaca isn't reachable."""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional


class OrderService:
    """Tracks orders, persists to a JSON file across restarts."""

    def __init__(self, history_path: str | Path = "order_history.json"):
        self._path = Path(history_path)
        self._orders: dict[str, dict] = {}
        self._load()

    # ── CRUD ───────────────────────────────────────────────────────

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
        self._save()
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

    # ── Persistence ─────────────────────────────────────────────────

    def _load(self) -> None:
        """Load order history from disk."""
        if self._path.exists():
            try:
                loaded = json.loads(self._path.read_text())
                if isinstance(loaded, dict):
                    self._orders = loaded
            except (json.JSONDecodeError, OSError):
                self._orders = {}

    def _save(self) -> None:
        """Write order history to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._orders, indent=2))
