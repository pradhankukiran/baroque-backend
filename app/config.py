from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_host: str = "localhost"
    database_port: int = 5432
    database_user: str = "postgres"
    database_password: str = "secret"
    database_name: str = "baroque"

    anthropic_admin_api_key: str = ""
    frontend_url: str = "http://localhost:5173"

    fetch_interval_minutes: int = 5

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    @property
    def database_url(self) -> str:
        return f"postgresql://{self.database_user}:{self.database_password}@{self.database_host}:{self.database_port}/{self.database_name}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
