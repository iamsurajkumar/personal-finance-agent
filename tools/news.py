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

    # Separate real articles from service messages/errors
    real = [a for a in articles if "title" in a and not ("error" in a or "message" in a)]
    problems = [a.get("error") or a.get("message") for a in articles if "error" in a or "message" in a]

    if not real and not problems:
        return "No recent news found for your portfolio holdings."

    if not real and problems:
        return f"News unavailable: {problems[0]}"

    # If we have real articles, use those (ignore partial batch failures)
    articles = real

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
