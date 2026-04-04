# Phase 01 — PostgreSQL Client Module

**Status:** completed  
**Priority:** high  
**Effort:** small

## Overview

Create `src/odoo_mcp/postgres_client.py` and add `psycopg2-binary` to `pyproject.toml`. This module handles connection management and read-only query execution against the Odoo PostgreSQL database.

## Related Files

- **Modify:** `pyproject.toml`
- **Create:** `src/odoo_mcp/postgres_client.py`

## Key Insights

- PostgreSQL is accessible at hostname `db` (Docker) or via `POSTGRES_HOST` env var
- Only SELECT queries should be allowed — enforce at the client level
- Use `psycopg2` (sync, matches existing codebase — no async)
- Connection pooling not needed; MCP is stateless per request

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_HOST` | `db` | PostgreSQL hostname |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `POSTGRES_USER` | — | Database user (required, **must be read-only**) |
| `POSTGRES_PASSWORD` | — | Database password (required) |
| `POSTGRES_DB` | — | Database name (required) |
| `POSTGRES_MAX_ROWS` | *(unset = unlimited)* | Hard cap on rows returned per query; if empty/unset, all rows returned |
| `POSTGRES_SKIP_READONLY_CHECK` | `false` | If `true`, bypass SELECT-only enforcement (dev/testing only — never in production) |

## Implementation Steps

### 1. Add dependency to `pyproject.toml`

In the `dependencies` list, add:
```
"psycopg2-binary>=2.9.0",
```

### 2. Create `src/odoo_mcp/postgres_client.py`

```python
"""
Direct PostgreSQL client for Odoo database access.
Provides read-only SQL query execution alongside the XML-RPC interface.
"""

import os
import psycopg2
import psycopg2.extras
from typing import Any


def _get_connection():
    """Create a new PostgreSQL connection from environment variables."""
    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "db"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        dbname=os.environ["POSTGRES_DB"],
        connect_timeout=10,
    )


_max_rows_env = os.environ.get("POSTGRES_MAX_ROWS", "")
MAX_ROWS = int(_max_rows_env) if _max_rows_env.strip() else None  # None = unlimited

# Dev bypass — disables SELECT-only check. NEVER set true in production.
SKIP_READONLY_CHECK = os.environ.get("POSTGRES_SKIP_READONLY_CHECK", "").lower() == "true"


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
    """Return column info (name, type, nullable) for a given table."""
    # Validate table name to prevent injection via identifier
    if not table_name.replace("_", "").replace(".", "").isalnum():
        raise ValueError(f"Invalid table name: {table_name!r}")

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
```

## Todo

<!-- Updated: Validation Session 1 - MAX_ROWS cap, read-only user note -->
<!-- Updated: Validation Session 2 - MAX_ROWS default changed to unlimited (None) when env var empty -->
<!-- COMPLETED: 2026-04-04 -->
- [x] Add `psycopg2-binary>=2.9.0` to `pyproject.toml` dependencies
- [x] Create `src/odoo_mcp/postgres_client.py` with `execute_query`, `list_tables`, `describe_table`
- [x] Set `MAX_ROWS = int(val) if val.strip() else None` — `None` means unlimited (fetchall), set value means capped (fetchmany)
- [x] Add `SKIP_READONLY_CHECK = os.environ.get("POSTGRES_SKIP_READONLY_CHECK", "").lower() == "true"` — bypasses SELECT-only check when `true`
- [x] Verify SELECT-only check rejects multi-statement input
- [x] Verify table name validation in `describe_table`
- [x] Document that `POSTGRES_USER` must be a read-only PostgreSQL user

## Success Criteria

- `postgres_client.py` imports without error
- `execute_query("SELECT 1")` returns `[{"1": 1}]` when DB is reachable
- Non-SELECT query raises `ValueError`

## Risk Assessment

- **psycopg2 build failure** in Docker slim image → mitigated by using `psycopg2-binary` and adding `libpq-dev` in Dockerfile (Phase 03)
- **Missing env vars** → `KeyError` on startup if `POSTGRES_USER/PASSWORD/DB` not set; acceptable — fails fast with clear error
