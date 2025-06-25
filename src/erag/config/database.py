"""Postgres connection settings."""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Read from env vars prefixed with ERAG_DB_."""

    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="ERAG_DB_", extra="ignore"
    )

    host: str = "localhost"
    port: int = 5472
    user: str = "erag"

    # SecretStr keeps the password out of logs and error messages.
    password: SecretStr = SecretStr("erag")
    name: str = "erag"

    # Connections kept open per worker process.
    pool_size: int = 10
    max_overflow: int = 5

    @property
    def url(self) -> str:
        """Async SQLAlchemy connection URL."""
        return (
            f"postgresql+asyncpg://{self.user}:{self.password.get_secret_value()}"
            f"@{self.host}:{self.port}/{self.name}"
        )
