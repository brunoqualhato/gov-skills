"""Global configuration and paths for gov-skills."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
DB_PATH = DATA_DIR / "gov_data.duckdb"
SKILLS_DIR = BASE_DIR / "skills"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
RAW_DIR.mkdir(parents=True, exist_ok=True)


class Settings:
    """Settings and secrets for government open data APIs."""

    BASE_DIR: Path = BASE_DIR
    DATA_DIR: Path = DATA_DIR
    RAW_DIR: Path = RAW_DIR
    DB_PATH: Path = DB_PATH
    SKILLS_DIR: Path = SKILLS_DIR

    # User-Agent standard for Brazilian Government transparency portals
    USER_AGENT: str = os.getenv(
        "GOV_SKILLS_USER_AGENT",
        "gov-skills/0.1.0 (Brasil Open Data Intelligence; +https://github.com/brunoqualhato/gov-skills)",
    )

    # API Keys (optional for open public APIs, required for specific portals like CGU)
    CGU_API_KEY: str = os.getenv("CGU_API_KEY", "")
    TRANSPARENCIA_API_KEY: str = os.getenv("TRANSPARENCIA_API_KEY", "") or CGU_API_KEY

    # Timeout and retries
    DEFAULT_TIMEOUT: float = float(os.getenv("DEFAULT_TIMEOUT", "30.0"))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))


settings = Settings()
