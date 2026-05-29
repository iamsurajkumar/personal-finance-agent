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
