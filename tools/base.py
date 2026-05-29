from dataclasses import dataclass
from services.data import DataService
from services.prices import PriceService


@dataclass
class AgentContext:
    """Central context object holding shared dependencies for all tools."""

    portfolio: DataService
    prices: PriceService

    async def ensure_prices_ready(self) -> str | None:
        """
        Ensure prices are loaded. Returns a message if still loading,
        None if ready.
        """
        if not self.prices.is_ready():
            return "Prices are still loading, please wait..."
        return None


def format_currency(value: float) -> str:
    """Format a number as currency."""
    return f"${value:,.2f}"


def format_percentage(value: float) -> str:
    """Format a number as percentage."""
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.2f}%"
