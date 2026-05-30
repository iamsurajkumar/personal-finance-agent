import asyncio
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# FastMCP must be imported before the project root is added to sys.path.
# The local mcp/ directory would otherwise shadow the installed mcp package.
from mcp.server.fastmcp import FastMCP

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from services import DataService, PriceService
from tools.base import AgentContext
from tools.position import get_position as _get_position
from tools.portfolio import (
    get_portfolio_value as _get_portfolio_value,
    get_total_cost_basis as _get_total_cost_basis,
    get_total_gain_loss as _get_total_gain_loss,
    get_largest_position as _get_largest_position,
    list_all_holdings as _list_all_holdings,
)

ctx: AgentContext | None = None


@asynccontextmanager
async def lifespan(server: FastMCP):
    global ctx
    portfolio_service = DataService(Config.PORTFOLIO_CSV_PATH)
    price_service = PriceService()
    portfolio_service.load()
    ctx = AgentContext(portfolio=portfolio_service, prices=price_service)
    asyncio.create_task(price_service.fetch_prices(portfolio_service.get_symbols()))
    yield


mcp = FastMCP("finance-agent", lifespan=lifespan, host="0.0.0.0", port=8001, streamable_http_path="/mcp")


@mcp.tool()
async def get_position(symbol: str) -> str:
    """Get the current position for a specific stock symbol. Returns quantity, cost basis, current value, and gain/loss."""
    return await _get_position(symbol, ctx)


@mcp.tool()
async def get_portfolio_value() -> str:
    """Get the total current value of all holdings in the portfolio."""
    return await _get_portfolio_value(ctx)


@mcp.tool()
async def get_total_cost_basis() -> str:
    """Get the total amount invested across all holdings (sum of quantity * cost basis)."""
    return await _get_total_cost_basis(ctx)


@mcp.tool()
async def get_total_gain_loss() -> str:
    """Get the overall profit or loss (current value minus cost basis) with percentage."""
    return await _get_total_gain_loss(ctx)


@mcp.tool()
async def get_largest_position() -> str:
    """Get the largest holding by current value, including its percentage of the total portfolio."""
    return await _get_largest_position(ctx)


@mcp.tool()
async def list_all_holdings() -> str:
    """Get a summary list of all positions in the portfolio with quantities and values."""
    return await _list_all_holdings(ctx)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
