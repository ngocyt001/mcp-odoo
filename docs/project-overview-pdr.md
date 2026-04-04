# Odoo MCP Server — Project Overview & PDR

## Project Purpose

**odoo-mcp** is a Model Context Protocol (MCP) server that bridges AI assistants with Odoo ERP systems. It enables Claude, ChatGPT, and other AI tools to query Odoo data, execute methods, and retrieve model information via a standardized MCP interface over XML-RPC.

**Version:** 0.0.3 | **License:** MIT | **Author:** Lê Anh Tuấn

## Core Value Proposition

- **Zero-Code Integration:** AI assistants can interact with any Odoo instance without custom scripting
- **Full Model Access:** Execute any Odoo model method, query data, and manipulate records
- **Secure Defaults:** SSL verification, timeout handling, proxy support, API key authentication
- **Production Ready:** Docker support, configurable via env vars, stateless operation

## Key Features

| Feature | Details |
|---------|---------|
| **XML-RPC Transport** | HTTP/HTTPS with redirect handling (301/302/303/307/308), custom transport layer |
| **Multi-format Domains** | Supports list `[[field, op, val]]`, object `{conditions:[...]}`, JSON string formats |
| **Type Safety** | Pydantic models for all request/response schemas |
| **Configuration** | Env vars (priority 1), config files: `~/.config/odoo/config.json`, `~/.odoo_config.json` (priority 2-3) |
| **Odoo Compatibility** | Tested Odoo 13+, special handling for Odoo 18 (many2many user_ids, removed date_assign) |
| **Error Handling** | Clear error messages, connection error recovery, authentication validation |
| **Claude Desktop** | Native integration via MCP protocol |
| **Docker** | Python 3.10-slim, pre-configured with dependencies |

## MCP Tools Reference

### 1. execute_method
Execute any Odoo model method with flexible domain normalization.

**Inputs:**
- `model` (string, required) — Model name (e.g., `res.partner`)
- `method` (string, required) — Method name
- `args` (array, optional) — Positional arguments
- `kwargs` (object, optional) — Keyword arguments

**Returns:** `{success: bool, result?: any, error?: string}`

**Examples:**
```python
# Get all companies
execute_method(model="res.partner", method="search", 
  args=[[[["is_company", "=", true]]]])

# Create a new contact
execute_method(model="res.partner", method="create",
  args=[[{"name": "John Doe", "email": "john@example.com"}]])

# Call custom method with kwargs
execute_method(model="sale.order", method="action_confirm",
  kwargs={"context": {"force_approve": true}})
```

**Domain Normalization:** Handles `[domain]` vs `domain`, object format, JSON strings automatically.

---

### 2. search_employee
Search employees by name via `hr.employee` model.

**Inputs:**
- `name` (string, required) — Employee name or partial match
- `limit` (number, optional, default 20) — Max results

**Returns:** `{success: bool, result?: [{id: int, name: string}], error?: string}`

---

### 3. search_holidays
Search leave records within date range.

**Inputs:**
- `start_date` (string, required) — Start date YYYY-MM-DD
- `end_date` (string, required) — End date YYYY-MM-DD
- `employee_id` (number, optional) — Filter by employee

**Returns:** `{success: bool, result?: Holiday[], error?: string}`

**Holiday Model:** Queries `hr.leave.report.calendar`, returns display_name, dates, state, employee_id.

---

### 4. search_tasks
Search project tasks (Odoo 13+, Odoo 18 compatible).

**Inputs:**
- `project_id` (number, optional) — Filter by project
- `stage_name` (string, optional) — Filter by stage (e.g., "To Do", "In Progress")
- `active_only` (boolean, default true) — Include only active tasks
- `limit` (number, optional, default 50) — Max results

**Returns:** `{success: bool, result?: Task[], error?: string}`

**Odoo 18 Note:** Uses `user_ids` (many2many) field instead of legacy `user_id` (many2one).

---

### 5. search_projects
Search projects by name and active status.

**Inputs:**
- `name` (string, optional) — Project name filter
- `active_only` (boolean, default true) — Include only active
- `limit` (number, optional, default 20) — Max results

**Returns:** `{success: bool, result?: Project[], error?: string}`

---

## MCP Resources Reference

| Resource | Description | Example |
|----------|-------------|---------|
| `odoo://models` | List all Odoo models | Returns JSON array with model_names and details |
| `odoo://model/{model_name}` | Model info + field definitions | `odoo://model/res.partner` → {name, fields{...}} |
| `odoo://record/{model_name}/{record_id}` | Single record by ID | `odoo://record/res.partner/1` → record data |
| `odoo://search/{model_name}/{domain}` | Search records (limit 10) | `odoo://search/res.partner/[["is_company","=",true]]` |

**Domain Format:** JSON-encoded list `[["field", "operator", value], ...]`

---

## Architecture

### High-Level Flow
```
AI Client (Claude) 
  ↓ (MCP Protocol)
FastMCP Server (server.py)
  ↓ (lifespan context injection)
Pydantic Models + Tools
  ↓ (AppContext.odoo)
OdooClient (odoo_client.py)
  ↓ (XML-RPC calls)
RedirectTransport (custom)
  ↓ (HTTP/HTTPS with timeout, SSL, proxy)
Odoo ERP Instance
```

### Key Components
1. **FastMCP Server** — MCP protocol handler, resource/tool registration
2. **OdooClient** — XML-RPC client, model introspection, method execution
3. **RedirectTransport** — Custom XML-RPC transport with advanced features
4. **Pydantic Models** — Type-safe request/response validation
5. **AppContext** — Lifespan-managed singleton OdooClient instance

---

## Use Cases

1. **AI-Assisted ERP Queries:** Ask Claude to list overdue sales orders, employees on vacation
2. **Automated Reporting:** Generate reports by querying Odoo data programmatically
3. **Data Enrichment:** Use AI to validate, categorize, or enrich contact/product data
4. **Process Automation:** Trigger Odoo workflows (state transitions, approvals) via Claude prompts
5. **Decision Support:** Analyze sales trends, inventory levels, project status via AI insights
6. **Multi-System Integration:** Chain Odoo queries with other tools (sheets, CRM, etc.)

---

## Technical Requirements

| Requirement | Specification |
|-------------|---------------|
| **Python** | 3.10+ |
| **Odoo** | 13+ (18+ with special handling) |
| **Network** | HTTPS recommended, HTTP supported |
| **Dependencies** | mcp>=0.1.1, requests>=2.31.0, pypi-xmlrpc==2020.12.3 |
| **Deployment** | Pip, Docker, MCP dev mode |
| **Protocol** | MCP v1 (Model Context Protocol) |

---

## Security Considerations

1. **API Key Storage:** Use env vars or config files (not hardcoded)
2. **SSL Verification:** Enabled by default, disable only for testing
3. **Timeout:** Default 30s, adjustable to prevent hanging requests
4. **Proxy Support:** HTTP_PROXY env var for corporate networks
5. **Error Messages:** Avoid leaking sensitive Odoo internals to AI clients
6. **Config Files:** Keep odoo_config.json out of version control (.gitignore recommended)

---

## Success Metrics

- **Reliability:** <0.1% failure rate on valid Odoo instances
- **Latency:** <2s P95 for typical queries (depends on Odoo instance)
- **Coverage:** All Odoo models + custom fields supported
- **Compatibility:** Odoo 13, 14, 15, 16, 17, 18 (with version-specific handling)
- **Adoption:** Used in production Claude Desktop configs
