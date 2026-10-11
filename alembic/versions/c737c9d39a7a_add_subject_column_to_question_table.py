"""add_subject_column_to_question_table

Revision ID: c737c9d39a7a
Revises: c8ab5fcf7b0f
Create Date: 2026-10-09 13:59:59.282712

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c737c9d39a7a'
down_revision: Union[str, Sequence[str], None] = 'c8ab5fcf7b0f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    question_cols = [col['name'] for col in inspector.get_columns('question')]
    if 'subject' not in question_cols:
        op.add_column('question', sa.Column('subject', sa.String(length=100), nullable=True))
        op.create_index(op.f('ix_question_subject'), 'question', ['subject'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    question_cols = [col['name'] for col in inspector.get_columns('question')]
    if 'subject' in question_cols:
        op.drop_index(op.f('ix_question_subject'), table_name='question')
        op.drop_column('question', 'subject')
