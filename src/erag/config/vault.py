from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class VaultSettings(BaseSettings):
    """How to reach Vault. Read from env vars prefixed with ERAG_VAULT_."""

    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="ERAG_VAULT_", extra="ignore"
    )

    address: str = "https://localhost:8200"
    ca_path: str = "docker/certs/erag-local-root-ca.crt"

    # No defaults: a missing credential must stop the app at startup.
    role_id: str
    secret_id: SecretStr
