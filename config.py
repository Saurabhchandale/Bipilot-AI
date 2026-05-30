from pathlib import Path
import os

from dotenv import load_dotenv


load_dotenv()


BASE_DIR = Path(__file__).resolve().parent


class Config:
    """Central application configuration for Bipilot AI."""

    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key")
    UPLOAD_FOLDER = BASE_DIR / "datasets"
    DATABASE_PATH = BASE_DIR / "database" / "bipilot_ai.sqlite3"
    MAX_CONTENT_LENGTH = 25 * 1024 * 1024
    ALLOWED_EXTENSIONS = {"csv", "xls", "xlsx"}

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    AI_PROVIDER = os.getenv("AI_PROVIDER", "local")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
