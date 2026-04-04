# Phase 03 — Dockerfile & Environment Config

**Status:** completed  
**Priority:** high  
**Effort:** small  
**Depends on:** Phase 01

## Overview

Update `Dockerfile` to install `libpq-dev` (required for psycopg2) and declare the 5 new PostgreSQL environment variables.

## Related Files

- **Modify:** `Dockerfile`

## Implementation Steps

### 1. Add `libpq-dev` to the apt-get install block

Current:
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    procps \
    && rm -rf /var/lib/apt/lists/*
```

Updated:
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    procps \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*
```

### 2. Add PostgreSQL env vars after the existing ODOO env vars

```dockerfile
# PostgreSQL direct access (Odoo database)
ENV POSTGRES_HOST="db"
ENV POSTGRES_PORT="5432"
ENV POSTGRES_USER=""
ENV POSTGRES_PASSWORD=""
ENV POSTGRES_DB=""
```

## Read-Only PostgreSQL User (Required)

<!-- Updated: Validation Session 1 - read-only user is primary security control -->
Users **must** create a read-only PostgreSQL user before connecting via this MCP. Add to README:

```sql
-- Run once as the Odoo DB superuser (e.g. psql -U odoo odoo)
CREATE USER mcp_readonly WITH PASSWORD 'choose-a-strong-password';
GRANT CONNECT ON DATABASE odoo TO mcp_readonly;
GRANT USAGE ON SCHEMA public TO mcp_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO mcp_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO mcp_readonly;
```

Then set `POSTGRES_USER=mcp_readonly` and `POSTGRES_PASSWORD=<chosen>` in the MCP environment.

## Docker-Compose / Runtime Config

When running the MCP container in the `odoo_default` network, pass the credentials at runtime:

```yaml
environment:
  # existing Odoo XML-RPC vars
  ODOO_URL: http://odoo:8069
  ODOO_DB: odoo
  ODOO_USERNAME: admin
  ODOO_PASSWORD: admin
  # new PostgreSQL direct access vars
  POSTGRES_HOST: db
  POSTGRES_PORT: "5432"
  POSTGRES_USER: odoo
  POSTGRES_PASSWORD: odoo_secret
  POSTGRES_DB: odoo
```

For local development (outside Docker), expose the port in the compose file:
```yaml
services:
  db:
    ports:
      - "5432:5432"
```
Then use `POSTGRES_HOST=localhost`.

## README Updates (Required)

Add a **"PostgreSQL Direct Access"** section to `README.md` covering:

1. **Prerequisites** — read-only user creation SQL (see snippet above)
2. **Environment variables table** — all `POSTGRES_*` vars with defaults and descriptions
3. **Docker Compose example** — full env block (XML-RPC + PostgreSQL vars)
4. **Dev/testing note** — `POSTGRES_SKIP_READONLY_CHECK=true` bypasses SELECT-only check; never use in production
5. **Odoo 19 note** — XML-RPC compat changes if applicable

## Todo

<!-- Updated: Validation Session 1 - add read-only user, POSTGRES_MAX_ROWS -->
<!-- COMPLETED: 2026-04-04 -->
- [x] Add `libpq-dev` to `apt-get install` in `Dockerfile`
- [x] Add 6 PostgreSQL `ENV` declarations to `Dockerfile` (5 connection vars + `POSTGRES_MAX_ROWS`)
- [x] Update `README.md` — add "PostgreSQL Direct Access" section (setup, env vars, compose example, dev bypass note)
- [x] Rebuild Docker image after changes: `docker build -t odoo-mcp .`
- [x] Verify psycopg2 installs cleanly: `docker run --rm odoo-mcp python -c "import psycopg2; print('ok')"`

## Success Criteria

- Docker image builds without error
- `import psycopg2` succeeds inside container
- MCP container can reach `db:5432` when on `odoo_default` network

## Risk Assessment

- `libpq-dev` not available in slim image → already `python:3.10-slim` uses Debian, `libpq-dev` is in the Debian repos, no issue
- `psycopg2-binary` includes its own libpq — `libpq-dev` is a safety net for any compile-time resolution; both are needed to avoid import errors in some slim environments
