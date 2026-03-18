from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # OpenAI
    OPENAI_API_KEY: str
    ROUTER_LLM: str = "gpt-4.1-nano"
    INTENT_PARSER: str = "gpt-4.1-nano"
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Telegram
    TELEGRAM_BOT_TOKEN: str

    # Auth
    PASSWORD: str
    JWT_SECRET: str

    # Google Calendar (optional — calendar features disabled if not set)
    GOOGLE_SERVICE_ACCOUNT_FILE: str | None = None
    GOOGLE_CALENDAR_ID: str | None = None

    # ChromaDB — persistent local vector store (no server required)
    CHROMA_PATH: Path = Path("data/chroma")

    # Pipeline
    HISTORY_LENGTH: int = 3

    # Data root — all paths are derived from this
    DATA_DIR: Path = Path("data")

    @field_validator("DATA_DIR", mode="before")
    @classmethod
    def parse_data_dir(cls, v: str | Path) -> Path:
        return Path(v)

    # Derived paths (read-only properties)
    @property
    def notes_dir(self) -> Path:
        return self.DATA_DIR / "notes"

    @property
    def notes_archive_dir(self) -> Path:
        return self.DATA_DIR / "notes" / "archive"

    @property
    def shopping_lists_dir(self) -> Path:
        return self.DATA_DIR / "shopping_lists"

    @property
    def shopping_lists_archive_dir(self) -> Path:
        return self.DATA_DIR / "shopping_lists" / "archive"

    @property
    def reminders_file(self) -> Path:
        return self.DATA_DIR / "reminders" / "reminders.json"

    @property
    def db_path(self) -> Path:
        return self.DATA_DIR / "nora.db"

    @property
    def state_file(self) -> Path:
        return self.DATA_DIR / "state.json"

    @property
    def preferences_file(self) -> Path:
        return self.DATA_DIR / "preferences.json"


settings = Settings()
