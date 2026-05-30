"""Alpha Vantage News & Sentiments API wrapper."""

from typing import Optional
import httpx


BASE_URL = "https://www.alphavantage.co/query"


class NewsService:
    """Fetches news from Alpha Vantage for portfolio symbols."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def fetch_news(self, symbols: list[str]) -> list[dict]:
        """Fetch news articles for a list of tickers.

        Returns deduplicated articles sorted by time (newest first).
        """
        if not symbols or not self.api_key:
            return []

        ticker_str = ",".join(s.upper() for s in symbols)

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
        seen: set[str] = set()

        for item in feed:
            title = item.get("title", "")
            url = item.get("url", "")
            if url and url not in seen:
                seen.add(url)
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

        # Alpha Vantage returns newest-first by default
        return articles[:20]  # cap at 20 to keep responses manageable
