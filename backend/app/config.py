from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "aicourt"
    postgres_password: str = "aicourt_secret"
    postgres_db: str = "aicourt"

    redis_url: str = "redis://localhost:6379/0"

    app_port: int = 8000
    app_secret_key: str = "change-me-in-production"
    app_debug: bool = True

    openclaw_bin: str = "openclaw"
    openclaw_config_path: str = "~/.openclaw/openclaw.json"

    upload_dir: str = "./uploads"
    upload_max_size_mb: int = 20
    oss_enabled: bool = False
    oss_endpoint: str = ""
    oss_bucket: str = ""
    oss_access_key: str = ""
    oss_secret_key: str = ""

    stall_threshold_sec: int = 180
    max_dispatch_retry: int = 3
    dispatch_timeout_sec: int = 300

    llm_api_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
