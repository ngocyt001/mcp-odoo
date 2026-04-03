"""
Direct PostgreSQL client for Odoo database access.
Provides read-only SQL query execution alongside the XML-RPC interface.
"""

import os
from typing import Any

import psycopg2
import psycopg2.extras


def _get_connection():
    """Create a new PostgreSQL connection from environment variables."""
    try:
        user = os.environ["POSTGRES_USER"]
        password = os.environ["POSTGRES_PASSWORD"]
        dbname = os.environ["POSTGRES_DB"]
    except KeyError as e:
        raise EnvironmentError(
            f"Required environment variable {e} is not set. "
            "Set POSTGRES_USER, POSTGRES_PASSWORD, and POSTGRES_DB to enable PostgreSQL access."
        ) from e

    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "db"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        user=user,
        password=password,
        dbname=dbname,
        connect_timeout=10,
    )


_max_rows_env = os.environ.get("POSTGRES_MAX_ROWS", "")
MAX_ROWS = int(_max_rows_env) if _max_rows_env.strip() else None  # None = unlimited

# Dev bypass — disables SELECT-only check. NEVER set true in production.
SKIP_READONLY_CHECK = (
    os.environ.get("POSTGRES_SKIP_READONLY_CHECK", "").lower() == "true"
)


def execute_query(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    """
    Execute a SQL query (SELECT-only by default).
    Set POSTGRES_SKIP_READONLY_CHECK=true to allow all SQL (dev/testing only).
    Returns list of row dicts; capped at MAX_ROWS if set, otherwise all rows.

    Primary security: POSTGRES_USER must be a read-only DB user.
    Secondary guard: reject non-SELECT statements at parse level.
    """
    if not SKIP_READONLY_CHECK:
        normalized = sql.strip().upper()
        if not normalized.startswith("SELECT"):
            raise ValueError("Only SELECT queries are permitted for security reasons.")

    conn = _get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchmany(MAX_ROWS) if MAX_ROWS is not None else cur.fetchall()
            return [dict(row) for row in rows]
    finally:
        conn.close()


def list_tables() -> list[str]:
    """Return all user table names in the public schema."""
    rows = execute_query(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
    )
    return [row["tablename"] for row in rows]


def describe_table(table_name: str) -> list[dict[str, Any]]:
    """Return column info (name, type, nullable, default) for a given table."""
    # Validate table name to prevent injection via identifier.
    # Reject schema-qualified names (e.g. "public.res_partner") — information_schema
    # lookup uses table_name column only, so a dot-qualified name returns zero rows silently.
    if not table_name.replace("_", "").isalnum():
        raise ValueError(
            f"Invalid table name: {table_name!r}. "
            "Use the bare table name (e.g. 'res_partner'), not schema-qualified."
        )

    rows = execute_query(
        """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
        """,
        (table_name,),
    )
    return rows
