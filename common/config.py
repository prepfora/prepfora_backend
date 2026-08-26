from pydantic_settings import BaseSettings, SettingsConfigDict
import os


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    database_url: str = os.getenv("DATABASE_URL", "")
    port: int = 8000
    debug: bool = False
    aloc_access_token: str = os.getenv("ALOC_ACCESS_TOKEN", "")


settings = Settings()
