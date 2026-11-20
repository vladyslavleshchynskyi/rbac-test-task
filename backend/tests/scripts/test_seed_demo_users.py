from sqlmodel import Session, func, select

from app import crud
from app.models import Role, User
from app.seed_demo_users import DEMO_USERS, seed_demo_users


def test_seed_demo_users_is_idempotent(db: Session) -> None:
    seed_demo_users(db)
    manager = crud.get_user_by_email(session=db, email="manager@example.com")
    assert manager
    manager.role = Role.member
    db.add(manager)
    db.commit()

    seed_demo_users(db)

    for email, role in DEMO_USERS:
        count = db.exec(
            select(func.count()).select_from(User).where(User.email == email)
        ).one()
        assert count == 1
        user = crud.get_user_by_email(session=db, email=email)
        assert user
        # Existing users are left untouched
        expected = Role.member if email == "manager@example.com" else role
        assert user.role == expected
