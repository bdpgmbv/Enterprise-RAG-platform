from functools import lru_cache

import hvac

from erag.config.vault import VaultSettings


@lru_cache(maxsize=1)
def get_client() -> hvac.Client:
    """Log in to Vault once, then reuse the connection."""
    settings = VaultSettings()

    client = hvac.Client(url=settings.address, verify=settings.ca_path)
    client.auth.approle.login(
        role_id=settings.role_id,
        secret_id=settings.secret_id.get_secret_value(),
    )
    return client


def read_secret(name: str) -> dict[str, str]:
    """Read one secret from the erag engine."""
    response = get_client().secrets.kv.v2.read_secret_version(
        mount_point="erag", path=name, raise_on_deleted_version=True
    )
    data: dict[str, str] = response["data"]["data"]
    return data