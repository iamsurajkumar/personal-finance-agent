import asyncio
import sys
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

# Add parent directory to path for local app imports after importing the MCP SDK.
# Importing the SDK first avoids shadowing it with this repo's local mcp/ folder.
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from services import DataService, PriceService, OrderService, NewsService
from tools.base import AgentContext
from tools import (
    get_position,
    get_portfolio_value,
    get_total_cost_basis,
    get_total_gain_loss,
    get_largest_position,
    list_all_holdings,
    buy,
    sell,
    check_order_status,
    get_portfolio_news,
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
        Tool(
            name="buy",
            description="Buy shares of a stock at the current market price. Updates the portfolio CSV immediately.",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock ticker symbol (e.g., AAPL, MSFT)",
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "Number of shares to buy",
                    },
                },
                "required": ["symbol", "quantity"],
            },
        ),
        Tool(
            name="sell",
            description="Sell shares of a stock at the current market price. Updates the portfolio CSV immediately. Removes the position if all shares are sold.",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock ticker symbol (e.g., AAPL, MSFT)",
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "Number of shares to sell",
                    },
                },
                "required": ["symbol", "quantity"],
            },
        ),
        Tool(
            name="check_order_status",
            description="Check the status of a specific order by ID, or list all recent orders if no ID is provided.",
            inputSchema={
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "Optional order ID to check. If omitted, lists all recent orders.",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="get_portfolio_news",
            description="Fetch recent news and sentiment for a specific ticker or all holdings. Provide a symbol to drill into one stock, or omit for portfolio-wide news.",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Optional stock ticker (e.g., AAPL). If omitted, fetches news for all portfolio holdings.",
                    },
                },
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
        elif name == "buy":
            symbol = arguments.get("symbol", "")
            quantity = arguments.get("quantity", 0)
            result = await buy(symbol, quantity, ctx)
        elif name == "sell":
            symbol = arguments.get("symbol", "")
            quantity = arguments.get("quantity", 0)
            result = await sell(symbol, quantity, ctx)
        elif name == "check_order_status":
            order_id = arguments.get("order_id") or None
            result = await check_order_status(order_id, ctx)
        elif name == "get_portfolio_news":
            symbol = arguments.get("symbol") or None
            result = await get_portfolio_news(symbol, ctx)
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
    order_service = OrderService(Config.ORDER_HISTORY_PATH)
    news_service = NewsService(Config.ALPHA_VANTAGE_API_KEY) if Config.ALPHA_VANTAGE_API_KEY else None

    # Load portfolio data
    portfolio_service.load()

    # Create context
    ctx = AgentContext(
        portfolio=portfolio_service,
        prices=price_service,
        orders=order_service,
        news=news_service,
    )

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
