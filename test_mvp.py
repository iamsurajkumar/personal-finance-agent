"""Direct test of all 6 MVP tools without the MCP layer."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from services import DataService, PriceService
from tools.base import AgentContext
from tools import (
    get_position,
    get_portfolio_value,
    get_total_cost_basis,
    get_total_gain_loss,
    get_largest_position,
    list_all_holdings,
)

SEPARATOR = "-" * 50


async def main():
    print("Initializing services...")
    portfolio = DataService("./sample_portfolio.csv")
    portfolio.load()

    prices = PriceService()
    ctx = AgentContext(portfolio=portfolio, prices=prices)

    # Yahoo Finance is blocked in this sandbox environment (HTTP 403).
    # Inject realistic mock prices to verify all calculation logic.
    mock_prices = {
        "AAPL": 213.50,
        "MSFT": 415.25,
        "GOOGL": 178.90,
        "NVDA": 1105.00,
        "AMZN": 195.75,
    }
    prices._prices = mock_prices
    prices._ready.set()

    print(f"Mock prices injected: {mock_prices}\n")

    tests = [
        ("list_all_holdings", list_all_holdings(ctx)),
        ("get_portfolio_value", get_portfolio_value(ctx)),
        ("get_total_cost_basis", get_total_cost_basis(ctx)),
        ("get_total_gain_loss", get_total_gain_loss(ctx)),
        ("get_largest_position", get_largest_position(ctx)),
        ("get_position(AAPL)", get_position("AAPL", ctx)),
        ("get_position(NVDA)", get_position("NVDA", ctx)),
        ("get_position(TSLA) [not in portfolio]", get_position("TSLA", ctx)),
    ]

    for label, coro in tests:
        print(SEPARATOR)
        print(f"Tool: {label}")
        result = await coro
        print(result)

    print(SEPARATOR)
    print("All tools tested.")


if __name__ == "__main__":
    asyncio.run(main())
