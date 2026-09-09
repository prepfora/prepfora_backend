"""create question table

Revision ID: 40be0bb71302
Revises: 560bb9cd4c5e
Create Date: 2026-09-07 17:48:31.239845

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '40be0bb71302'
down_revision: Union[str, Sequence[str], None] = '560bb9cd4c5e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    if 'question' not in tables:
        op.create_table(
            'question',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('question', sa.String(), nullable=False),
            sa.Column('option', sa.JSON(), nullable=True),
            sa.Column('section', sa.String(), nullable=True),
            sa.Column('image', sa.String(length=255), nullable=True),
            sa.Column('answer', sa.String(), nullable=True),
            sa.Column('solution', sa.String(), nullable=True),
            sa.Column('examtype', sa.String(length=50), nullable=True),
            sa.Column('examyear', sa.String(length=50), nullable=True),
            sa.Column('has_passage', sa.Boolean(), nullable=True),
            sa.Column('category', sa.String(length=100), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('isDeleted', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_question_id'), 'question', ['id'], unique=False)
    
    user_columns = [col['name'] for col in inspector.get_columns('user')]
    if 'phone' not in user_columns:
        op.add_column('user', sa.Column('phone', sa.String(length=255), nullable=True))
    if 'current_examination_date' not in user_columns:
        op.add_column('user', sa.Column('current_examination_date', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    user_columns = [col['name'] for col in inspector.get_columns('user')]
    tables = inspector.get_table_names()

    if 'current_examination_date' in user_columns:
        op.drop_column('user', 'current_examination_date')
    if 'phone' in user_columns:
        op.drop_column('user', 'phone')
    if 'question' in tables:
        op.drop_index(op.f('ix_question_id'), table_name='question')
        op.drop_table('question')
