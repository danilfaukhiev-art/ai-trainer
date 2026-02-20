from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App
    app_env: str = "development"
    app_port: int = 8000
    app_secret_key: str = "change_me_in_production"
    cors_origins: str = "http://localhost:5173"

    # Telegram
    telegram_bot_token: str
    telegram_webhook_url: str = ""
    telegram_webhook_secret: str = "webhook_secret"

    # Database
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/ai_trainer"
    database_url_sync: str = "postgresql://postgres:password@localhost:5432/ai_trainer"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # OpenAI
    openai_api_key: str
    openai_model: str = "gpt-4o"
    openai_vision_model: str = "gpt-4o"

    # S3
    s3_endpoint_url: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket_name: str = "ai-trainer-storage"
    s3_region: str = "us-east-1"

    # Business rules
    trial_days: int = 7
    free_ai_messages_per_day: int = 3

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


settings = Settings()
