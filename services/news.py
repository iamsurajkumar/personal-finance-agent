"""Alpha Vantage News & Sentiments API wrapper."""

import asyncio
from typing import Optional
import httpx


BASE_URL = "https://www.alphavantage.co/query"
MAX_TICKERS_PER_REQUEST = 5   # Alpha Vantage hard limit


class NewsService:
    """Fetches news from Alpha Vantage for portfolio symbols."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def fetch_news(self, symbols: list[str]) -> list[dict]:
        """Fetch news articles for a list of tickers.

        Batches requests into groups of MAX_TICKERS_PER_REQUEST to
        respect Alpha Vantage's ticker limit, then deduplicates.
        Returns articles sorted by time (newest first).
        """
        if not symbols or not self.api_key:
            return []

        symbols = [s.upper() for s in symbols]
        all_articles: list[dict] = []
        seen: set[str] = set()

        for i in range(0, len(symbols), MAX_TICKERS_PER_REQUEST):
            batch = symbols[i:i + MAX_TICKERS_PER_REQUEST]

            # Respect rate limit (1 req/s on free tier)
            if i > 0:
                await asyncio.sleep(1.1)

            articles = await self._fetch_batch(batch)

            for a in articles:
                url = a.get("url", "")
                if url and url not in seen:
                    seen.add(url)
                    all_articles.append(a)

        return sorted(
            all_articles,
            key=lambda a: a.get("published", ""),
            reverse=True,
        )[:20]

    async def _fetch_batch(self, symbols: list[str]) -> list[dict]:
        """Fetch news for a single batch of up to 5 tickers."""
        ticker_str = ",".join(symbols)

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    BASE_URL,
                    params={
                        "function": "NEWS_SENTIMENT",
                        "tickers": ticker_str,
                        "apikey": self.api_key,
                        "limit": 50,
                    },
                    timeout=15.0,
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception:
                return [{"error": "Failed to fetch news from Alpha Vantage"}]

        # Alpha Vantage returns {"feed": [...]} or an error/rate-limit message
        feed = data.get("feed") if isinstance(data, dict) else None
        if not feed:
            note = data.get("Information") or data.get("Note") or "No news available"
            return [{"message": note}]

        articles: list[dict] = []

        for item in feed:
            title = item.get("title", "")
            url = item.get("url", "")
            articles.append({
                "title": title,
                "url": url,
                "summary": item.get("summary", ""),
                "source": item.get("source", ""),
                "published": item.get("time_published", ""),
                "tickers": [
                    t.get("ticker", "")
                    for t in item.get("ticker_sentiment", [])
                ],
                "overall_sentiment": item.get("overall_sentiment_label", "neutral"),
            })

        return articles
