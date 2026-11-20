import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.models import Role
from tests.utils.item import create_random_item
from tests.utils.user import create_random_user, user_with_role_headers
from tests.utils.utils import random_email, random_lower_string


@pytest.mark.parametrize(
    ("role", "method", "path", "expected"),
    [
        (Role.member, "GET", "/users/", 403),
        (Role.manager, "GET", "/users/", 200),
        (Role.admin, "GET", "/users/", 200),
        (Role.member, "GET", "/users/{other}", 403),
        (Role.manager, "GET", "/users/{other}", 200),
        (Role.manager, "GET", "/users/{missing}", 404),
        (Role.member, "GET", "/users/{missing}", 403),
        (Role.member, "POST", "/users/", 403),
        (Role.manager, "POST", "/users/", 403),
        (Role.admin, "POST", "/users/", 200),
        (Role.member, "PATCH", "/users/{other}", 403),
        (Role.manager, "PATCH", "/users/{other}", 403),
        (Role.admin, "PATCH", "/users/{other}", 200),
        (Role.member, "DELETE", "/users/{other}", 403),
        (Role.manager, "DELETE", "/users/{other}", 403),
        (Role.admin, "DELETE", "/users/{other}", 200),
    ],
)
def test_access_matrix(
    client: TestClient,
    db: Session,
    role: Role,
    method: str,
    path: str,
    expected: int,
) -> None:
    _, headers = user_with_role_headers(client=client, db=db, role=role)
    other = create_random_user(db)
    url = settings.API_V1_STR + path.format(other=other.id, missing=uuid.uuid4())
    body: dict[str, Any] | None = None
    if method == "POST":
        body = {"email": random_email(), "password": random_lower_string()}
    elif method == "PATCH":
        body = {"full_name": "Updated Name"}

    r = client.request(method, url, headers=headers, json=body)
    assert r.status_code == expected


@pytest.mark.parametrize("data", [{"role": "member"}, {"is_active": False}])
def test_admin_cannot_change_own_role_or_status(
    client: TestClient, db: Session, data: dict[str, Any]
) -> None:
    admin, headers = user_with_role_headers(client=client, db=db, role=Role.admin)
    r = client.patch(
        f"{settings.API_V1_STR}/users/{admin.id}", headers=headers, json=data
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "Users cannot change their own role or active status"

    db.refresh(admin)
    assert admin.role == Role.admin
    assert admin.is_active is True


def test_admin_can_submit_unchanged_own_role_and_status(
    client: TestClient, db: Session
) -> None:
    admin, headers = user_with_role_headers(client=client, db=db, role=Role.admin)
    data = {"role": "admin", "is_active": True, "full_name": "New Name"}
    r = client.patch(
        f"{settings.API_V1_STR}/users/{admin.id}", headers=headers, json=data
    )
    assert r.status_code == 200
    assert r.json()["full_name"] == "New Name"


def test_admin_can_change_other_users_role(client: TestClient, db: Session) -> None:
    _, admin_headers = user_with_role_headers(client=client, db=db, role=Role.admin)
    member, member_headers = user_with_role_headers(
        client=client, db=db, role=Role.member
    )
    r = client.patch(
        f"{settings.API_V1_STR}/users/{member.id}",
        headers=admin_headers,
        json={"role": "manager"},
    )
    assert r.status_code == 200
    assert r.json()["role"] == "manager"

    r = client.get(f"{settings.API_V1_STR}/users/me", headers=member_headers)
    assert "users:read" in r.json()["permissions"]


def test_demotion_applies_to_existing_token(client: TestClient, db: Session) -> None:
    _, admin_headers = user_with_role_headers(client=client, db=db, role=Role.admin)
    manager, manager_headers = user_with_role_headers(
        client=client, db=db, role=Role.manager
    )
    r = client.get(f"{settings.API_V1_STR}/users/", headers=manager_headers)
    assert r.status_code == 200

    r = client.patch(
        f"{settings.API_V1_STR}/users/{manager.id}",
        headers=admin_headers,
        json={"role": "member"},
    )
    assert r.status_code == 200

    r = client.get(f"{settings.API_V1_STR}/users/", headers=manager_headers)
    assert r.status_code == 403


def test_deactivation_applies_to_existing_token(
    client: TestClient, db: Session
) -> None:
    _, admin_headers = user_with_role_headers(client=client, db=db, role=Role.admin)
    member, member_headers = user_with_role_headers(
        client=client, db=db, role=Role.member
    )
    r = client.get(f"{settings.API_V1_STR}/users/me", headers=member_headers)
    assert r.status_code == 200

    r = client.patch(
        f"{settings.API_V1_STR}/users/{member.id}",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert r.status_code == 200

    r = client.get(f"{settings.API_V1_STR}/users/me", headers=member_headers)
    assert r.status_code == 401


@pytest.mark.parametrize("method", ["GET", "PUT", "DELETE"])
def test_manager_cannot_access_other_users_items(
    client: TestClient, db: Session, method: str
) -> None:
    _, headers = user_with_role_headers(client=client, db=db, role=Role.manager)
    item = create_random_item(db)
    body = {"title": "Updated"} if method == "PUT" else None
    r = client.request(
        method, f"{settings.API_V1_STR}/items/{item.id}", headers=headers, json=body
    )
    assert r.status_code == 403


def test_admin_can_access_other_users_items(client: TestClient, db: Session) -> None:
    _, headers = user_with_role_headers(client=client, db=db, role=Role.admin)
    item = create_random_item(db)
    r = client.get(f"{settings.API_V1_STR}/items/{item.id}", headers=headers)
    assert r.status_code == 200
