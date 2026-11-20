from enum import StrEnum

from app.models import Role


class Permission(StrEnum):
    USERS_READ = "users:read"
    USERS_MANAGE = "users:manage"
    METRICS_READ = "metrics:read"
    ITEMS_MANAGE_ALL = "items:manage_all"


ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.member: frozenset(),
    Role.manager: frozenset({Permission.USERS_READ, Permission.METRICS_READ}),
    Role.admin: frozenset(Permission),
}


def permissions_for(role: Role) -> list[Permission]:
    return sorted(ROLE_PERMISSIONS[role])
