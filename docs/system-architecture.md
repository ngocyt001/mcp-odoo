# System Architecture — odoo-mcp

## High-Level Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                      AI Client (Claude)                         │
│                   Calls MCP Server via stdio                    │
└────────────────────────────┬─────────────────────────────────┘
                             │
                    MCP Protocol (JSON-RPC)
                             │
        ┌────────────────────▼────────────────────┐
        │                                         │
        │        FastMCP Server (server.py)       │
        │  ┌─────────────────────────────────┐   │
        │  │ • Resources (4)                 │   │
        │  │   - odoo://models               │   │
        │  │   - odoo://model/{name}         │   │
        │  │   - odoo://record/{model}/{id}  │   │
        │  │   - odoo://search/{model}       │   │
        │  ├─────────────────────────────────┤   │
        │  │ • Tools (5)                     │   │
        │  │   - execute_method              │   │
        │  │   - search_employee             │   │
        │  │   - search_holidays             │   │
        │  │   - search_tasks                │   │
        │  │   - search_projects             │   │
        │  ├─────────────────────────────────┤   │
        │  │ • Pydantic Models               │   │
        │  │   - DomainCondition             │   │
        │  │   - SearchDomain                │   │
        │  │   - EmployeeSearchResult        │   │
        │  │   - Holiday, etc.               │   │
        │  └─────────────────────────────────┘   │
        │                                         │
        │  Lifespan: OdooClient (singleton)      │
        └────────────────────┬────────────────────┘
                             │
            ┌────────────────▼────────────────┐
            │   OdooClient (odoo_client.py)   │
            │  ┌────────────────────────────┐ │
            │  │ Public Methods:            │ │
            │  │ • execute_method()         │ │
            │  │ • get_models()             │ │
            │  │ • get_model_info()         │ │
            │  │ • get_model_fields()       │ │
            │  │ • search_read()            │ │
            │  │ • read_records()           │ │
            │  │ • search_count()           │ │
            │  │ • name_search()            │ │
            │  │ • create_record()          │ │
            │  │ • write_records()          │ │
            │  │ • unlink_records()         │ │
            │  └────────────────────────────┘ │
            │  ┌────────────────────────────┐ │
            │  │ Private Methods:           │ │
            │  │ • _connect()               │ │
            │  │ • _execute()               │ │
            │  └────────────────────────────┘ │
            └────────────────────┬────────────┘
                                 │
        ┌────────────────────────▼──────────────┐
        │  RedirectTransport (Custom)           │
        │  ┌──────────────────────────────────┐ │
        │  │ • Handles HTTP redirects        │ │
        │  │ • Timeout management            │ │
        │  │ • SSL verification toggle       │ │
        │  │ • HTTP proxy support            │ │
        │  │ • Custom request headers        │ │
        │  └──────────────────────────────────┘ │
        └────────────────────┬───────────────────┘
                             │
                      HTTP/HTTPS
                             │
        ┌────────────────────▼────────────────────┐
        │      Odoo ERP Instance                  │
        │  ┌──────────────────────────────────┐   │
        │  │ XML-RPC Endpoints:               │   │
        │  │ • /xmlrpc/2/common (auth)        │   │
        │  │ • /xmlrpc/2/object (models)      │   │
        │  └──────────────────────────────────┘   │
        │  ┌──────────────────────────────────┐   │
        │  │ Models (Examples):               │   │
        │  │ • res.partner (contacts)         │   │
        │  │ • hr.employee (employees)        │   │
        │  │ • hr.leave (time off)            │   │
        │  │ • project.task (tasks)           │   │
        │  │ • project.project (projects)     │   │
        │  │ • sale.order (sales orders)      │   │
        │  └──────────────────────────────────┘   │
        └─────────────────────────────────────────┘
```

---

## Component Interaction Flow

### Request Lifecycle (Example: search_employee)

```
1. Claude asks: "Find employees named John"
   │
   └─→ MCP Client encodes request: 
       {
         "jsonrpc": "2.0",
         "id": "12345",
         "method": "tools/call",
         "params": {
           "name": "search_employee",
           "arguments": {"name": "John", "limit": 20}
         }
       }

2. MCP Server (FastMCP) receives request
   │
   └─→ Routes to @mcp.tool("search_employee") function
       │
       └─→ Context injection: ctx.request_context.lifespan_context.odoo

3. search_employee() executes
   │
   ├─→ Extract OdooClient from context
   ├─→ Call odoo.name_search("hr.employee", "John", limit=20)
   └─→ Catch exceptions, return {"success": bool, "result": [...], "error": str?}

4. OdooClient.name_search()
   │
   ├─→ Call self._execute("hr.employee", "name_search", "John", [], {"limit": 20})
   │
   └─→ OdooClient._execute()
       │
       ├─→ self._models.execute_kw(db, uid, password, model, method, args, kwargs)
       │
       └─→ RedirectTransport.request()
           │
           ├─→ Establish HTTPS connection to Odoo
           ├─→ Send XML-RPC POST request
           ├─→ Handle redirects if 301/302/303/307/308
           ├─→ Apply timeout (default 30s)
           ├─→ Receive XML-RPC response
           └─→ Decode result

5. Result bubbles back up
   │
   └─→ Claude receives: {"success": true, "result": [{"id": 10, "name": "John Doe"}]}

6. Claude formats response to user
```

---

## Data Flow Diagram

```
┌──────────────────┐
│  Claude Request  │
│  (JSON-RPC)      │
└────────┬─────────┘
         │
    ┌────▼──────────────────┐
    │  FastMCP Server       │
    │  ┌────────────────────┤
    │  │ Route to Tool      │
    │  │ (e.g., search_*)   │
    │  └────────────────────┤
    │  Validate Args        │
    │  (Pydantic)           │
    └────┬──────────────────┘
         │
    ┌────▼──────────────────┐
    │  Tool Function        │
    │  ┌────────────────────┤
    │  │ Extract OdooClient │
    │  │ from lifespan ctx  │
    │  └────────────────────┤
    │  Build domain/kwargs  │
    │  Normalize inputs     │
    └────┬──────────────────┘
         │
    ┌────▼──────────────────┐
    │  OdooClient           │
    │  ┌────────────────────┤
    │  │ execute_method()   │
    │  │ or               │
    │  │ search_read()      │
    │  │ etc.               │
    │  └────────────────────┤
    │  Build XML-RPC call   │
    └────┬──────────────────┘
         │
    ┌────▼──────────────────┐
    │  RedirectTransport    │
    │  ┌────────────────────┤
    │  │ Create HTTPS conn  │
    │  │ Handle redirects   │
    │  │ Send request       │
    │  │ Receive response   │
    │  │ (with timeout)     │
    │  └────────────────────┤
    │  Parse XML-RPC result │
    └────┬──────────────────┘
         │
    ┌────▼──────────────────┐
    │  Odoo Instance        │
    │  ┌────────────────────┤
    │  │ Execute RPC method │
    │  │ Database query     │
    │  │ Return result      │
    │  └────────────────────┤
    │  Send XML-RPC response│
    └────┬──────────────────┘
         │
         │ (reversed path)
         │
    ┌────▼──────────────────┐
    │  Result to Claude     │
    │  (JSON-RPC response)  │
    └──────────────────────┘
```

---

## Configuration & Startup Flow

```
┌────────────────────────────┐
│  Application Start         │
│  (odoo-mcp command)        │
└────────────┬───────────────┘
             │
    ┌────────▼─────────────────────┐
    │  __main__.py:main()           │
    │  ├─ Print startup banner      │
    │  ├─ Log env vars (masked pwd) │
    │  └─ Call mcp.run()            │
    └────────┬─────────────────────┘
             │
    ┌────────▼──────────────────────┐
    │  FastMCP.run()                │
    │  ├─ Initialize lifespan       │
    │  └─ Call app_lifespan()       │
    └────────┬──────────────────────┘
             │
    ┌────────▼──────────────────────────┐
    │  app_lifespan() Context Manager    │
    │  ├─ Call get_odoo_client()         │
    │  └─ Yield AppContext(odoo=client)  │
    └────────┬───────────────────────────┘
             │
    ┌────────▼──────────────────────────┐
    │  get_odoo_client() - Singleton     │
    │  ┌──────────────────────────────┐  │
    │  │ Load Configuration:          │  │
    │  │ 1. Environment vars (ODOO_*) │  │
    │  │ 2. ~/.config/odoo/conf.json  │  │
    │  │ 3. ~/.odoo_config.json       │  │
    │  │ 4. ./odoo_config.json        │  │
    │  └──────────────────────────────┘  │
    │  Create OdooClient(url, db, ...)   │
    │  Return cached instance            │
    └────────┬───────────────────────────┘
             │
    ┌────────▼──────────────────────────┐
    │  OdooClient.__init__()             │
    │  ├─ Normalize URL (add http://)    │
    │  ├─ Store credentials              │
    │  └─ Call _connect()                │
    └────────┬───────────────────────────┘
             │
    ┌────────▼──────────────────────────┐
    │  OdooClient._connect()             │
    │  ┌──────────────────────────────┐  │
    │  │ Create RedirectTransport:    │  │
    │  │ • timeout (default 30s)      │  │
    │  │ • verify_ssl (default true)  │  │
    │  │ • use_https (from URL)       │  │
    │  └──────────────────────────────┘  │
    │  Setup XML-RPC proxies:            │
    │  • self._common = /xmlrpc/2/common │
    │  • self._models = /xmlrpc/2/object │
    │  Call authenticate(db, user, pwd)  │
    │  Store uid for future requests     │
    └────────┬───────────────────────────┘
             │
    ┌────────▼──────────────────────────┐
    │  RedirectTransport.request()       │
    │  (First connection during auth)    │
    │  ├─ Create HTTPS connection        │
    │  ├─ Follow redirects 301/302/...   │
    │  └─ Apply timeout, SSL verification│
    └────────┬───────────────────────────┘
             │
    ┌────────▼──────────────────────────┐
    │  Odoo Server Response              │
    │  └─ Return uid (or raise error)    │
    └────────┬───────────────────────────┘
             │
    ┌────────▼──────────────────────────┐
    │  MCP Server Ready                  │
    │  └─ Listen for tool/resource calls │
    └────────────────────────────────────┘
```

---

## Resource Access Pattern

### Static Resources (No Caching)

Each resource request triggers a fresh RPC call:

```
Claude: "Get all models"
   ↓
Resource: odoo://models
   ↓
server.py:get_models()
   ↓
get_odoo_client() [singleton instance]
   ↓
odoo_client.get_models()
   ↓
_execute("ir.model", "search", []) + read fields
   ↓
XML-RPC → Odoo
   ↓
Return: {model_names: [...], models_details: {...}}
```

### Domain Search Resource

```
Claude: "Search res.partner where is_company=true"
   ↓
Resource: odoo://search/res.partner/[["is_company","=",true]]
   ↓
server.py:search_records_resource(model_name, domain)
   ↓
Parse domain from JSON string
   ↓
odoo_client.search_read(model, domain_list, limit=10)
   ↓
_execute("res.partner", "search_read", domain_list, {...})
   ↓
XML-RPC → Odoo
   ↓
Return: [{record}, ...]  (max 10 records)
```

---

## Error Handling Architecture

### Connection-Level Errors

```
┌──────────────────────────────┐
│ RedirectTransport.request()  │
├──────────────────────────────┤
│ socket.error                 │
│ socket.timeout               │
│ ConnectionError              │
│ TimeoutError                 │
└────────────┬─────────────────┘
             │
      ┌──────▼────────┐
      │ Re-raise as   │
      │ ConnectionErr │
      └──────┬────────┘
             │
    ┌────────▼──────────┐
    │ Caught in         │
    │ __init__ or tool  │
    └────────┬──────────┘
             │
    ┌────────▼──────────────────┐
    │ Return to tool/resource:  │
    │ {success: false, error:   │
    │  "Failed to connect..."}  │
    └───────────────────────────┘
```

### Authentication Errors

```
┌─────────────────────────────┐
│ OdooClient._connect()       │
│ common.authenticate()       │
│ Returns: None (failed) OR   │
│ Raises: ValueError          │
└────────────┬────────────────┘
             │
    ┌────────▼────────────────────┐
    │ Exception propagates        │
    │ Startup fails immediately   │
    │ (fatal error, not recoverable)
    └─────────────────────────────┘
```

### RPC Execution Errors

```
┌─────────────────────────────┐
│ OdooClient.execute_method() │
│ _execute() call fails       │
│ (invalid model, method, etc)│
└────────────┬────────────────┘
             │
    ┌────────▼─────────────────┐
    │ Exception caught in tool │
    │ (try/except wrapper)     │
    └────────┬─────────────────┘
             │
    ┌────────▼──────────────────────┐
    │ Return dict with error:       │
    │ {"success": false,            │
    │  "error": "message"}          │
    └───────────────────────────────┘
```

---

## Lifespan & State Management

### Singleton Pattern (OdooClient)

```python
# Module-level cache
_odoo_client = None

def get_odoo_client() -> OdooClient:
    """Get or create singleton OdooClient"""
    global _odoo_client
    if _odoo_client is None:
        _odoo_client = OdooClient(
            url=load_url(),
            db=load_db(),
            username=load_username(),
            password=load_password(),
            timeout=load_timeout(),
            verify_ssl=load_verify_ssl()
        )
    return _odoo_client
```

### Lifespan Context Injection

```python
@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Called once on server startup"""
    odoo_client = get_odoo_client()  # Singleton init + auth
    try:
        yield AppContext(odoo=odoo_client)  # Available for all requests
    finally:
        # No cleanup needed (stateless XML-RPC)
        pass
```

### Per-Request Access

```python
@mcp.tool(description="...")
def my_tool(ctx: Context, ...) -> Dict[str, Any]:
    """Every tool receives ctx parameter"""
    odoo = ctx.request_context.lifespan_context.odoo  # Access singleton
    result = odoo.execute_method(...)
    return {"success": True, "result": result}
```

---

## XML-RPC Communication Details

### Authentication Flow

```
Client: POST /xmlrpc/2/common
Body: <?xml version="1.0"?>
      <methodCall>
        <methodName>authenticate</methodName>
        <params>
          <param><value><string>database_name</string></value></param>
          <param><value><string>username</string></value></param>
          <param><value><string>password</string></value></param>
          <param><value><struct></struct></value></param>
        </params>
      </methodCall>

Server: HTTP 200 OK
Body: <?xml version="1.0"?>
      <methodResponse>
        <params>
          <param><value><int>2</int></value></param>
        </params>
      </methodResponse>
      (uid = 2)
```

### Method Execution

```
Client: POST /xmlrpc/2/object
Body: <?xml version="1.0"?>
      <methodCall>
        <methodName>execute_kw</methodName>
        <params>
          <param><value><string>database_name</string></value></param>
          <param><value><int>2</int></value></param>       <!-- uid -->
          <param><value><string>password</string></value></param>
          <param><value><string>res.partner</string></value></param>
          <param><value><string>search</string></value></param>
          <param><value><array>
            <data>
              <value><array>
                <data>
                  <value><string>is_company</string></value>
                  <value><string>=</string></value>
                  <value><boolean>1</boolean></value>
                </data>
              </array></value>
            </data>
          </array></value>
          <param><value><struct></struct></value></param>  <!-- empty kwargs -->
        </params>
      </methodCall>

Server: HTTP 200 OK
Body: <?xml version="1.0"?>
      <methodResponse>
        <params>
          <param><value><array>
            <data>
              <value><int>1</int></value>
              <value><int>3</int></value>
              <value><int>5</int></value>
            </data>
          </array></value>
        </params>
      </methodResponse>
      (IDs = [1, 3, 5])
```

---

## Deployment Architecture

### Docker Deployment

```
┌────────────────────────────────┐
│  Docker Host                   │
├────────────────────────────────┤
│  Container: mcp/odoo           │
│  ├─ Base: python:3.10-slim     │
│  ├─ Workdir: /app              │
│  ├─ Packages:                  │
│  │  • mcp[cli]                 │
│  │  • odoo-mcp (editable)       │
│  │  • System: gcc, procps       │
│  ├─ Volumes: /app/logs (777)   │
│  ├─ Env vars:                  │
│  │  • ODOO_URL                 │
│  │  • ODOO_DB                  │
│  │  • ODOO_USERNAME            │
│  │  • ODOO_PASSWORD            │
│  │  • ODOO_TIMEOUT (default 30)│
│  │  • ODOO_VERIFY_SSL (default 1)
│  │  • PYTHONUNBUFFERED=1       │
│  ├─ Entrypoint: run_server.py  │
│  └─ Logging: logs/ directory   │
└────────────────────────────────┘
          │
          └─→ HTTP/HTTPS to Odoo
```

### Claude Desktop Configuration

```json
{
  "mcpServers": {
    "odoo": {
      "command": "python",
      "args": ["-m", "odoo_mcp"],
      "env": {
        "ODOO_URL": "https://odoo.example.com",
        "ODOO_DB": "production",
        "ODOO_USERNAME": "api_user",
        "ODOO_PASSWORD": "api_key_here"
      }
    }
  }
}
```

---

## Security Architecture

### Authentication Flow

```
1. Config Loading (Priority):
   ├─ Environment variables (ODOO_*)
   ├─ ~/.config/odoo/config.json
   ├─ ~/.odoo_config.json
   └─ ./odoo_config.json

2. Credentials Extraction:
   ├─ url → may add http:// prefix
   ├─ db → literal
   ├─ username → literal
   ├─ password → API key recommended (not plain password)

3. SSL/TLS Configuration:
   ├─ HTTPS by default (auto-detected from URL)
   ├─ Verify SSL certificates (default: true)
   │   └─ Disable only for testing: verify_ssl=false
   └─ Custom CA certs: N/A (use system trust store)

4. Odoo Authentication:
   └─ XML-RPC authenticate() endpoint
       └─ Returns uid for session

5. Request Signing:
   └─ All RPC calls include: [db, uid, password]
       (No separate token, uses Odoo password as session key)
```

### Secrets Masking

```
Startup logging:
├─ ODOO_URL     → logged (public)
├─ ODOO_DB      → logged (public)
├─ ODOO_USERNAME → logged (public)
├─ ODOO_PASSWORD → **hidden** (masked)
└─ HTTP_PROXY    → logged (usually public)

Exception messages:
└─ Never include full passwords in error output
```

---

## Scalability Considerations

### Bottlenecks

1. **Single XML-RPC Connection:**
   - No connection pooling (single client per process)
   - Synchronized calls only (no async)
   - Solution: Run multiple MCP server instances, load-balance

2. **Odoo Instance Capacity:**
   - Depends on Odoo server resources
   - Monitor XML-RPC endpoint load
   - Consider Odoo database optimization

3. **Network Latency:**
   - Default timeout 30s (configurable)
   - Increase for slow/distant servers
   - Consider reducing for local dev

### Performance Optimization

1. **Batch Operations:**
   ```python
   # Good: Single RPC call
   odoo.write_records(model, [1, 2, 3, 4, 5], values)
   
   # Avoid: Multiple RPC calls
   for id in [1, 2, 3, 4, 5]:
       odoo.write_records(model, [id], values)
   ```

2. **Field Limiting:**
   ```python
   # Good: Request only needed fields
   odoo.search_read(model, domain, fields=['id', 'name'])
   
   # Avoid: Load all fields
   odoo.search_read(model, domain)  # Returns all fields
   ```

3. **Domain Optimization:**
   - Use indexed fields (id, name)
   - Avoid complex multi-table joins
   - Limit result sets (use limit parameter)

