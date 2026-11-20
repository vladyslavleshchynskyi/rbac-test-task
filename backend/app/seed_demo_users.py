import logging

from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.core.db import engine, init_db
from app.models import Role, UserCreate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEMO_USERS = [
    ("manager@example.com", Role.manager),
    ("member@example.com", Role.member),
]


def seed_demo_users(session: Session) -> None:
    init_db(session)
    for email, role in DEMO_USERS:
        if crud.get_user_by_email(session=session, email=email):
            continue
        user_in = UserCreate(
            email=email, password=settings.FIRST_SUPERUSER_PASSWORD, role=role
        )
        crud.create_user(session=session, user_create=user_in)


def main() -> None:
    if settings.FASTAPI_ENV != "development":
        raise SystemExit("Demo users can only be seeded with FASTAPI_ENV=development")
    logger.info("Seeding demo users")
    with Session(engine) as session:
        seed_demo_users(session)
    logger.info("Demo users seeded")


if __name__ == "__main__":
    main()
