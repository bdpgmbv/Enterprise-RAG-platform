from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="ERAG_AUTH_", extra="ignore"
    )

    issuer: str = "http://localhost:8095/realms/erag"
    client_id: str = "erag-api"
    client_secret: SecretStr | None = None
    audience: str = "erag-api"

    allowed_algorithms: tuple[str, ...] = ("RS256",)
    groups_claim: str = "groups"
    jwks_cache_seconds: int = 3600

    leeway_seconds: int = 30
    enabled: bool = True

    @property
    def discovery_url(self) -> str:
        return f"{self.issuer}/.well-known/openid-configuration"
