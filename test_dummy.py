"""
Test all 6 tools using dummy portfolio + dummy prices.
Covers: normal positions, a loss position (TSLA), a missing price (FAKE),
and a symbol not in the portfolio at all (NVDA).
"""
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

SEPARATOR = "=" * 55

# Dummy prices — FAKE intentionally omitted to test missing-price path.
# TSLA is below cost basis ($800) to test a loss scenario.
DUMMY_PRICES = {
    "AAPL": 210.00,   # gain:  +$60/share
    "TSLA": 190.00,   # loss:  -$610/share
    "MSFT": 420.00,   # gain:  +$120/share
    "GOOGL": 175.00,  # gain:  +$85/share
    # FAKE: no price → triggers "unavailable" branch
}


def section(title: str):
    print(f"\n{SEPARATOR}")
    print(f"  {title}")
    print(SEPARATOR)


async def run_tool(label: str, coro):
    result = await coro
    print(f"\n[{label}]\n{result}")


async def main():
    section("Setup")
    portfolio = DataService("./dummy_portfolio.csv")
    portfolio.load()
    print("Portfolio loaded:")
    print(portfolio.get_all_holdings().to_string(index=False))

    prices = PriceService()
    prices._prices = DUMMY_PRICES.copy()
    prices._ready.set()
    print(f"\nDummy prices: {DUMMY_PRICES}")
    print("(FAKE has no price — intentional, tests missing-price branch)")

    ctx = AgentContext(portfolio=portfolio, prices=prices)

    section("Portfolio-level tools")
    await run_tool("list_all_holdings", list_all_holdings(ctx))
    await run_tool("get_portfolio_value", get_portfolio_value(ctx))
    await run_tool("get_total_cost_basis", get_total_cost_basis(ctx))
    await run_tool("get_total_gain_loss", get_total_gain_loss(ctx))
    await run_tool("get_largest_position", get_largest_position(ctx))

    section("get_position — individual stocks")
    for symbol in ["AAPL", "TSLA", "MSFT", "GOOGL", "FAKE"]:
        await run_tool(f"get_position({symbol})", get_position(symbol, ctx))

    section("Edge cases")
    await run_tool(
        "get_position(NVDA) — not in portfolio",
        get_position("NVDA", ctx),
    )
    await run_tool(
        "get_position(aapl) — lowercase input",
        get_position("aapl", ctx),
    )

    section("Done")
    print("All tools exercised successfully.\n")


if __name__ == "__main__":
    asyncio.run(main())
