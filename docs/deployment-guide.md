# Deployment Guide — odoo-mcp

## Quick Start

### Minimum Requirements
- **Python:** 3.10+
- **Odoo:** 13+ (18+ recommended)
- **Network:** HTTPS connection to Odoo server
- **Credentials:** Odoo username/password or API key

---

## Installation Methods

### Method 1: pip (Recommended)

**Install from PyPI:**
```bash
pip install odoo-mcp
```

**Verify installation:**
```bash
odoo-mcp --help
# or
python -m odoo_mcp --version
```

**Upgrade:**
```bash
pip install --upgrade odoo-mcp
```

---

### Method 2: Development Installation

**Clone repository:**
```bash
git clone https://github.com/tuanle96/mcp-odoo.git
cd mcp-odoo
```

**Install in editable mode:**
```bash
pip install -e .
```

**With dev tools:**
```bash
pip install -e ".[dev]"
```

**Run directly:**
```bash
python -m odoo_mcp
```

---

### Method 3: Docker

**Build image:**
```bash
docker build -t mcp/odoo:latest -f Dockerfile .
```

**Run container:**
```bash
docker run -i --rm \
  -e ODOO_URL="https://odoo.example.com" \
  -e ODOO_DB="production" \
  -e ODOO_USERNAME="api_user" \
  -e ODOO_PASSWORD="api_key" \
  mcp/odoo:latest
```

**With file logging:**
```bash
docker run -i --rm \
  -v logs:/app/logs \
  -e ODOO_URL="https://odoo.example.com" \
  -e ODOO_DB="production" \
  -e ODOO_USERNAME="api_user" \
  -e ODOO_PASSWORD="api_key" \
  mcp/odoo:latest
```

**Pull from registry (when published):**
```bash
docker run -i --rm \
  -e ODOO_URL="https://odoo.example.com" \
  -e ODOO_DB="production" \
  -e ODOO_USERNAME="api_user" \
  -e ODOO_PASSWORD="api_key" \
  odoo-mcp:latest
```

---

### Method 4: MCP Dev Mode

**For development/testing (requires MCP tools installed):**
```bash
# Install MCP development tools
npm install -g @modelcontextprotocol/sdk

# Run server in dev mode
mcp dev src/odoo_mcp/server.py
```

---

## Configuration

### Configuration File (Priority: 2nd)

**Create `~/.config/odoo/config.json`:**
```bash
mkdir -p ~/.config/odoo
cat > ~/.config/odoo/config.json << 'EOF'
{
  "url": "https://odoo.example.com",
  "db": "production",
  "username": "api_user",
  "password": "your_api_key_or_password",
  "timeout": 30,
  "verify_ssl": true
}
EOF

chmod 600 ~/.config/odoo/config.json  # Secure permissions
```

**Or create `~/.odoo_config.json`:**
```bash
cat > ~/.odoo_config.json << 'EOF'
{
  "url": "https://odoo.example.com",
  "db": "production",
  "username": "api_user",
  "password": "your_api_key_or_password"
}
EOF

chmod 600 ~/.odoo_config.json  # Secure permissions
```

**Or create local `odoo_config.json` (not recommended for production):**
```bash
cat > odoo_config.json << 'EOF'
{
  "url": "https://odoo.example.com",
  "db": "production",
  "username": "api_user",
  "password": "your_api_key_or_password"
}
EOF
```

**Configuration File Format:**
```json
{
  "url": "https://odoo.example.com",          // Required: Odoo server URL
  "db": "production",                         // Required: Database name
  "username": "api_user",                     // Required: Login username
  "password": "your_api_key_or_password",     // Required: Password/API key
  "timeout": 30,                              // Optional: Request timeout (seconds)
  "verify_ssl": true                          // Optional: Verify SSL certificates
}
```

### Environment Variables (Priority: 1st, highest)

**Required:**
```bash
export ODOO_URL="https://odoo.example.com"
export ODOO_DB="production"
export ODOO_USERNAME="api_user"
export ODOO_PASSWORD="your_api_key_or_password"
```

**Optional:**
```bash
export ODOO_TIMEOUT="30"           # Request timeout (default: 30)
export ODOO_VERIFY_SSL="true"      # Verify SSL (default: true)
export HTTP_PROXY="http://proxy:8080"  # Corporate proxy (if needed)
```

**Run with env vars:**
```bash
ODOO_URL="https://odoo.example.com" \
ODOO_DB="production" \
ODOO_USERNAME="api_user" \
ODOO_PASSWORD="api_key" \
python -m odoo_mcp
```

**Or from .env file:**
```bash
# Create .env file (DO NOT commit to git)
cat > .env << 'EOF'
ODOO_URL=https://odoo.example.com
ODOO_DB=production
ODOO_USERNAME=api_user
ODOO_PASSWORD=api_key
EOF

# Load and run
set -a; source .env; set +a
python -m odoo_mcp
```

### Configuration Priority

**Loading order (highest → lowest):**
1. Environment variables (`ODOO_*`)
2. `~/.config/odoo/config.json`
3. `~/.odoo_config.json`
4. `./odoo_config.json` (local)

**Example:**
```bash
# This env var takes precedence
export ODOO_URL="https://override.com"

# Even if config.json has a different URL
python -m odoo_mcp  # Uses https://override.com
```

---

## Odoo Preparation

### Create API User (Recommended)

**In Odoo (as admin):**
1. Go to Settings → Users & Companies → Users
2. Create new user "api_mcp"
3. Set password or generate API key
4. Assign required groups:
   - Access Rights: Basic User
   - Or custom group with required models access
5. Save

**Benefits:**
- API key instead of user password (more secure)
- Separate audit trail for MCP operations
- Can disable without affecting real user
- Fine-grained permission control

### Required Odoo Permissions

**Minimum access for core tools:**

| Tool | Model | Required Permission |
|------|-------|-------------------|
| execute_method | Any | Model-specific access |
| search_employee | hr.employee | Read access |
| search_holidays | hr.leave.report.calendar | Read access |
| search_tasks | project.task | Read access |
| search_projects | project.project | Read access |

**Setup custom group (optional):**
1. Create group "MCP Access"
2. Grant read access to required models
3. Assign to api_mcp user

---

## Claude Desktop Integration

### Configuration File Location

**macOS:**
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Windows:**
```
%APPDATA%\Claude\claude_desktop_config.json
```

**Linux:**
```
~/.config/Claude/claude_desktop_config.json
```

### Method 1: Pip Installation (Recommended)

**Edit `claude_desktop_config.json`:**
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
        "ODOO_URL": "https://odoo.example.com",
        "ODOO_DB": "production",
        "ODOO_USERNAME": "api_user",
        "ODOO_PASSWORD": "your_api_key"
      }
    }
  }
}
```

### Method 2: Docker

**Edit `claude_desktop_config.json`:**
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
        "mcp/odoo:latest"
      ],
      "env": {
        "ODOO_URL": "https://odoo.example.com",
        "ODOO_DB": "production",
        "ODOO_USERNAME": "api_user",
        "ODOO_PASSWORD": "your_api_key"
      }
    }
  }
}
```

### Method 3: Development (Git Checkout)

**Edit `claude_desktop_config.json`:**
```json
{
  "mcpServers": {
    "odoo": {
      "command": "python",
      "args": [
        "-m",
        "odoo_mcp"
      ],
      "cwd": "/path/to/mcp-odoo",
      "env": {
        "PYTHONPATH": "/path/to/mcp-odoo/src",
        "ODOO_URL": "https://odoo.example.com",
        "ODOO_DB": "production",
        "ODOO_USERNAME": "api_user",
        "ODOO_PASSWORD": "your_api_key"
      }
    }
  }
}
```

### Verify Connection

1. Restart Claude Desktop
2. Check Claude menu → Settings → Model Context Protocol
3. Should show "odoo" server status
4. Test: Ask Claude "List all Odoo models"
5. Should return JSON array of model names

---

## Production Deployment

### Architecture

```
┌─────────────────────────────┐
│    Claude Desktop (macOS)    │
└──────────────┬──────────────┘
               │ MCP Protocol
               │ (stdio/JSON-RPC)
               │
    ┌──────────▼──────────────┐
    │  MCP Odoo Server        │
    │  (python -m odoo_mcp)   │
    │  ├─ Single process      │
    │  └─ Stateless requests  │
    └──────────┬──────────────┘
               │ XML-RPC
               │ (HTTPS)
               │
    ┌──────────▼──────────────┐
    │   Odoo Instance         │
    │   (https://...)         │
    └─────────────────────────┘
```

### Deployment Checklist

**Before Production:**
- [ ] Test with real Odoo instance
- [ ] Create dedicated API user
- [ ] Secure credentials (use env vars)
- [ ] Set appropriate ODOO_TIMEOUT
- [ ] Verify ODOO_VERIFY_SSL=true
- [ ] Test with sample domains
- [ ] Review error handling
- [ ] Monitor logs

**Security:**
- [ ] Use HTTPS only (no HTTP)
- [ ] API key instead of password
- [ ] Restrict network access if possible
- [ ] Keep odoo-mcp updated
- [ ] Audit logs regularly
- [ ] Don't commit config to git

**Monitoring:**
- [ ] Check stderr logs for errors
- [ ] Monitor response times
- [ ] Track error rates
- [ ] Setup alerts for failures

### Scaling Strategy

**Single Instance (Recommended for most use):**
- Simple, no coordination needed
- Sufficient for typical Claude usage (1-5 concurrent)
- Monitor and upgrade if overloaded

**Multiple Instances (If needed):**
1. Run multiple MCP server processes
2. Use load balancer (e.g., nginx)
3. Configure Claude Desktop to use load balancer
4. Share configuration via environment

**Example (nginx reverse proxy):**
```nginx
upstream odoo_mcp {
    server localhost:8001;
    server localhost:8002;
    server localhost:8003;
}

server {
    listen 8000;
    location / {
        proxy_pass http://odoo_mcp;
    }
}
```

---

## Environment Variables Reference

### Core Configuration

| Variable | Type | Default | Required | Example |
|----------|------|---------|----------|---------|
| `ODOO_URL` | string | — | Yes | `https://odoo.example.com` |
| `ODOO_DB` | string | — | Yes | `production` |
| `ODOO_USERNAME` | string | — | Yes | `api_user` |
| `ODOO_PASSWORD` | string | — | Yes | `api_key_123` |

### Connection Tuning

| Variable | Type | Default | Notes |
|----------|------|---------|-------|
| `ODOO_TIMEOUT` | integer | 30 | Seconds, increase for slow networks |
| `ODOO_VERIFY_SSL` | boolean | true | Set to false only for testing |
| `HTTP_PROXY` | string | — | For corporate proxies |

### Deployment

| Variable | Type | Default | Notes |
|----------|------|---------|-------|
| `PYTHONUNBUFFERED` | string | — | Set to 1 for real-time logging |
| `DEBUG` | string | 0 | Set to 1 for verbose logging (Docker) |

**Example startup:**
```bash
ODOO_URL="https://odoo.example.com" \
ODOO_DB="production" \
ODOO_USERNAME="api_user" \
ODOO_PASSWORD="api_key" \
ODOO_TIMEOUT="60" \
PYTHONUNBUFFERED="1" \
python -m odoo_mcp
```

---

## Troubleshooting

### Connection Issues

**Symptom:** "Failed to connect to Odoo server"

**Diagnosis:**
```bash
# Test Odoo connectivity
curl -k https://odoo.example.com/xmlrpc/2/common

# Check Python can reach Odoo
python -c "import requests; print(requests.get('https://odoo.example.com').status_code)"
```

**Solutions:**
1. Verify ODOO_URL is correct
2. Check network connectivity
3. Disable firewall/VPN if blocking
4. Set ODOO_VERIFY_SSL=false (testing only)
5. Increase ODOO_TIMEOUT

---

### Authentication Errors

**Symptom:** "Authentication failed: Invalid username or password"

**Solutions:**
1. Verify ODOO_USERNAME and ODOO_PASSWORD
2. Check user exists in Odoo
3. Check password/API key is correct
4. Verify user has "Basic User" group
5. Try with admin account first (for testing)

---

### Timeout Issues

**Symptom:** "Connection timeout" or long delays

**Solutions:**
1. Increase ODOO_TIMEOUT: `export ODOO_TIMEOUT=60`
2. Check Odoo server is responsive
3. Check network latency: `ping odoo.example.com`
4. Reduce domain complexity (fewer conditions)
5. Check Odoo database is not under heavy load

---

### Claude Desktop Not Connecting

**Symptom:** Server appears offline in Claude Desktop

**Solutions:**
1. Restart Claude Desktop
2. Check syntax of claude_desktop_config.json (validate JSON)
3. Verify command path: `which python`
4. Test manually: `python -m odoo_mcp` (should start without errors)
5. Check stderr logs for startup errors
6. Ensure ODOO_* env vars are set

---

### Database/Model Access Issues

**Symptom:** "Model not found" or permission denied

**Solutions:**
1. Verify database name (ODOO_DB) matches Odoo
2. Check user has access to model/database
3. Verify model name (e.g., `hr.employee` not `employee`)
4. Check Odoo module is installed (hr, project, etc.)

---

## Logs & Debugging

### Startup Logs

When server starts, it prints to stderr:
```
=== ODOO MCP SERVER STARTING ===
Python version: 3.10.x
Environment variables:
  ODOO_URL: https://odoo.example.com
  ODOO_DB: production
  ODOO_USERNAME: api_user
  ODOO_PASSWORD: ***hidden***
Connecting to Odoo at: https://odoo.example.com
  Hostname: odoo.example.com
  Timeout: 30s, Verify SSL: True
Authenticating with database: production, username: api_user
Making request to odoo.example.com/xmlrpc/2/common (attempt 1)
```

### Docker Logs

```bash
# View running container logs
docker logs <container_id>

# With timestamps
docker logs --timestamps <container_id>

# Follow logs
docker logs -f <container_id>
```

### Error Examples

**SSL verification failure:**
```
[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed
Solution: Set ODOO_VERIFY_SSL=false (testing) or fix certificate
```

**Connection refused:**
```
[Errno 111] Connection refused
Solution: Verify ODOO_URL, check Odoo is running, check firewall
```

**XML-RPC parse error:**
```
Traceback: xmlrpc.client.ResponseError: [INVALID DATABASE]
Solution: Verify ODOO_DB matches actual database name
```

---

## Performance Tuning

### Timeout Optimization

**Default:** 30 seconds

**Adjust based on:**
- Network latency: ping ODOO_URL
- Odoo server load: check Odoo CPU/memory
- Query complexity: simpler = faster

**Recommendations:**
- Local/LAN: 10-15 seconds
- WAN/Remote: 30-60 seconds
- Large exports: 120+ seconds

**Set timeout:**
```bash
export ODOO_TIMEOUT=60
python -m odoo_mcp
```

### Domain Optimization

**Good (indexed):**
```python
# Searches on indexed fields are fast
[["id", "=", 123]]
[["name", "ilike", "john"]]
```

**Slow (unindexed):**
```python
# Custom fields may not be indexed
[["x_custom_field", "=", "value"]]

# Complex multi-table joins
[["partner_id.country_id.name", "=", "France"]]
```

### Batch Operations

**Good (single RPC call):**
```python
odoo.write_records("res.partner", [1, 2, 3, 4, 5], values)
```

**Slow (multiple RPC calls):**
```python
for id in [1, 2, 3, 4, 5]:
    odoo.write_records("res.partner", [id], values)  # 5 RPC calls!
```

---

## Upgrade Guide

### From v0.0.2 to v0.0.3

**What's new:**
- Odoo 18 compatibility (user_ids field handling)
- Improved error messages
- Better configuration loading

**Upgrade steps:**
```bash
pip install --upgrade odoo-mcp
```

**Breaking changes:** None

**Migration needed:** None

---

## Getting Help

### Resources

- **GitHub Issues:** https://github.com/tuanle96/mcp-odoo/issues
- **Documentation:** ./docs/ (this directory)
- **README:** ./README.md

### Reporting Issues

**Include:**
1. Python version: `python --version`
2. Odoo version: From Odoo instance
3. Error message: Full traceback
4. Steps to reproduce
5. Configuration (sanitized): ODOO_URL, ODOO_DB, etc.

**Example:**
```
Python 3.10.5
Odoo 18.0.1
Error: "Connection timeout"
Steps: 
1. Set ODOO_URL=https://odoo.example.com
2. Set ODOO_DB=production
3. Run: python -m odoo_mcp
4. After 30s, get timeout error
```

