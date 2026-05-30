import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""

    PORTFOLIO_CSV_PATH: str = os.getenv("PORTFOLIO_CSV_PATH", "portfolio.csv")
    ALPHA_VANTAGE_API_KEY: str = os.getenv("ALPHA_VANTAGE_API_KEY", "")
