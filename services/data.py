from datetime import date, datetime
from typing import Optional
import pandas as pd


class DataService:
    """Loads and queries the portfolio CSV."""

    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self._df: Optional[pd.DataFrame] = None

    def load(self) -> None:
        """Load the CSV file into memory."""
        self._df = pd.read_csv(
            self.csv_path,
            parse_dates=["purchase_date"],
            dtype={
                "symbol": str,
                "quantity": int,
                "cost_basis": float,
            },
        )
        # Normalize symbols to uppercase
        self._df["symbol"] = self._df["symbol"].str.upper()

    @property
    def df(self) -> pd.DataFrame:
        """Get the underlying DataFrame."""
        if self._df is None:
            raise RuntimeError("DataService not loaded. Call load() first.")
        return self._df

    def get_all_holdings(self) -> pd.DataFrame:
        """Return all holdings."""
        return self.df.copy()

    def get_holding(self, symbol: str) -> Optional[pd.Series]:
        """Get a specific holding by symbol."""
        symbol = symbol.upper()
        matches = self.df[self.df["symbol"] == symbol]
        if matches.empty:
            return None
        return matches.iloc[0]

    def get_symbols(self) -> list[str]:
        """Get list of all symbols in portfolio."""
        return self.df["symbol"].tolist()

    def get_total_cost_basis(self) -> float:
        """Calculate total cost basis (quantity * cost_basis for each holding)."""
        return (self.df["quantity"] * self.df["cost_basis"]).sum()

    # ── Write operations ──────────────────────────────────────────

    def buy(self, symbol: str, quantity: int, fill_price: float) -> dict:
        """Execute a buy: increase quantity, re-average cost basis.

        Returns a dict describing the updated holding.
        """
        symbol = symbol.upper()
        existing = self.get_holding(symbol)

        if existing is not None:
            idx = existing.name  # DataFrame index
            old_qty = int(existing["quantity"])
            old_cost = float(existing["cost_basis"])
            new_qty = old_qty + quantity
            new_cost = (
                (old_qty * old_cost) + (quantity * fill_price)
            ) / new_qty
            self._df.at[idx, "quantity"] = new_qty
            self._df.at[idx, "cost_basis"] = round(new_cost, 4)
        else:
            today = date.today().strftime("%Y-%m-%d")
            new_row = pd.DataFrame([{
                "symbol": symbol,
                "quantity": quantity,
                "cost_basis": fill_price,
                "purchase_date": today,
            }])
            self._df = pd.concat([self._df, new_row], ignore_index=True)

        self._save()
        return self.get_holding(symbol).to_dict()

    def sell(self, symbol: str, quantity: int, fill_price: float) -> dict:
        """Execute a sell: reduce quantity, remove row if zero.

        Returns a dict with the result.
        Raises ValueError if insufficient shares.
        """
        symbol = symbol.upper()
        existing = self.get_holding(symbol)

        if existing is None:
            raise ValueError(f"No position found for {symbol}")

        idx = existing.name
        old_qty = int(existing["quantity"])

        if quantity > old_qty:
            raise ValueError(
                f"Insufficient shares of {symbol}: "
                f"have {old_qty}, trying to sell {quantity}"
            )

        new_qty = old_qty - quantity

        if new_qty == 0:
            self._df = self._df.drop(idx).reset_index(drop=True)
            self._save()
            return {
                "symbol": symbol,
                "quantity": 0,
                "removed": True,
                "fill_price": fill_price,
            }

        self._df.at[idx, "quantity"] = new_qty
        self._save()
        return self.get_holding(symbol).to_dict()

    def _save(self) -> None:
        """Persist the DataFrame back to CSV."""
        self._df.to_csv(self.csv_path, index=False)
