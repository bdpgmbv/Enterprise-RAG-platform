from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from erag.config.observability import ObservabilitySettings


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="ERAG_")

    service_name: str = "erag-api"
    environment: str = "local"
    debug: bool = False
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
