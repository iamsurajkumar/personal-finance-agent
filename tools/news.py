"""Qualitative news tool using Alpha Vantage."""

from .base import AgentContext


async def get_portfolio_news(symbol: str | None, ctx: AgentContext) -> str:
    """Fetch news for a specific symbol or all portfolio symbols.

    Args:
        symbol: Ticker symbol (e.g., AAPL). If omitted, fetches for all holdings.
    """
    if ctx.news is None:
        return (
            "News is not configured. To enable portfolio news:\n"
            "1. Get a free API key at https://alphavantage.co/support/#api-key\n"
            "2. Add it to your .env file: ALPHA_VANTAGE_API_KEY=your_key_here\n"
            "3. Restart the MCP server"
        )

    if symbol:
        symbols = [symbol.upper()]
    else:
        symbols = ctx.portfolio.get_symbols()
        if not symbols:
            return "No symbols in portfolio."

    articles = await ctx.news.fetch_news(symbols)

    # Handle error messages from the service
    if articles and ("error" in articles[0] or "message" in articles[0]):
        msg = articles[0].get("error") or articles[0].get("message")
        return f"News unavailable: {msg}"

    if not articles:
        return "No recent news found for your portfolio holdings."

    lines = [f"📰 Portfolio News ({len(articles)} articles):", ""]
    for a in articles:
        tickers = ", ".join(a.get("tickers", [])) or "—"
        sentiment = a.get("overall_sentiment", "neutral").capitalize()
        lines.append(
            f"• [{tickers}] {a['title']}\n"
            f"  {a.get('source', '')} · {sentiment}\n"
            f"  {a.get('url', '')}"
        )

    return "\n".join(lines)
