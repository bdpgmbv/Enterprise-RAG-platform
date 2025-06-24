from pydantic import BaseModel


class Principal(BaseModel):
    subject: str

    username: str | None = None

    groups: frozenset[str] = frozenset()

    roles: frozenset[str] = frozenset()

    is_service_account: bool = False

    def has_role(self, role: str) -> bool:
        return role in self.roles
