from typing import List, Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: str = "CONSOLE"

    project_name: str = "itparty2026.project.api"
    version: str = "1.0.0"
    api_v1_prefix: str = "/api/v1"

    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 5

    backend_cors_origins: list[str] = ["*"]

    db_host: str = "db"  # Имя сервиса в docker-compose
    db_port: int = 5432
    db_user: str = "postgres"
    db_pass: str = "postgres"
    db_name: str = "db"

    # redis_host: str = "redis"
    # redis_port: int = 6379
    # redis_db: int = 0

    @property
    def db_url(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_pass}@{self.db_host}:{self.db_port}/{self.db_name}"
    #
    # @property
    # def redis_url(self) -> str:
    #     return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

config = Config()

