from dataclasses import dataclass, field
from services.data import DataService
from services.prices import PriceService
from services.order import OrderService
from services.news import NewsService


@dataclass
class AgentContext:
    """Central context object holding shared dependencies for all tools."""

    portfolio: DataService
    prices: PriceService
    orders: OrderService = field(default_factory=OrderService)
    news: NewsService | None = None

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
