import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Project root — always the directory containing this config file
_PROJECT_ROOT = Path(__file__).parent.resolve()


def _resolve_path(raw: str) -> str:
    """Resolve a path relative to the project root."""
    p = Path(raw)
    if p.is_absolute():
        return str(p)
    return str(_PROJECT_ROOT / p)


class Config:
    """Application configuration loaded from environment variables."""

    PORTFOLIO_CSV_PATH: str = _resolve_path(
        os.getenv("PORTFOLIO_CSV_PATH", "portfolio.csv")
    )
    ALPHA_VANTAGE_API_KEY: str = os.getenv("ALPHA_VANTAGE_API_KEY", "")
    ORDER_HISTORY_PATH: str = str(_PROJECT_ROOT / "order_history.json")
