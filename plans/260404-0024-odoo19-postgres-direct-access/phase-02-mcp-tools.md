# Phase 02 — MCP Tools for Direct SQL Access

**Status:** completed  
**Priority:** high  
**Effort:** small  
**Depends on:** Phase 01

## Overview

Add 3 new MCP tools to `server.py` that expose PostgreSQL direct access:
- `execute_sql` — run an arbitrary SELECT query
- `list_db_tables` — list all tables in the Odoo database
- `describe_db_table` — get column structure of a specific table

## Related Files

- **Modify:** `src/odoo_mcp/server.py`

## Implementation Steps

### 1. Add import at top of `server.py`

After the existing imports, add:
```python
from . import postgres_client
```

### 2. Add Pydantic response models (after existing models, before tools section)

```python
class SqlQueryResponse(BaseModel):
    success: bool
    result: Optional[List[Dict[str, Any]]] = None
    row_count: Optional[int] = None
    error: Optional[str] = None


class ListTablesResponse(BaseModel):
    success: bool
    tables: Optional[List[str]] = None
    error: Optional[str] = None


class DescribeTableResponse(BaseModel):
    success: bool
    columns: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None
```

### 3. Add 3 new MCP tools at the bottom of `server.py`

```python
# ── Direct PostgreSQL access tools ──────────────────────────────────────────
# Bypasses XML-RPC for complex queries or data not exposed via Odoo API.
# SECURITY: Only SELECT queries are permitted (enforced in postgres_client).

@mcp.tool(description="Execute a read-only SQL SELECT query directly on the Odoo PostgreSQL database.")
def execute_sql(
    ctx: Context,
    query: str,
    limit: int = 100,
) -> SqlQueryResponse:
    """
    Run a raw SQL SELECT query on the Odoo database.

    Parameters:
        query: A valid SQL SELECT statement.
        limit: Max rows to return (appended as LIMIT if not already present, default 100).
    """
    try:
        sql = query.strip()
        upper = sql.upper()
        if "LIMIT" not in upper:
            sql = f"{sql} LIMIT {limit}"
        rows = postgres_client.execute_query(sql)
        return SqlQueryResponse(success=True, result=rows, row_count=len(rows))
    except Exception as e:
        return SqlQueryResponse(success=False, error=str(e))


@mcp.tool(description="List all tables in the Odoo PostgreSQL database.")
def list_db_tables(ctx: Context) -> ListTablesResponse:
    """Return all user table names in the public schema."""
    try:
        tables = postgres_client.list_tables()
        return ListTablesResponse(success=True, tables=tables)
    except Exception as e:
        return ListTablesResponse(success=False, error=str(e))


@mcp.tool(description="Describe the columns of a table in the Odoo PostgreSQL database.")
def describe_db_table(ctx: Context, table_name: str) -> DescribeTableResponse:
    """
    Get column definitions (name, type, nullable, default) for a table.

    Parameters:
        table_name: The table name (e.g., 'res_partner').
    """
    try:
        columns = postgres_client.describe_table(table_name)
        return DescribeTableResponse(success=True, columns=columns)
    except Exception as e:
        return DescribeTableResponse(success=False, error=str(e))
```

## Todo

<!-- COMPLETED: 2026-04-04 -->
- [x] Add `from . import postgres_client` import to `server.py`
- [x] Add `SqlQueryResponse`, `ListTablesResponse`, `DescribeTableResponse` Pydantic models
- [x] Add `execute_sql` tool
- [x] Add `list_db_tables` tool
- [x] Add `describe_db_table` tool

## Success Criteria

- All 3 tools appear in MCP tool list
- `list_db_tables` returns Odoo table names (e.g., `res_partner`, `sale_order`)
- `execute_sql("SELECT id, name FROM res_partner LIMIT 5")` returns rows
- `execute_sql("DELETE FROM res_partner")` returns error (not SELECT)

## Known Limitations

<!-- Updated: Validation Session 3 - task_count is XML-RPC only, not in DB schema -->

- **`task_count` is not queryable via SQL.** It is a computed field in Odoo's ORM, not stored in `project_project`. The `execute_sql` and `describe_db_table` tools will not return it. Users needing project task counts via SQL must use: `SELECT COUNT(*) FROM project_task WHERE project_id = <id> AND active = true`

## Security Notes

<!-- Updated: Validation Session 1 - read-only user is primary guard -->
- **Primary guard:** `POSTGRES_USER` must be a read-only PostgreSQL user (SELECT-only grants). This is enforced at the DB level — no string check can replace it.
- **Secondary guard:** `postgres_client.execute_query` rejects non-SELECT statements — cannot be bypassed from the tool layer
- **Row cap:** `MAX_ROWS` in `postgres_client` limits rows fetched; `limit` param in `execute_sql` adds LIMIT clause before that cap
- Table name in `describe_db_table` is validated (alphanumeric + `_` + `.` only)
