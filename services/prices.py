import asyncio
from typing import Optional
import yfinance as yf


class PriceService:
    """Fetches and caches stock prices from Yahoo Finance."""

    def __init__(self):
        self._prices: dict[str, float] = {}
        self._ready = asyncio.Event()
        self._loading = False
        self._error: Optional[str] = None

    def is_ready(self) -> bool:
        """Check if prices have been loaded."""
        return self._ready.is_set()

    async def wait_until_ready(self) -> None:
        """Wait for prices to be loaded."""
        await self._ready.wait()

    def get_price(self, symbol: str) -> Optional[float]:
        """Get cached price for a symbol."""
        return self._prices.get(symbol.upper())

    async def fetch_one(self, symbol: str) -> Optional[float]:
        """Fetch and cache a single symbol's price on demand.

        Returns the price if successful, None otherwise.
        """
        symbol = symbol.upper()
        if symbol in self._prices:
            return self._prices[symbol]

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._fetch_prices_sync, [symbol])
        return self._prices.get(symbol)

    def get_all_prices(self) -> dict[str, float]:
        """Get all cached prices."""
        return self._prices.copy()

    async def fetch_prices(self, symbols: list[str]) -> None:
        """Fetch prices for all symbols asynchronously."""
        if self._loading:
            return

        self._loading = True
        self._error = None

        try:
            # Run yfinance in thread pool (it's synchronous)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._fetch_prices_sync, symbols)
        except Exception as e:
            self._error = str(e)
        finally:
            self._loading = False
            self._ready.set()

    def _fetch_prices_sync(self, symbols: list[str]) -> None:
        """Synchronous price fetching (runs in thread pool)."""
        symbols = [s.upper() for s in symbols]

        if not symbols:
            return

        # Fetch all tickers at once for efficiency
        tickers = yf.Tickers(" ".join(symbols))

        for symbol in symbols:
            try:
                ticker = tickers.tickers.get(symbol)
                if ticker is None:
                    continue

                # Get current price from fast_info or history
                info = ticker.fast_info
                if hasattr(info, "last_price") and info.last_price:
                    self._prices[symbol] = float(info.last_price)
                else:
                    # Fallback to history
                    hist = ticker.history(period="1d")
                    if not hist.empty:
                        self._prices[symbol] = float(hist["Close"].iloc[-1])
            except Exception:
                # Skip symbols that fail
                continue
