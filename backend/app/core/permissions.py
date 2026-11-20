from app.models import Permission, Role, User

ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.member: frozenset(),
    Role.manager: frozenset({Permission.USERS_READ, Permission.METRICS_READ}),
    Role.admin: frozenset(Permission),
}


def permissions_for(role: Role) -> list[Permission]:
    return sorted(ROLE_PERMISSIONS[role])


def has_permission(user: User, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS[user.role]
