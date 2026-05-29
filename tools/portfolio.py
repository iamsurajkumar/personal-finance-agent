from .base import AgentContext, format_currency, format_percentage


async def get_portfolio_value(ctx: AgentContext) -> str:
    """
    Get the total current value of all holdings.

    Returns:
        Human-readable total portfolio value
    """
    if not ctx.prices.is_ready():
        await ctx.prices.wait_until_ready()

    df = ctx.portfolio.get_all_holdings()
    total_value = 0.0
    missing_prices = []

    for _, row in df.iterrows():
        symbol = row["symbol"]
        quantity = row["quantity"]
        price = ctx.prices.get_price(symbol)

        if price is not None:
            total_value += quantity * price
        else:
            missing_prices.append(symbol)

    result = f"Total portfolio value: {format_currency(total_value)}"

    if missing_prices:
        result += f"\n(Excludes {', '.join(missing_prices)} - prices unavailable)"

    return result


async def get_total_cost_basis(ctx: AgentContext) -> str:
    """
    Get the total amount invested across all holdings.

    Returns:
        Human-readable total cost basis
    """
    df = ctx.portfolio.get_all_holdings()
    total_cost = (df["quantity"] * df["cost_basis"]).sum()

    return f"Total cost basis: {format_currency(total_cost)}"


async def get_total_gain_loss(ctx: AgentContext) -> str:
    """
    Get the overall profit/loss (current value - cost basis).

    Returns:
        Human-readable gain/loss with percentage
    """
    if not ctx.prices.is_ready():
        await ctx.prices.wait_until_ready()

    df = ctx.portfolio.get_all_holdings()
    total_cost = 0.0
    total_value = 0.0
    missing_prices = []

    for _, row in df.iterrows():
        symbol = row["symbol"]
        quantity = row["quantity"]
        cost_basis = row["cost_basis"]
        price = ctx.prices.get_price(symbol)

        total_cost += quantity * cost_basis

        if price is not None:
            total_value += quantity * price
        else:
            missing_prices.append(symbol)

    gain_loss = total_value - total_cost
    gain_loss_pct = (gain_loss / total_cost) * 100 if total_cost > 0 else 0

    if gain_loss >= 0:
        result = f"Total gain: {format_currency(gain_loss)} ({format_percentage(gain_loss_pct)})"
    else:
        result = f"Total loss: {format_currency(abs(gain_loss))} ({format_percentage(gain_loss_pct)})"

    if missing_prices:
        result += f"\n(Excludes {', '.join(missing_prices)} - prices unavailable)"

    return result


async def get_largest_position(ctx: AgentContext) -> str:
    """
    Get the largest holding by current value.

    Returns:
        Human-readable largest position details
    """
    if not ctx.prices.is_ready():
        await ctx.prices.wait_until_ready()

    df = ctx.portfolio.get_all_holdings()
    largest_symbol = None
    largest_value = 0.0
    total_value = 0.0

    for _, row in df.iterrows():
        symbol = row["symbol"]
        quantity = row["quantity"]
        price = ctx.prices.get_price(symbol)

        if price is not None:
            value = quantity * price
            total_value += value

            if value > largest_value:
                largest_value = value
                largest_symbol = symbol

    if largest_symbol is None:
        return "Unable to determine largest position - no prices available"

    pct_of_portfolio = (largest_value / total_value) * 100 if total_value > 0 else 0

    return (
        f"Largest position: {largest_symbol} at {format_currency(largest_value)} "
        f"({pct_of_portfolio:.1f}% of portfolio)"
    )


async def list_all_holdings(ctx: AgentContext) -> str:
    """
    Get a summary of all positions.

    Returns:
        Human-readable list of all holdings
    """
    if not ctx.prices.is_ready():
        await ctx.prices.wait_until_ready()

    df = ctx.portfolio.get_all_holdings()
    num_positions = len(df)

    lines = [f"Holdings ({num_positions} positions):"]

    for _, row in df.iterrows():
        symbol = row["symbol"]
        quantity = row["quantity"]
        price = ctx.prices.get_price(symbol)

        if price is not None:
            value = quantity * price
            lines.append(f"  - {symbol}: {quantity} shares, {format_currency(value)}")
        else:
            lines.append(f"  - {symbol}: {quantity} shares, price unavailable")

    return "\n".join(lines)
