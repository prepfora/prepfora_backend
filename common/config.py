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
    aws_access_key_id: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    aws_secret_key: str = os.getenv("AWS_SECRET_KEY", "")
    aws_region: str = os.getenv("AWS_REGION", "eu-north-1")
    aws_bucket_name: str = os.getenv("AWS_BUCKET_NAME", "ryzly-apps")


settings = Settings()
