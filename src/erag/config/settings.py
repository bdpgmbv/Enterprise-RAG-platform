from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from erag.config.auth import AuthSettings
from erag.config.database import DatabaseSettings
from erag.config.observability import ObservabilitySettings


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="ERAG_", extra="ignore"
    )

    service_name: str = "erag-api"
    environment: str = "local"
    debug: bool = False
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
