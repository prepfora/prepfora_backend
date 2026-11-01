"""add_referral_code_to_user

Revision ID: 23eeb9af819d
Revises: acd78fb53371
Create Date: 2026-11-01 20:47:21.232009

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '23eeb9af819d'
down_revision: Union[str, Sequence[str], None] = 'acd78fb53371'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    user_cols = [col['name'] for col in inspector.get_columns('user')]
    if 'referral_code' not in user_cols:
        op.add_column('user', sa.Column('referral_code', sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    user_cols = [col['name'] for col in inspector.get_columns('user')]
    if 'referral_code' in user_cols:
        op.drop_column('user', 'referral_code')
