import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""

    PORTFOLIO_CSV_PATH: str = os.getenv("PORTFOLIO_CSV_PATH", "portfolio.csv")
