"""Replace is_superuser with role

Revision ID: 3f8aabd50af4
Revises: fe56fa70289e
Create Date: 2026-11-20 13:54:14.289532

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = '3f8aabd50af4'
down_revision = 'fe56fa70289e'
branch_labels = None
depends_on = None


role_enum = sa.Enum('admin', 'manager', 'member', name='userrole')


def upgrade():
    role_enum.create(op.get_bind())
    op.add_column('user', sa.Column('role', role_enum, nullable=True, server_default='member'))
    op.execute("""UPDATE "user" SET role = 'admin' WHERE is_superuser""")
    op.execute("""UPDATE "user" SET role = 'member' WHERE role IS NULL""")
    op.alter_column('user', 'role', nullable=False)
    op.drop_column('user', 'is_superuser')


def downgrade():
    op.add_column('user', sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default=sa.false()))
    # Managers have no superuser equivalent and fall back to regular users
    op.execute("""UPDATE "user" SET is_superuser = true WHERE role = 'admin'""")
    op.alter_column('user', 'is_superuser', server_default=None)
    op.drop_column('user', 'role')
    role_enum.drop(op.get_bind())
