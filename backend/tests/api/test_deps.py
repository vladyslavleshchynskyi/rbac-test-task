from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.models import Role
from tests.utils.user import user_with_role_headers


def test_invalid_token_returns_401(client: TestClient) -> None:
    headers = {"Authorization": "Bearer invalid"}
    r = client.get(f"{settings.API_V1_STR}/users/me", headers=headers)
    assert r.status_code == 401


def test_inactive_user_token_returns_401(client: TestClient, db: Session) -> None:
    user, headers = user_with_role_headers(client=client, db=db, role=Role.member)
    user.is_active = False
    db.add(user)
    db.commit()

    r = client.get(f"{settings.API_V1_STR}/users/me", headers=headers)
    assert r.status_code == 401
    assert r.json()["detail"] == "Inactive user"


def test_deleted_user_token_returns_401(client: TestClient, db: Session) -> None:
    user, headers = user_with_role_headers(client=client, db=db, role=Role.member)
    db.delete(user)
    db.commit()

    r = client.get(f"{settings.API_V1_STR}/users/me", headers=headers)
    assert r.status_code == 401
