import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.models import Role
from tests.utils.user import user_with_role_headers


def test_read_metrics_as_member_forbidden(client: TestClient, db: Session) -> None:
    _, headers = user_with_role_headers(client=client, db=db, role=Role.member)
    r = client.get(f"{settings.API_V1_STR}/metrics/", headers=headers)
    assert r.status_code == 403


@pytest.mark.parametrize("role", [Role.manager, Role.admin])
def test_read_metrics(client: TestClient, db: Session, role: Role) -> None:
    _, headers = user_with_role_headers(client=client, db=db, role=role)
    r = client.get(f"{settings.API_V1_STR}/metrics/", headers=headers)
    assert r.status_code == 200
    metrics = r.json()
    assert set(metrics["users_by_role"]) == {"admin", "manager", "member"}
    assert sum(metrics["users_by_role"].values()) == metrics["total_users"]
    assert 0 < metrics["active_users"] <= metrics["total_users"]
