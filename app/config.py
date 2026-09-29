from functools import lru_cache
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    telegram_bot_token: SecretStr = Field(alias="TELEGRAM_BOT_TOKEN")
    gemini_api_key: SecretStr = Field(alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-3.6-flash", alias="GEMINI_MODEL")
    max_photos_per_session: int = Field(default=10, ge=1, le=20, alias="MAX_PHOTOS_PER_SESSION")
    max_image_bytes: int = Field(default=8 * 1024 * 1024, ge=100_000, alias="MAX_IMAGE_BYTES")
    music_provider: str = Field(default="none", alias="MUSIC_PROVIDER")


@lru_cache
def get_settings() -> Settings:
    return Settings()
