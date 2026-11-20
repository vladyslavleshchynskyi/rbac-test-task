import pytest

from app.core.permissions import ROLE_PERMISSIONS, Permission, permissions_for
from app.models import Role


@pytest.mark.parametrize(
    ("role", "expected"),
    [
        (Role.member, set()),
        (Role.manager, {Permission.USERS_READ, Permission.METRICS_READ}),
        (Role.admin, set(Permission)),
    ],
)
def test_role_permissions(role: Role, expected: set[Permission]) -> None:
    assert set(permissions_for(role)) == expected


def test_every_role_is_mapped() -> None:
    assert set(ROLE_PERMISSIONS) == set(Role)
