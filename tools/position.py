from .base import AgentContext, format_currency


async def get_position(symbol: str, ctx: AgentContext) -> str:
    """
    Get the current position for a specific stock symbol.

    Args:
        symbol: Stock ticker symbol (e.g., AAPL, MSFT)
        ctx: Agent context with portfolio and price services

    Returns:
        Human-readable position details or error message
    """
    # Check if prices are ready
    if not ctx.prices.is_ready():
        await ctx.prices.wait_until_ready()

    # Look up the holding
    holding = ctx.portfolio.get_holding(symbol)
    if holding is None:
        return f"No position found for {symbol.upper()}"

    symbol = holding["symbol"]
    quantity = holding["quantity"]
    cost_basis = holding["cost_basis"]
    purchase_date = holding["purchase_date"].strftime("%Y-%m-%d")

    # Calculate values
    total_cost = quantity * cost_basis

    # Get current price
    current_price = ctx.prices.get_price(symbol)
    if current_price is None:
        return (
            f"{symbol}: {quantity} shares @ {format_currency(cost_basis)} cost basis\n"
            f"Total invested: {format_currency(total_cost)}\n"
            f"Purchased: {purchase_date}\n"
            f"Current price: unavailable"
        )

    current_value = quantity * current_price
    gain_loss = current_value - total_cost
    gain_loss_pct = (gain_loss / total_cost) * 100 if total_cost > 0 else 0
    sign = "+" if gain_loss >= 0 else "-"

    return (
        f"{symbol}: {quantity} shares @ {format_currency(cost_basis)} cost basis\n"
        f"Current price: {format_currency(current_price)}\n"
        f"Current value: {format_currency(current_value)}\n"
        f"Gain/Loss: {sign}{format_currency(abs(gain_loss))} ({sign}{abs(gain_loss_pct):.2f}%)\n"
        f"Purchased: {purchase_date}"
    )
