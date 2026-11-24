"""add_score_completion_to_exam_and_code_to_badge

Revision ID: f4a8c91d2e3b
Revises: 23eeb9af819d
Create Date: 2026-11-24 20:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f4a8c91d2e3b'
down_revision: Union[str, Sequence[str], None] = '23eeb9af819d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # 1. Add score, is_completed, completed_at to user_examination
    exam_cols = [col['name'] for col in inspector.get_columns('user_examination')]
    if 'score' not in exam_cols:
        op.add_column('user_examination', sa.Column('score', sa.Float(), nullable=True, server_default='0.0'))
    if 'is_completed' not in exam_cols:
        op.add_column('user_examination', sa.Column('is_completed', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    if 'completed_at' not in exam_cols:
        op.add_column('user_examination', sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True))

    # 2. Add code to badge
    badge_cols = [col['name'] for col in inspector.get_columns('badge')]
    if 'code' not in badge_cols:
        op.add_column('badge', sa.Column('code', sa.String(length=100), nullable=True))
        op.create_index(op.f('ix_badge_code'), 'badge', ['code'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    badge_cols = [col['name'] for col in inspector.get_columns('badge')]
    if 'code' in badge_cols:
        op.drop_index(op.f('ix_badge_code'), table_name='badge')
        op.drop_column('badge', 'code')

    exam_cols = [col['name'] for col in inspector.get_columns('user_examination')]
    if 'completed_at' in exam_cols:
        op.drop_column('user_examination', 'completed_at')
    if 'is_completed' in exam_cols:
        op.drop_column('user_examination', 'is_completed')
    if 'score' in exam_cols:
        op.drop_column('user_examination', 'score')
