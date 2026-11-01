
from pathlib import Path
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


# Resolve the backend directory
BASE_DIR = Path(__file__).resolve().parents[1]

# Database location: backend/data/roshtaty.db
DB_PATH = BASE_DIR / "data" / "roshtaty.db"

# Ensure the database directory exists
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Roshtaty Medicine Intelligence Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "127.0.0.1"
    PORT: int = 5000

    # Database
    DATABASE_URL: str = f"sqlite:///{DB_PATH.as_posix()}"

    # Security
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # CORS
    CORS_ORIGINS: str = "*"

    # OCR
    MAX_UPLOAD_MB: int = 10
    OCR_LANG: str = "eng"

    # AI
    AI_PROVIDER: str = "ollama"
    AI_MODEL: str = "llama-3.1-8b"
    AI_API_KEY: Optional[str] = None
    AI_BASE_URL: Optional[str] = None
    AI_ENABLED: bool = False

    # External APIs
    RXNAV_BASE_URL: str = "https://rxnav.nlm.nih.gov/REST"
    OPENFDA_BASE_URL: str = "https://api.fda.gov"

    # Ingestion
    INGESTION_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
