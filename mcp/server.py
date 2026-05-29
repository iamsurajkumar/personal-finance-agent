import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from config import Config
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


# Create the MCP server
server = Server("finance-agent")

# Global context - initialized on startup
ctx: AgentContext | None = None


@server.list_tools()
async def list_tools() -> list[Tool]:
    """Return list of available tools."""
    return [
        Tool(
            name="get_position",
            description="Get the current position for a specific stock symbol. Returns quantity, cost basis, current value, and gain/loss.",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock ticker symbol (e.g., AAPL, MSFT, GOOGL)",
                    }
                },
                "required": ["symbol"],
            },
        ),
        Tool(
            name="get_portfolio_value",
            description="Get the total current value of all holdings in the portfolio.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="get_total_cost_basis",
            description="Get the total amount invested across all holdings (sum of quantity * cost basis).",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="get_total_gain_loss",
            description="Get the overall profit or loss (current value minus cost basis) with percentage.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="get_largest_position",
            description="Get the largest holding by current value, including its percentage of the total portfolio.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="list_all_holdings",
            description="Get a summary list of all positions in the portfolio with quantities and values.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    global ctx

    if ctx is None:
        return [TextContent(type="text", text="Error: Server not initialized")]

    try:
        if name == "get_position":
            symbol = arguments.get("symbol", "")
            result = await get_position(symbol, ctx)
        elif name == "get_portfolio_value":
            result = await get_portfolio_value(ctx)
        elif name == "get_total_cost_basis":
            result = await get_total_cost_basis(ctx)
        elif name == "get_total_gain_loss":
            result = await get_total_gain_loss(ctx)
        elif name == "get_largest_position":
            result = await get_largest_position(ctx)
        elif name == "list_all_holdings":
            result = await list_all_holdings(ctx)
        else:
            result = f"Unknown tool: {name}. Support is coming."

        return [TextContent(type="text", text=result)]

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def initialize() -> None:
    """Initialize services and context."""
    global ctx

    # Initialize services
    portfolio_service = DataService(Config.PORTFOLIO_CSV_PATH)
    price_service = PriceService()

    # Load portfolio data
    portfolio_service.load()

    # Create context
    ctx = AgentContext(portfolio=portfolio_service, prices=price_service)

    # Start async price fetching
    symbols = portfolio_service.get_symbols()
    asyncio.create_task(price_service.fetch_prices(symbols))


async def main() -> None:
    """Main entry point."""
    # Initialize services
    await initialize()

    # Run the server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
