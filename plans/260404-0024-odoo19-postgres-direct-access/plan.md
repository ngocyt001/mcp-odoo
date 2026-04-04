---
title: Odoo 19 Support — PostgreSQL Direct Access + XML-RPC Compat
status: completed
priority: high
created: 2026-04-04
blockedBy: []
blocks: []
---

# Odoo 19 Support — PostgreSQL Direct Access + XML-RPC Compat

## Overview

Two-track update to make mcp-odoo support Odoo 19 (currently targets Odoo 16):

1. **XML-RPC compatibility** — fix breaking changes in API methods, auth, and model fields between Odoo 16 and 19
2. **PostgreSQL direct access** — add SQL-level query tools via psycopg2 alongside the existing XML-RPC interface

**Context:**
- MCP is distributed to many users who connect to their own Odoo databases
- Credentials provided via env vars at startup (same pattern as existing `ODOO_URL`/`ODOO_DB`)
- PostgreSQL access requires a **read-only DB user** (defense in depth; string-check alone is insufficient)
- `MAX_ROWS` enforced in the client layer (default 1000), not just at the tool layer

## Phases

| # | Phase | Status | File |
|---|-------|--------|------|
| 1 | Add psycopg2 dependency & PostgreSQL client module | completed | [phase-01](phase-01-postgres-client.md) |
| 2 | Add MCP tools for direct SQL access | completed | [phase-02](phase-02-mcp-tools.md) |
| 3 | Update Dockerfile & environment config | completed | [phase-03](phase-03-docker-config.md) |
| 4 | Odoo 16 → 19 XML-RPC compatibility fixes | completed | [phase-04](phase-04-xmlrpc-odoo19-compat.md) |

## Key Dependencies

- `psycopg2-binary` Python package
- `libpq-dev` system package (in Dockerfile)
- Docker `odoo_default` network connectivity
- Read-only PostgreSQL user created by the end-user (documented in README)

## Files Modified

- `pyproject.toml` — add `psycopg2-binary` dependency
- `src/odoo_mcp/postgres_client.py` — new module (PostgreSQL client)
- `src/odoo_mcp/server.py` — add 3 new MCP tools + Odoo 19 XML-RPC fixes
- `Dockerfile` — install `libpq-dev`, include new env vars
- `README.md` — add PostgreSQL Direct Access section (setup, env vars, compose example, dev bypass note)

## Validation Log

### Session 1 — 2026-04-04
**Trigger:** Pre-implementation validation interview  
**Questions asked:** 5

#### Questions & Answers

1. **[Scope]** Does "support Odoo 19" mean adding PostgreSQL access only, or also updating XML-RPC compatibility?
   - Options: Both needed | PostgreSQL only | XML-RPC compat only
   - **Answer:** Both needed
   - **Rationale:** Existing XML-RPC tools (search_tasks, search_projects, etc.) have breaking changes between Odoo 16 and 19. Plan was missing a full phase for this.

2. **[Architecture]** How should multi-user credential configuration work?
   - Options: Env vars at startup | Claude Desktop config | Optional/graceful degradation
   - **Answer:** Env vars at startup
   - **Rationale:** Consistent with existing `ODOO_URL`/`ODOO_DB` pattern. Users configure once in their shell/compose file.

3. **[Security]** Should SELECT enforcement go beyond string prefix check?
   - Options: Read-only DB user | Keep string check only | Semicolon/comment detection
   - **Answer:** Read-only DB user (defense in depth)
   - **Rationale:** String-check alone bypassable via `SELECT 1; DELETE ...`. Require users to create a read-only PG user; document in README.

4. **[Safety]** Should MAX_ROWS be enforced in the client layer?
   - Options: Yes — enforce in postgres_client | No — tool layer is enough
   - **Answer:** Yes — enforce max rows in client
   - **Rationale:** Prevents accidental full-table dumps from any caller, not just the MCP tool layer.

5. **[Odoo 19]** What breaking changes between Odoo 16 and 19 affect this MCP?
   - Options: API method changes | Auth changes | Model structure changes | Not sure
   - **Answer:** API method changes + Auth changes + Model structure changes
   - **Rationale:** All three tracks need investigation and fixes. Adds Phase 04.

#### Confirmed Decisions
- Scope expanded: add Phase 04 for XML-RPC Odoo 19 compatibility
- Security: read-only PG user required; document in README/phase-03
- Safety: `MAX_ROWS` cap added to `postgres_client.execute_query`
- Config: env vars at startup (no change to approach, confirmed)

#### Action Items
- [ ] Add Phase 04 file: `phase-04-xmlrpc-odoo19-compat.md`
- [ ] Update phase-01 to add `MAX_ROWS` enforcement in `execute_query`
- [ ] Update phase-03 to add read-only DB user creation steps + README note
- [ ] Update phase-02 security notes to reference read-only user requirement

#### Impact on Phases
- Phase 01: Add `MAX_ROWS` cap to `execute_query`; add `POSTGRES_MAX_ROWS` env var
- Phase 02: Update security notes — SELECT check is secondary; primary guard is read-only user
- Phase 03: Add read-only PG user creation SQL snippet + README instruction
- Phase 04: New — Odoo 16→19 XML-RPC compat fixes (API methods, auth, model fields)

### Session 2 — 2026-04-04
**Trigger:** User clarification on MAX_ROWS default behavior  
**Questions asked:** 1

#### Questions & Answers

1. **[Assumptions]** What should happen when `POSTGRES_MAX_ROWS` env var is empty or unset?
   - Options: Default to 1000 | Return all rows (unlimited) | Raise error if not set
   - **Answer:** Return all rows (unlimited) — `None` cap means `fetchall()`
   - **Rationale:** User explicitly specified: empty env var = show full results. Operators who want a cap must set the variable explicitly.

#### Confirmed Decisions
- `POSTGRES_MAX_ROWS` unset/empty → `MAX_ROWS = None` → `fetchall()` (no cap)
- `POSTGRES_MAX_ROWS` set to integer → `fetchmany(MAX_ROWS)` (capped)

#### Action Items
- [x] Update phase-01 implementation snippet: `MAX_ROWS = int(val) if val.strip() else None`
- [x] Update phase-01 env var table: default = *(unset = unlimited)*

#### Impact on Phases
- Phase 01: `MAX_ROWS` default changed from `1000` to `None`; `fetchall()` used when unset

### Session 3 — 2026-04-04
**Trigger:** Live DB schema inspection (Odoo 19 PostgreSQL 15 via Docker)  
**Questions asked:** 4

#### Questions & Answers

1. **[Architecture]** `project_project.name` is `jsonb` (translated field) in Odoo 19 DB — how should XML-RPC search_projects handle this?
   - Options: Return raw jsonb | Extract lang string | Let Odoo handle it
   - **Answer:** Let Odoo handle it — verify XML-RPC returns resolved string before changing code
   - **Rationale:** XML-RPC may already resolve translations server-side. Don't add post-processing until a real failure is observed.

2. **[Assumptions]** `task_count` is in `_PROJECT_FIELDS` but is NOT a stored column in `project_project` DB schema (computed only).
   - Options: Keep via XML-RPC only | Remove from fields list | Add SQL note in describe_db_table
   - **Answer:** Keep via XML-RPC only — stays in `_PROJECT_FIELDS`; document that SQL users must join `project_task` manually
   - **Rationale:** XML-RPC computes it fine. SQL direct access doesn't support computed fields — document as a known limitation.

3. **[Risk]** `hr_leave` table doesn't exist in the Odoo 19 DB — time-off module not installed. `search_holidays` calls `hr.leave.report.calendar`.
   - Options: Graceful error | Remove the tool | Skip (already returns success=False)
   - **Answer:** Graceful error — catch XML-RPC error and return `success=False` with message "hr.leave module not installed"
   - **Rationale:** Clear error message is better than a raw XML-RPC fault. The tool stays in for users who do have the module.
   - **Update (DB re-check after all modules activated):** `hr_leave` and `hr_leave_report_calendar` NOW EXIST. Fields used by `search_holidays` (`start_datetime`, `stop_datetime`, `employee_id`) match schema exactly — tool likely works in Odoo 19 with no changes. Graceful error handling still valid for users without the module installed.

4. **[Security]** Should `POSTGRES_SKIP_READONLY_CHECK=true` still block multi-statement SQL (semicolons)?
   - Options: No extra check | Warn on semicolons | Always reject multi-statements
   - **Answer:** No extra check — YAGNI; flag is explicitly for dev/testing, already documented as dangerous
   - **Rationale:** Adding safety checks on a flag whose entire purpose is to bypass safety is contradictory. Trust the operator.

#### Confirmed Decisions
- `project_project.name` jsonb: verify XML-RPC behavior first, no code change until failure observed
- `task_count`: stays in XML-RPC field list; SQL access limitation documented in Phase 02
- `search_holidays`: add specific catch for module-not-installed XML-RPC fault → clear error message; field names in Odoo 19 are confirmed compatible (start_datetime, stop_datetime, employee_id all present)
- `SKIP_READONLY_CHECK`: no semicolon/multi-statement guard added

#### Action Items
- [ ] Phase 04: Add investigation step — verify XML-RPC returns resolved name string vs raw dict for `project_project.name`
- [ ] Phase 04: Add graceful error handling for `hr.leave.report.calendar` when module not installed
- [ ] Phase 02: Add note that `task_count` is a computed field not in DB schema — SQL users must `SELECT COUNT(*) FROM project_task WHERE project_id = X`

#### Impact on Phases
- Phase 04: Two additions — (a) verify translated `name` field behavior, (b) catch `hr.leave` module-not-installed fault with clear message
- Phase 02: Add documentation note on `task_count` being XML-RPC-only (not SQL-queryable)
