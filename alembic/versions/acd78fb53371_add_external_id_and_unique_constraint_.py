"""add_external_id_and_unique_constraint_to_question

Revision ID: acd78fb53371
Revises: c737c9d39a7a
Create Date: 2026-10-09 15:52:24.349422

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'acd78fb53371'
down_revision: Union[str, Sequence[str], None] = 'c737c9d39a7a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    question_cols = [col['name'] for col in inspector.get_columns('question')]
    if 'external_id' not in question_cols:
        op.add_column('question', sa.Column('external_id', sa.Integer(), nullable=True))
        op.create_index(op.f('ix_question_external_id'), 'question', ['external_id'], unique=False)

    constraints = [c['name'] for c in inspector.get_unique_constraints('question')]
    if 'uq_question_subject_external_id' not in constraints:
        op.create_unique_constraint('uq_question_subject_external_id', 'question', ['subject', 'external_id'])


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    constraints = [c['name'] for c in inspector.get_unique_constraints('question')]
    if 'uq_question_subject_external_id' in constraints:
        op.drop_constraint('uq_question_subject_external_id', 'question', type_='unique')
    question_cols = [col['name'] for col in inspector.get_columns('question')]
    if 'external_id' in question_cols:
        op.drop_index(op.f('ix_question_external_id'), table_name='question')
        op.drop_column('question', 'external_id')
