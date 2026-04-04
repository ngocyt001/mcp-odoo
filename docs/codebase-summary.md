# Codebase Summary — odoo-mcp

## Directory Structure

```
mcp-odoo/
├── src/odoo_mcp/
│   ├── __init__.py              (7 LOC)   Package initialization
│   ├── __main__.py              (54 LOC)  CLI entry point (odoo-mcp command)
│   ├── server.py                (665 LOC) MCP server, tools, resources, models
│   ├── odoo_client.py           (437 LOC) XML-RPC client + transport
│   └── postgres_client.py        (97 LOC)  PostgreSQL direct client (SELECT-only)
├── run_server.py                (90 LOC)  Alternative stdio server runner
├── pyproject.toml               (64 LOC)  Package config, dependencies
├── Dockerfile                   (47 LOC)  Python 3.10-slim container
├── README.md                    (220 LOC) User documentation
└── (project files)
    ├── .gitignore
    ├── LICENSE
    ├── CHANGELOG.md
    ├── odoo_config.json.example
    └── .github/workflows/publish.yml
```

**Total Python LOC:** ~1,250 | **Total Project LOC:** ~1,500+

---

## Core Modules

### 1. src/odoo_mcp/server.py (665 LOC)

**Purpose:** MCP server instance, tool/resource registration, Pydantic models, request handling.

**Key Classes (Odoo/Domain Models):**

| Class | Purpose | Fields |
|-------|---------|--------|
| `AppContext` | Lifespan context container | `odoo: OdooClient` |
| `DomainCondition` | Single domain clause | `field`, `operator`, `value`, `to_tuple()` |
| `SearchDomain` | Structured domain query | `conditions[]`, `to_domain_list()` |
| `EmployeeSearchResult` | Employee search row | `id`, `name` |
| `SearchEmployeeResponse` | Tool response wrapper | `success`, `result[]`, `error` |
| `Holiday` | Leave record | `display_name`, `start_datetime`, `stop_datetime`, `employee_id`, `name`, `state` |
| `SearchHolidaysResponse` | Holiday search response | `success`, `result[]`, `error` |

**Key Classes (PostgreSQL Response Models):**

| Class | Purpose | Fields |
|-------|---------|--------|
| `SqlQueryResponse` | SQL query result wrapper | `success`, `result[]`, `row_count`, `error` |
| `ListTablesResponse` | Table list response | `success`, `tables[]`, `error` |
| `DescribeTableResponse` | Column description | `success`, `columns[]`, `error` |

**Key Functions (Resources):**

| Function | Purpose | Signature |
|----------|---------|-----------|
| `get_models()` | Resource: list all models | `() → str` (JSON) |
| `get_model_info()` | Resource: model details + fields | `(model_name: str) → str` |
| `get_record()` | Resource: fetch by ID | `(model_name: str, record_id: str) → str` |
| `search_records_resource()` | Resource: domain search (limit 10) | `(model_name: str, domain: str) → str` |

**Key Functions (Odoo Tools):**

| Function | Purpose | Signature |
|----------|---------|-----------|
| `execute_method()` | Tool: arbitrary method execution | `(ctx, model, method, args, kwargs) → Dict` |
| `search_employee()` | Tool: hr.employee search | `(ctx, name, limit=20) → Dict` |
| `search_holidays()` | Tool: leave records in date range | `(ctx, start_date, end_date, employee_id) → Dict` |
| `search_tasks()` | Tool: project.task search (Odoo 18 compat) | `(ctx, project_id, stage_name, active_only, limit) → Dict` |
| `search_projects()` | Tool: project.project search | `(ctx, name, active_only, limit) → Dict` |

**Key Functions (PostgreSQL Tools):**

| Function | Purpose | Signature |
|----------|---------|-----------|
| `execute_sql()` | Tool: raw SELECT query | `(ctx, query: str, limit=100) → SqlQueryResponse` |
| `list_db_tables()` | Tool: list all tables | `(ctx) → ListTablesResponse` |
| `describe_db_table()` | Tool: column info for table | `(ctx, table_name: str) → DescribeTableResponse` |

**Domain Normalization Logic (execute_method):**
- Unwraps `[[domain]]` → `[domain]`
- Converts object format `{conditions:[...]}` to list format
- Parses JSON strings
- Handles `&`, `|`, `!` operators
- Normalizes `[field, op, val]` to `[[field, op, val]]`

**Context Injection:**
- `@mcp.tool(...)` decorated functions receive `ctx: Context` parameter
- Extract Odoo client: `ctx.request_context.lifespan_context.odoo`
- Resources access via `get_odoo_client()` singleton

**Type Safety:**
- All tools/resources fully type-hinted
- Pydantic validation on request/response
- Union types for flexible inputs (e.g., `Optional[Dict[str, Any]]`)

---

### 2. src/odoo_mcp/odoo_client.py (437 LOC)

**Purpose:** XML-RPC client for Odoo, transport layer, model introspection, method execution.

**Key Classes:**

| Class | Purpose | Lines |
|-------|---------|-------|
| `RedirectTransport` | Custom XML-RPC transport | ~120 |
| `OdooClient` | Main client class | ~320 |

**RedirectTransport Features:**
- Extends `xmlrpc.client.Transport`
- Handles HTTP redirects (301, 302, 303, 307, 308)
- Configurable timeout (default 10s)
- SSL verification toggle (`verify_ssl`)
- HTTP proxy support via env var `HTTP_PROXY`
- Logs connection attempts

**OdooClient Methods:**

| Method | Purpose | Args | Returns |
|--------|---------|------|---------|
| `__init__()` | Constructor | url, db, username, password, timeout, verify_ssl | — |
| `_connect()` | Authenticate + setup endpoints | — | None (sets `self.uid`) |
| `_execute()` | Raw XML-RPC wrapper | model, method, *args, **kwargs | RPC result |
| `execute_method()` | Public method executor | model, method, *args, **kwargs | RPC result |
| `get_models()` | List all ir.model records | — | `{model_names[], models_details{}}` |
| `get_model_info()` | Fetch ir.model record | model_name | `{name, model, ...}` |
| `get_model_fields()` | Fetch field definitions | model_name | `{field_name: {type, ...}, ...}` |
| `search_read()` | Search + read in one call | model, domain, fields, offset, limit, order | `[{record}, ...]` |
| `read_records()` | Fetch records by ID | model, ids, fields | `[{record}, ...]` |
| `search_count()` | Count matching records | model, domain | int |
| `name_search()` | Fuzzy search by name | model, name, operator, limit | `[[id, name], ...]` |
| `create_record()` | Create new record | model, values | int (new ID) |
| `write_records()` | Update records | model, ids, values | bool |
| `unlink_records()` | Delete records | model, ids | bool |

**Authentication:**
- Calls `common.authenticate(db, username, password, {})`
- Stores `uid` (user ID) for subsequent requests
- All RPC calls include: `db, uid, password, model, method, args, kwargs`

**Error Handling:**
- `socket.error`, `socket.timeout` → ConnectionError
- Authentication failures → ValueError
- Logs errors to stderr with context

**URL Normalization:**
- Auto-adds `http://` if no protocol specified
- Strips trailing slashes
- Parses hostname for logging

---

### 3. src/odoo_mcp/postgres_client.py (97 LOC)

**Purpose:** Direct PostgreSQL access for read-only SQL queries against the Odoo database.

**Security Model:**
1. **Primary Guard:** POSTGRES_USER env var must be a read-only database user (enforced at DB level)
2. **Secondary Guard:** All non-SELECT statements rejected at parse level
3. **Bypass Dev Mode:** `POSTGRES_SKIP_READONLY_CHECK=true` (dev/testing only — never production)

**Key Functions:**

| Function | Purpose | Signature |
|----------|---------|-----------|
| `_get_connection()` | Create psycopg2 connection from env vars | `() → psycopg2.connection` |
| `execute_query()` | Execute SELECT query, return row dicts | `(sql: str, params: tuple) → list[dict]` |
| `list_tables()` | List all user tables in public schema | `() → list[str]` |
| `describe_table()` | Get column definitions (name, type, nullable, default) | `(table_name: str) → list[dict]` |

**Configuration (Environment Variables):**
- `POSTGRES_HOST` — Database hostname (default: "db")
- `POSTGRES_PORT` — Database port (default: "5432")
- `POSTGRES_USER` — Database user (required; must have SELECT-only privileges)
- `POSTGRES_PASSWORD` — Database password (required)
- `POSTGRES_DB` — Database name (required)
- `POSTGRES_MAX_ROWS` — Hard cap on results per query (unset = unlimited)
- `POSTGRES_SKIP_READONLY_CHECK` — Bypass SELECT-only check (set to "true" for dev only)

**Row Limiting:**
- `MAX_ROWS` env var parsed at module load time
- If set, `execute_query()` uses `cursor.fetchmany(MAX_ROWS)` instead of `fetchall()`
- Unset/empty string → unlimited rows
- Applied per query execution

**Connection Details:**
- Uses `psycopg2.extras.RealDictCursor` for dict-like row access
- Connection timeout: 10 seconds
- Cursor closed in `try/finally` block; connection always closed

---

### 4. src/odoo_mcp/__main__.py (54 LOC)

**Purpose:** CLI entry point for `odoo-mcp` command.

**Behavior:**
1. Print startup banner to stderr
2. Log Python version
3. Log ODOO_* env vars (mask ODOO_PASSWORD)
4. Call `mcp.run()` to start FastMCP server
5. Handle KeyboardInterrupt gracefully
6. Return exit code 0 (success) or 1 (error)

**Key Points:**
- Imports `mcp` from `server.py` (FastMCP instance)
- All logs go to stderr (stdout reserved for MCP protocol)
- Expects `mcp.run()` method (from FastMCP)

---

### 5. run_server.py (90 LOC)

**Purpose:** Alternative standalone server runner with file logging.

**Features:**
- Setup logging to `logs/mcp_server_YYYYMMDD_HHMMSS.log`
- Configurable log levels (console INFO, file DEBUG)
- Async runner using `anyio`
- Uses `stdio_server()` transport (official MCP pattern)
- Calls `mcp._mcp_server.run()` with streams

**Logging:**
- Creates `logs/` directory if missing
- Formats: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
- Logs ODOO_* env vars (masked password)

---

### 6. pyproject.toml (64 LOC)

**Build Configuration:**
```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "odoo-mcp"
version = "0.0.3"
requires-python = ">=3.10"
```

**Dependencies:**
- `mcp>=0.1.1` — Model Context Protocol SDK
- `requests>=2.31.0` — HTTP library (for transport)
- `pypi-xmlrpc==2020.12.3` — Custom XML-RPC vendor
- `psycopg2-binary>=2.9.0` — PostgreSQL client library (for direct DB access)

**Optional Dev Dependencies:**
- `black`, `isort` — Formatters
- `mypy` — Type checker
- `ruff` — Linter
- `build`, `twine` — Package tools

**Tools:**
- Black: line-length 88, target Python 3.10
- isort: black profile, line-length 88
- mypy: strict mode (disallow_untyped_defs, disallow_incomplete_defs)

**Package Config:**
- Entry point: `odoo-mcp = "odoo_mcp.__main__:main"`
- Source dir: `src/`
- Packages: `["odoo_mcp"]`

---

### 7. Dockerfile (47 LOC)

**Base:** Python 3.10-slim

**Setup:**
1. Install system packages: gcc, procps, libpq-dev (for psycopg2)
2. Copy source code to `/app`
3. Create `/app/logs` directory (mode 777)
4. Install `mcp[cli]` + `odoo-mcp` package (editable)
5. Set environment variables with defaults
6. Make `run_server.py` executable
7. Set `PYTHONUNBUFFERED=1`

**Entry Point:** `python run_server.py`

**Env Vars (Odoo XML-RPC, Defaults):**
```
ODOO_URL=""
ODOO_DB=""
ODOO_USERNAME=""
ODOO_PASSWORD=""
ODOO_TIMEOUT="30"
ODOO_VERIFY_SSL="1"
DEBUG="0"
```

**Env Vars (PostgreSQL Direct Access, Defaults):**
```
POSTGRES_HOST="db"
POSTGRES_PORT="5432"
POSTGRES_USER=""
POSTGRES_PASSWORD=""
POSTGRES_DB=""
POSTGRES_MAX_ROWS=""
POSTGRES_SKIP_READONLY_CHECK="false"
```

---

## Configuration Loading

### Priority Order (Highest → Lowest)
1. Environment variables (`ODOO_*`)
2. Config file: `~/.config/odoo/config.json`
3. Config file: `~/.odoo_config.json`
4. Config file: `odoo_config.json` (local)

### Config File Format
```json
{
  "url": "https://your-odoo-instance.com",
  "db": "your-database-name",
  "username": "your-username",
  "password": "your-password-or-api-key",
  "timeout": 30,
  "verify_ssl": true
}
```

### Environment Variables (Odoo XML-RPC)
| Var | Type | Default | Note |
|-----|------|---------|------|
| `ODOO_URL` | string | — | Required |
| `ODOO_DB` | string | — | Required |
| `ODOO_USERNAME` | string | — | Required |
| `ODOO_PASSWORD` | string | — | API key recommended |
| `ODOO_TIMEOUT` | int | 30 | Seconds |
| `ODOO_VERIFY_SSL` | bool | true | "1"/"0" or "true"/"false" |
| `HTTP_PROXY` | string | — | For corporate proxies |

### Environment Variables (PostgreSQL Direct Access)
| Var | Type | Default | Note |
|-----|------|---------|------|
| `POSTGRES_HOST` | string | "db" | Database hostname |
| `POSTGRES_PORT` | int | 5432 | Database port |
| `POSTGRES_USER` | string | — | Required; must be read-only user |
| `POSTGRES_PASSWORD` | string | — | Required |
| `POSTGRES_DB` | string | — | Required |
| `POSTGRES_MAX_ROWS` | int | unset (unlimited) | Hard cap on rows per query |
| `POSTGRES_SKIP_READONLY_CHECK` | bool | false | Bypass SELECT check (dev only) |

---

## Type Hints & Pydantic Usage

**Module Coverage:**
- `server.py`: 100% type hints (tools, resources, models)
- `odoo_client.py`: 95% type hints (mixed legacy patterns)
- `__main__.py`: 100% type hints
- `run_server.py`: ~80% type hints (async patterns less strict)

**Pydantic Patterns:**
- `BaseModel` for request/response schemas
- `Field(description="...")` for OpenAPI-like documentation
- `Optional[T]` for nullable fields
- `Union[int, str]` for flexible types
- `List[Dict[str, Any]]` for Odoo domain structures

**Type Checker:** mypy with strict flags:
- `disallow_untyped_defs = true`
- `disallow_incomplete_defs = true`
- `warn_return_any = true`

---

## Error Handling Patterns

**try/except Blocks:**
1. Resource handlers wrap XML-RPC calls in try/except
2. Return JSON error format: `{"error": "message"}`
3. Tool handlers catch exceptions and return error dict
4. Connection errors mapped to specific exception types

**Error Types:**
- `ConnectionError` — Network/socket issues
- `ValueError` — Authentication failures, invalid input
- `Exception` — Catch-all for Odoo RPC errors

**Logging:**
- All errors logged to stderr
- Password values masked in logs
- Stack traces printed in debug mode

---

## File Size Management

| File | LOC | Status |
|------|-----|--------|
| server.py | 665 | ✓ Focused (MCP layer + models + PostgreSQL tools) |
| odoo_client.py | 437 | ✓ Focused (XML-RPC client) |
| postgres_client.py | 97 | ✓ Lightweight (PostgreSQL client) |
| run_server.py | 90 | ✓ Lightweight |
| __main__.py | 54 | ✓ Minimal |
| __init__.py | 7 | ✓ Package init only |

**Modularization Strategy:**
- XML-RPC transport isolated in `RedirectTransport` class
- Pydantic models grouped by domain (employees, holidays, tasks)
- Tools registered via decorators (no separate registry file)
- Client methods organized by concern (read, search, create, etc.)

---

## Dependencies & Versions

| Package | Version | Purpose |
|---------|---------|---------|
| mcp | >=0.1.1 | MCP SDK, FastMCP |
| requests | >=2.31.0 | HTTP client (XML-RPC transport) |
| pypi-xmlrpc | 2020.12.3 | XML-RPC codec (vendored) |
| psycopg2-binary | >=2.9.0 | PostgreSQL client (direct DB access) |
| python | >=3.10 | Runtime |

**Technical Notes:**
- **pypi-xmlrpc**: Handles edge cases in Odoo's XML-RPC implementation; better than stdlib `xmlrpc` for production
- **psycopg2-binary**: Includes PostgreSQL libpq client library; no separate system installation required

---

## PostgreSQL Direct Access (New Feature)

**Overview:** Complements XML-RPC with read-only SQL access for complex queries and data not exposed via Odoo API.

**Security Layers:**
1. **Database-Level** — POSTGRES_USER must be a read-only database user (enforced at PostgreSQL level)
2. **Parse-Level** — All non-SELECT statements rejected before execution
3. **Row-Level** — Optional hard cap via POSTGRES_MAX_ROWS (per query)
4. **Dev Override** — POSTGRES_SKIP_READONLY_CHECK=true (development/testing only, never production)

**Use Cases:**
- Complex JOIN queries across multiple tables
- Aggregations (COUNT, SUM, AVG) not available via XML-RPC
- Performance optimization for bulk data retrieval
- Debugging/auditing direct database state

**Available Tools:**
- `execute_sql()` — Run arbitrary SELECT with optional row limit
- `list_db_tables()` — Discover all user tables in public schema
- `describe_db_table()` — Inspect column definitions (type, nullable, default)

**Connection Model:**
- New connection per query (simplifies state management)
- Connection timeout: 10 seconds
- Cursor factory: `RealDictCursor` (dict-like row access)
- Results: List of dicts, one per row

**Limitations:**
- SELECT-only (by design; bypassable for testing only)
- No prepared statement caching (fresh connection per query)
- No streaming; all rows fetched into memory
- No transaction support (single-query operations)

---

## Known Limitations

**Odoo XML-RPC:**
1. **No Async Client:** XML-RPC calls are synchronous (thread-blocking)
2. **Odoo 18 Breaking Changes:** `user_ids` (many2many) vs `user_id` (many2one)
3. **Date Fields:** No automatic date serialization, pass strings YYYY-MM-DD
4. **Binary Fields:** Not supported (files, images)
5. **Relations:** Many2many/many2one returned as IDs, not full objects
6. **Timeout:** Global per-client, not per-request
7. **hr.leave Module:** `search_holidays()` tool requires `hr_holidays` module installed; gracefully reports error if missing

**PostgreSQL Direct Access:**
1. **SELECT-Only:** Write operations blocked at parse level
2. **No Streaming:** All rows loaded into memory
3. **Single-Query:** No transaction support (each query is isolated)
4. **Row Capping:** Optional hard limit via POSTGRES_MAX_ROWS env var

---

## Testing Strategy

No automated test suite included. Testing approach:
1. Manual integration tests against Odoo instance
2. Docker verification (build + run checks)
3. Type checking via `mypy` (CI/CD via GitHub Actions)
4. Code formatting (black, isort) in dev workflow

---

## Performance Characteristics

| Operation | Latency | Notes |
|-----------|---------|-------|
| `get_models()` | 0.5-2s | Queries ir.model (full list) |
| `search_employee()` | 0.1-0.5s | Uses name_search (indexed) |
| `search_records_resource()` | 0.2-1s | Depends on domain complexity |
| `execute_method()` | 0.1-5s+ | Varies by method |
| Auth handshake | 0.3-1s | One-time on startup |

**Bottlenecks:**
- Network latency to Odoo server dominates
- Large domain searches on unindexed fields slow
- Timeout default (30s) may need adjustment for Odoo 18+

