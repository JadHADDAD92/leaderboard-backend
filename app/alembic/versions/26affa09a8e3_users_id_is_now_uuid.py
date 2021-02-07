"""users id is now UUID

Revision ID: 26affa09a8e3
Revises: 08fa6a844e0c
Create Date: 2020-12-20 18:52:10.596327

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '26affa09a8e3'
down_revision = '08fa6a844e0c'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.execute("ALTER TABLE users DROP CONSTRAINT users_pkey CASCADE")
    op.alter_column('users', 'id', type_=postgresql.UUID(as_uuid=True), postgresql_using="id::uuid")
    op.alter_column('leaderboards', 'user_id', type_=postgresql.UUID(as_uuid=True), postgresql_using="user_id::uuid")
    op.create_primary_key('users_pkey', 'users', ['id'])
    op.create_foreign_key( "leaderboards_user_id_fkey", "leaderboards", "users", ["user_id"], ["id"])
     # ### end Alembic commands ###

def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###