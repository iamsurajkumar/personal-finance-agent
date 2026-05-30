"""Trade execution tools: buy, sell, check_order_status."""

from .base import AgentContext, format_currency


async def buy(symbol: str, quantity: int, ctx: AgentContext) -> str:
    """Buy shares of a stock at current market price.

    Updates the CSV immediately.  Order is recorded in-memory
    (Alpaca integration pending).
    """
    if quantity <= 0:
        return "Error: quantity must be positive"

    # Use current price as fill price (mock — Alpaca would give real fill)
    if not ctx.prices.is_ready():
        await ctx.prices.wait_until_ready()

    fill_price = ctx.prices.get_price(symbol)
    if fill_price is None:
        return f"Error: no current price available for {symbol.upper()}"

    try:
        updated = ctx.portfolio.buy(symbol, quantity, fill_price)
    except Exception as e:
        return f"Error executing buy: {e}"

    order_id = ctx.orders.create(symbol, "buy", quantity, fill_price)
    total = quantity * fill_price

    return (
        f"✅ Bought {quantity} share(s) of {symbol.upper()} "
        f"at {format_currency(fill_price)}\n"
        f"Total: {format_currency(total)}\n"
        f"Order ID: {order_id}\n"
        f"New position: {updated['quantity']} shares "
        f"@ {format_currency(updated['cost_basis'])} avg cost"
    )


async def sell(symbol: str, quantity: int, ctx: AgentContext) -> str:
    """Sell shares of a stock at current market price.

    Updates the CSV immediately.  Removes the row if quantity hits zero.
    """
    if quantity <= 0:
        return "Error: quantity must be positive"

    if not ctx.prices.is_ready():
        await ctx.prices.wait_until_ready()

    fill_price = ctx.prices.get_price(symbol)
    if fill_price is None:
        return f"Error: no current price available for {symbol.upper()}"

    try:
        result = ctx.portfolio.sell(symbol, quantity, fill_price)
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error executing sell: {e}"

    order_id = ctx.orders.create(symbol, "sell", quantity, fill_price)
    total = quantity * fill_price

    if result.get("removed"):
        return (
            f"✅ Sold all {quantity} share(s) of {symbol.upper()} "
            f"at {format_currency(fill_price)}\n"
            f"Total proceeds: {format_currency(total)}\n"
            f"Order ID: {order_id}\n"
            f"Position closed — removed from portfolio."
        )

    return (
        f"✅ Sold {quantity} share(s) of {symbol.upper()} "
        f"at {format_currency(fill_price)}\n"
        f"Total proceeds: {format_currency(total)}\n"
        f"Order ID: {order_id}\n"
        f"Remaining: {result['quantity']} shares "
        f"@ {format_currency(result['cost_basis'])} avg cost"
    )


async def check_order_status(order_id: str | None, ctx: AgentContext) -> str:
    """Check the status of an order by ID, or list recent orders."""
    if order_id:
        order = ctx.orders.get(order_id)
        if order is None:
            return f"No order found with ID: {order_id}"
        return (
            f"Order {order['id']}: {order['side'].upper()} "
            f"{order['quantity']} {order['symbol']} "
            f"@ {format_currency(order['fill_price'])} — "
            f"{order['status']} ({order['filled_at']})"
        )

    all_orders = ctx.orders.list_all()
    if not all_orders:
        return "No orders placed this session."

    lines = ["Recent orders:"]
    for o in all_orders[:10]:
        lines.append(
            f"  {o['id']}: {o['side'].upper()} {o['quantity']} {o['symbol']} "
            f"@ {format_currency(o['fill_price'])} — {o['status']}"
        )
    return "\n".join(lines)
