"""Add Row Level Security policies for multi-tenant isolation

Revision ID: 003
Revises: 002
Create Date: 2026-03-06

Wichtig: RLS isoliert Daten nach workspace_id.
Jeder App-Request setzt vor DB-Zugriffen:
    SET LOCAL app.workspace_id = '<uuid>';
Migrationen laufen als Table-Owner und umgehen RLS automatisch.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tabellen die RLS-Schutz erhalten
RLS_TABLES = ["meetings", "action_items", "embeddings"]


def upgrade() -> None:
    for table in RLS_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        # FORCE RLS gilt auch für den Table-Owner (Ausnahme: Superuser)
        # Für Migrationen ist das OK da Alembic DDL ausführt, kein SELECT/UPDATE
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

        # missing_ok=true: gibt NULL zurück wenn app.workspace_id nicht gesetzt ist
        # (statt einen Error zu werfen) — wichtig für health checks und ähnliches
        op.execute(f"""
            CREATE POLICY workspace_isolation ON {table}
            USING (
                workspace_id = current_setting('app.workspace_id', true)::uuid
            )
        """)


def downgrade() -> None:
    for table in RLS_TABLES:
        op.execute(f"DROP POLICY IF EXISTS workspace_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
