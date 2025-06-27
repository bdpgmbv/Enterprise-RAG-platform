from pydantic import SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

from erag.vault.client import read_secret


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="ERAG_DB_", extra="ignore"
    )

    host: str = "localhost"
    port: int = 5472
    user: str = "erag_app"
    name: str = "erag_db"

    pool_size: int = 10
    max_overflow: int = 5

    @property
    def url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.user}:{self.password.get_secret_value()}"
            f"@{self.host}:{self.port}/{self.name}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def password(self) -> SecretStr:
        """Fetched from Vault, never from a file."""
        return SecretStr(read_secret("database")["password"])
