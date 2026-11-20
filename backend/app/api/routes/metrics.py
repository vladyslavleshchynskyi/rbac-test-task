from typing import Any

from fastapi import APIRouter, Depends
from sqlmodel import col, func, select

from app.api.deps import SessionDep, require_permission
from app.models import Metrics, Permission, Role, User

router = APIRouter(
    prefix="/metrics",
    tags=["metrics"],
    dependencies=[Depends(require_permission(Permission.METRICS_READ))],
)


@router.get("/", response_model=Metrics)
def read_metrics(session: SessionDep) -> Any:
    """
    Retrieve user metrics.
    """
    total_users = session.exec(select(func.count()).select_from(User)).one()
    active_users = session.exec(
        select(func.count()).select_from(User).where(col(User.is_active))
    ).one()
    role_counts = session.exec(
        select(User.role, func.count()).group_by(col(User.role))
    ).all()

    users_by_role = dict.fromkeys(Role, 0)
    users_by_role.update({Role(role): count for role, count in role_counts})
    return Metrics(
        total_users=total_users,
        active_users=active_users,
        users_by_role=users_by_role,
    )
