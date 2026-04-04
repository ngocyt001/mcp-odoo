# Documentation Update: PostgreSQL Direct Access Feature

**Date:** 2026-04-04 | **Updated File:** `/Users/ngoctran/Documents/Tech/mcp-odoo/docs/codebase-summary.md`

---

## Summary

Updated `codebase-summary.md` to document the new PostgreSQL direct access feature alongside existing Odoo XML-RPC functionality. All code references verified against actual implementation.

**File Size:** 509 LOC (well within 800 LOC limit)

---

## Changes Made

### 1. Directory Structure (Updated)
- Added `postgres_client.py` (97 LOC) entry
- Updated `server.py` from 577 → 665 LOC (new PostgreSQL tools)
- Updated `pyproject.toml` from 62 → 64 LOC (psycopg2-binary dependency)
- Updated `Dockerfile` from 36 → 47 LOC (libpq-dev, PostgreSQL env vars)
- Updated `README.md` from 194 → 220 LOC (PostgreSQL documentation)
- **Total Python LOC:** ~1,165 → ~1,250
- **Total Project LOC:** ~1,400+ → ~1,500+

### 2. Core Modules Section (Enhanced)
- **Section 1 (server.py):** Separated response models into two tables:
  - Odoo/Domain models (unchanged existing classes)
  - PostgreSQL response models (`SqlQueryResponse`, `ListTablesResponse`, `DescribeTableResponse`)
- Separated tool functions into two sections:
  - Odoo tools (existing: `execute_method`, `search_employee`, `search_holidays`, `search_tasks`, `search_projects`)
  - PostgreSQL tools (new: `execute_sql`, `list_db_tables`, `describe_db_table`)

- **Section 3 (postgres_client.py — NEW):** Comprehensive module documentation
  - Security model: 3-layer defense (DB user, parse-level SELECT check, row limit cap, dev bypass)
  - Functions: `_get_connection()`, `execute_query()`, `list_tables()`, `describe_table()`
  - Configuration: All 7 environment variables documented
  - Row limiting mechanism (POSTGRES_MAX_ROWS env var)
  - Connection details (psycopg2 setup, cursor type, timeout)

- **Renumbered subsequent sections:** __main__.py (4→5), run_server.py (5→6), pyproject.toml (5→7), Dockerfile (6→7)

### 3. Dependencies Section (Updated)
- Added `psycopg2-binary>=2.9.0` to dependencies table
- Added technical note: "Includes PostgreSQL libpq client library; no separate system installation required"

### 4. Configuration Loading Section (Split)
- **Odoo XML-RPC variables** — Kept existing table unchanged
- **PostgreSQL variables** — New table with 7 environment variables:
  - `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
  - `POSTGRES_MAX_ROWS`, `POSTGRES_SKIP_READONLY_CHECK`

### 5. Dockerfile Documentation (Updated)
- Added libpq-dev system dependency
- Split Env Vars into two sections:
  - Odoo XML-RPC (existing: ODOO_URL, ODOO_DB, etc.)
  - PostgreSQL Direct Access (new: POSTGRES_HOST, POSTGRES_PORT, etc.)

### 6. File Size Management Table (Updated)
- Added `postgres_client.py` (97 LOC) row
- Updated `server.py` note: now includes "PostgreSQL tools"

### 7. PostgreSQL Direct Access Section (NEW)
Comprehensive feature overview (35 LOC):
- **Overview:** Complements XML-RPC, read-only SQL access for complex queries
- **Security Layers:** 4-tier security model (database-level, parse-level, row-level, dev override)
- **Use Cases:** JOINs, aggregations, bulk retrieval, debugging
- **Available Tools:** `execute_sql()`, `list_db_tables()`, `describe_db_table()`
- **Connection Model:** Fresh connection per query, 10s timeout, RealDictCursor
- **Limitations:** SELECT-only, no statement caching, no streaming, no transactions

### 8. Known Limitations (Reorganized)
- Split into two subsections: **Odoo XML-RPC** and **PostgreSQL Direct Access**
- Added new Odoo limitation: hr.leave module graceful error handling
- Added 4 PostgreSQL-specific limitations

---

## Verification Checklist

- [x] Read all modified code files (`postgres_client.py`, `server.py`, `pyproject.toml`, `Dockerfile`, `README.md`)
- [x] Verified all function signatures match actual implementation
- [x] Confirmed all environment variable names (POSTGRES_* prefix)
- [x] Verified Pydantic model names and fields
- [x] Checked connection defaults (POSTGRES_HOST="db", POSTGRES_PORT="5432")
- [x] Confirmed security model (SELECT-only + env var bypass)
- [x] All line counts verified against actual files
- [x] File paths match actual module structure
- [x] No stale/TODO markers in documentation
- [x] File size within limit: 509 LOC << 800 LOC

---

## Cross-Reference Consistency

**Related docs that reference this content:**
- `README.md` — "PostgreSQL Direct Access" section (matches feature overview)
- `system-architecture.md` — May need review for data flow diagrams
- `deployment-guide.md` — May need PostgreSQL environment variable examples

---

## Token Efficiency Notes

- Utilized Grep tool to locate new code patterns quickly (execute_sql, list_db_tables, describe_db_table)
- Batch Read calls to gather context (postgres_client.py + server.py + pyproject.toml + Dockerfile in one block)
- Focused Edit operations: no rewrites, only targeted inserts/updates
- Final file size: 509 LOC (balanced, no splitting needed)

---

## Status

**DONE** — Documentation successfully updated and verified.

All code examples, function signatures, environment variables, and architectural descriptions reflect the actual implementation as of git commit `be69978` (feat: add Odoo 18 compatible search_tasks and search_projects tools).
