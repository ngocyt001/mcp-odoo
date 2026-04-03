# Odoo MCP Server

An MCP server implementation that integrates with Odoo ERP systems, enabling AI assistants to interact with Odoo data and functionality through the Model Context Protocol.

## Features

* **Comprehensive Odoo Integration**: Full access to Odoo models, records, and methods
* **XML-RPC Communication**: Secure connection to Odoo instances via XML-RPC
* **Flexible Configuration**: Support for config files and environment variables
* **Resource Pattern System**: URI-based access to Odoo data structures
* **Error Handling**: Clear error messages for common Odoo API issues
* **Stateless Operations**: Clean request/response cycle for reliable integration

## Tools

* **execute_method**
  * Execute a custom method on an Odoo model
  * Inputs:
    * `model` (string): The model name (e.g., 'res.partner')
    * `method` (string): Method name to execute
    * `args` (optional array): Positional arguments
    * `kwargs` (optional object): Keyword arguments
  * Returns: Dictionary with the method result and success indicator

* **search_employee**
  * Search for employees by name
  * Inputs:
    * `name` (string): The name (or part of the name) to search for
    * `limit` (optional number): The maximum number of results to return (default 20)
  * Returns: Object containing success indicator, list of matching employee names and IDs, and any error message

* **search_holidays**
  * Searches for holidays within a specified date range
  * Inputs:
    * `start_date` (string): Start date in YYYY-MM-DD format
    * `end_date` (string): End date in YYYY-MM-DD format
    * `employee_id` (optional number): Optional employee ID to filter holidays
  * Returns: Object containing success indicator, list of holidays found, and any error message
  * Note: Requires the Time Off (`hr_holidays`) module to be installed

* **execute_sql**
  * Execute a read-only SQL SELECT query directly on the Odoo PostgreSQL database
  * Inputs:
    * `query` (string): A valid SQL SELECT statement
    * `limit` (optional number): Max rows to return if no LIMIT clause present (default 100)
  * Returns: Object with `success`, `result` (list of row dicts), `row_count`, and `error`

* **list_db_tables**
  * List all tables in the Odoo PostgreSQL database
  * Returns: Object with `success`, `tables` (list of table names), and `error`

* **describe_db_table**
  * Describe the columns of a table in the Odoo PostgreSQL database
  * Inputs:
    * `table_name` (string): The table name (e.g., `res_partner`)
  * Returns: Object with `success`, `columns` (list of column dicts with name, type, nullable, default), and `error`

## Resources

* **odoo://models**
  * Lists all available models in the Odoo system
  * Returns: JSON array of model information

* **odoo://model/{model_name}**
  * Get information about a specific model including fields
  * Example: `odoo://model/res.partner`
  * Returns: JSON object with model metadata and field definitions

* **odoo://record/{model_name}/{record_id}**
  * Get a specific record by ID
  * Example: `odoo://record/res.partner/1`
  * Returns: JSON object with record data

* **odoo://search/{model_name}/{domain}**
  * Search for records that match a domain
  * Example: `odoo://search/res.partner/[["is_company","=",true]]`
  * Returns: JSON array of matching records (limited to 10 by default)

## Configuration

### Odoo Connection Setup

1. Create a configuration file named `odoo_config.json`:

```json
{
  "url": "https://your-odoo-instance.com",
  "db": "your-database-name",
  "username": "your-username",
  "password": "your-password-or-api-key"
}
```

2. Alternatively, use environment variables:
   * `ODOO_URL`: Your Odoo server URL
   * `ODOO_DB`: Database name
   * `ODOO_USERNAME`: Login username
   * `ODOO_PASSWORD`: Password or API key
   * `ODOO_TIMEOUT`: Connection timeout in seconds (default: 30)
   * `ODOO_VERIFY_SSL`: Whether to verify SSL certificates (default: true)
   * `HTTP_PROXY`: Force the ODOO connection to use an HTTP proxy

### PostgreSQL Direct Access

This MCP supports direct SQL queries against the Odoo PostgreSQL database, bypassing XML-RPC for complex queries or data not exposed via the Odoo API. Requires Odoo 16 / 19.

#### 1. Create a read-only PostgreSQL user (required)

```sql
-- Run once as the Odoo DB superuser (e.g. psql -U odoo odoo)
CREATE USER mcp_readonly WITH PASSWORD 'choose-a-strong-password';
GRANT CONNECT ON DATABASE odoo TO mcp_readonly;
GRANT USAGE ON SCHEMA public TO mcp_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO mcp_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO mcp_readonly;
```

#### 2. PostgreSQL environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_HOST` | `db` | PostgreSQL hostname |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `POSTGRES_USER` | — | Database user (**must be read-only**) |
| `POSTGRES_PASSWORD` | — | Database password |
| `POSTGRES_DB` | — | Database name |
| `POSTGRES_MAX_ROWS` | *(unset = unlimited)* | Hard cap on rows per query; unset/empty = all rows |
| `POSTGRES_SKIP_READONLY_CHECK` | `false` | Bypass SELECT-only check (dev/testing only — **never in production**) |

#### 3. Docker Compose example

```yaml
services:
  odoo-mcp:
    image: mcp/odoo:latest
    networks:
      - odoo_default
    environment:
      # XML-RPC connection
      ODOO_URL: http://odoo:8069
      ODOO_DB: odoo
      ODOO_USERNAME: admin
      ODOO_PASSWORD: admin
      # PostgreSQL direct access
      POSTGRES_HOST: db
      POSTGRES_PORT: "5432"
      POSTGRES_USER: mcp_readonly
      POSTGRES_PASSWORD: choose-a-strong-password
      POSTGRES_DB: odoo

networks:
  odoo_default:
    external: true
```

For local development (outside Docker), expose the port and use `POSTGRES_HOST=localhost`:

```yaml
services:
  db:
    ports:
      - "5432:5432"
```

### Usage with Claude Desktop

Add this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "odoo": {
      "command": "python",
      "args": [
        "-m",
        "odoo_mcp"
      ],
      "env": {
        "ODOO_URL": "https://your-odoo-instance.com",
        "ODOO_DB": "your-database-name",
        "ODOO_USERNAME": "your-username",
        "ODOO_PASSWORD": "your-password-or-api-key"
      }
    }
  }
}
```

### Docker

```json
{
  "mcpServers": {
    "odoo": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e",
        "ODOO_URL",
        "-e",
        "ODOO_DB",
        "-e",
        "ODOO_USERNAME",
        "-e",
        "ODOO_PASSWORD",
        "mcp/odoo"
      ],
      "env": {
        "ODOO_URL": "https://your-odoo-instance.com",
        "ODOO_DB": "your-database-name",
        "ODOO_USERNAME": "your-username",
        "ODOO_PASSWORD": "your-password-or-api-key"
      }
    }
  }
}
```

## Installation

### Python Package

```bash
pip install odoo-mcp
```

### Running the Server

```bash
# Using the installed package
odoo-mcp

# Using the MCP development tools
mcp dev odoo_mcp/server.py

# With additional dependencies
mcp dev odoo_mcp/server.py --with pandas --with numpy

# Mount local code for development
mcp dev odoo_mcp/server.py --with-editable .
```

## Build

Docker build:

```bash
docker build -t mcp/odoo:latest -f Dockerfile .
```

## Parameter Formatting Guidelines

When using the MCP tools for Odoo, pay attention to these parameter formatting guidelines:

1. **Domain Parameter**:
   * The following domain formats are supported:
     * List format: `[["field", "operator", value], ...]`
     * Object format: `{"conditions": [{"field": "...", "operator": "...", "value": "..."}]}`
     * JSON string of either format
   * Examples:
     * List format: `[["is_company", "=", true]]`
     * Object format: `{"conditions": [{"field": "date_order", "operator": ">=", "value": "2025-03-01"}]}`
     * Multiple conditions: `[["date_order", ">=", "2025-03-01"], ["date_order", "<=", "2025-03-31"]]`

2. **Fields Parameter**:
   * Should be an array of field names: `["name", "email", "phone"]`
   * The server will try to parse string inputs as JSON

## License

This MCP server is licensed under the MIT License.
