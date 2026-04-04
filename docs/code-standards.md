# Code Standards — odoo-mcp

## Overview

This document defines the coding standards, conventions, and best practices for the odoo-mcp project. All contributors must follow these standards to maintain code quality, consistency, and maintainability.

---

## Python Version & Dependencies

| Standard | Value |
|----------|-------|
| **Minimum Python** | 3.10 |
| **Target Python** | 3.10+ |
| **Style Guide** | PEP 8 (Black enforced) |
| **Type Checking** | mypy (strict mode) |
| **Formatter** | black (line-length 88) |
| **Linter** | ruff |
| **Import Sorter** | isort (black profile) |

---

## Code Structure

### File Organization

**Source Layout:**
```
src/odoo_mcp/
├── __init__.py           — Empty or minimal (re-exports)
├── __main__.py           — CLI entry point only
├── server.py             — MCP server, tools, resources, Pydantic models
├── odoo_client.py        — XML-RPC client, transport, config loading
```

**Guidelines:**
- One main responsibility per file
- Keep files under 600 LOC for readability (target: 400-500)
- Group related classes/functions by logical domain
- Use module docstrings to explain purpose

**File Naming:**
- Use `snake_case.py` for Python modules
- Use descriptive names: `odoo_client.py` not `client.py`
- Avoid single-letter or cryptic abbreviations

### Module Docstrings

**Required:**
```python
"""
One-sentence module purpose.

Longer description if needed:
- Key responsibility 1
- Key responsibility 2
"""
```

**Example (server.py):**
```python
"""
MCP server for Odoo integration

Provides MCP tools and resources for interacting with Odoo ERP systems
"""
```

---

## Naming Conventions

| Category | Convention | Example |
|----------|-----------|---------|
| **Modules** | snake_case | `odoo_client.py`, `server.py` |
| **Classes** | PascalCase | `OdooClient`, `AppContext`, `SearchDomain` |
| **Functions** | snake_case | `get_models()`, `execute_method()` |
| **Constants** | UPPER_SNAKE_CASE | `DEFAULT_TIMEOUT = 30` |
| **Private** | `_leading_underscore` | `_connect()`, `_execute()` |
| **Protected** | `__dunder__` (rarely) | `__init__()`, `__str__()` |
| **Methods** | snake_case | `search_read()`, `get_model_info()` |
| **Variables** | snake_case | `model_name`, `domain_list` |
| **Booleans** | `is_*`, `has_*` | `is_https`, `verify_ssl` |

**Rationale:**
- Follows PEP 8 conventions
- Improves code readability and discoverability
- Matches Python ecosystem standards

---

## Type Hints

### Requirements

**Mandatory for:**
- All public function signatures
- All class method signatures
- All Pydantic model fields
- Return types (even if `None`)

**Example (correct):**
```python
def search_employee(
    ctx: Context,
    name: str,
    limit: int = 20
) -> Dict[str, Any]:
    """Search employees by name"""
    ...

def _connect(self) -> None:
    """Initialize the XML-RPC connection"""
    ...
```

### Common Patterns

**Optional Values:**
```python
from typing import Optional

# Function parameter
def search_holidays(
    ctx: Context,
    start_date: str,
    end_date: str,
    employee_id: Optional[int] = None
) -> Dict[str, Any]:
    ...

# Model field
class Holiday(BaseModel):
    name: str
    description: Optional[str] = None
```

**Union Types:**
```python
from typing import Union

# Multiple valid types
def normalize_domain(domain: Union[str, list, dict]) -> List[List]:
    ...

# Odoo fields can be ID or display tuple
employee_id: Union[int, str]
```

**Generic Collections:**
```python
from typing import List, Dict

def get_models(self) -> Dict[str, List[str]]:
    return {
        "model_names": ["res.partner", "sale.order"],
        "details": {}
    }
```

**Callable Types:**
```python
from typing import Callable

def register_handler(handler: Callable[[str], bool]) -> None:
    ...
```

### Type Checker Configuration

**mypy settings (pyproject.toml):**
```toml
[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
```

**Enforcement:**
- Run before commit: `mypy src/`
- CI/CD pipeline validates all PRs
- Type errors block merge

---

## Pydantic Models

### BaseModel Usage

**Purpose:**
- Request/response validation for MCP tools
- Schema documentation (via Field descriptions)
- Type safety without runtime overhead

**Pattern:**
```python
from pydantic import BaseModel, Field
from typing import List, Optional, Any

class EmployeeSearchResult(BaseModel):
    """Single employee search result"""
    id: int = Field(description="Employee ID")
    name: str = Field(description="Employee name")

class SearchEmployeeResponse(BaseModel):
    """Response from search_employee tool"""
    success: bool = Field(description="Search succeeded")
    result: Optional[List[EmployeeSearchResult]] = Field(
        default=None,
        description="List of matching employees"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if search failed"
    )
```

**Field Descriptions:**
- Required for all fields
- Should be concise (1-2 sentences)
- Explain type, constraints, and purpose
- Helps with API documentation (OpenAPI)

**Inheritance:**
- Use `BaseModel` directly for top-level schemas
- Reuse model composition over inheritance
- Group related fields in nested models

**Validation:**
- Rely on Pydantic for JSON parsing
- Use custom validators sparingly
- Document any custom logic

---

## Error Handling

### Exception Hierarchy

**Standard exceptions (stdlib):**
```python
# Invalid input
raise ValueError("Authentication failed: Invalid credentials")

# Network issues
raise ConnectionError("Failed to connect to Odoo server: timeout")

# Logic errors (rare)
raise RuntimeError("Unexpected state in XML-RPC transport")
```

**Avoid custom exceptions** unless domain-specific (none needed currently).

### Try/Except Patterns

**Resource handlers (logging to JSON):**
```python
@mcp.resource("odoo://record/{model_name}/{record_id}")
def get_record(model_name: str, record_id: str) -> str:
    odoo_client = get_odoo_client()
    try:
        record_id_int = int(record_id)
        record = odoo_client.read_records(model_name, [record_id_int])
        if not record:
            return json.dumps({"error": "Record not found"}, indent=2)
        return json.dumps(record[0], indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)
```

**Tool handlers (return dict):**
```python
@mcp.tool(description="Execute a method on an Odoo model")
def execute_method(
    ctx: Context,
    model: str,
    method: str,
    args: List = None,
    kwargs: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    try:
        odoo = ctx.request_context.lifespan_context.odoo
        result = odoo.execute_method(model, method, *(args or []), **(kwargs or {}))
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

**Constructor (let exceptions propagate):**
```python
def __init__(self, url: str, db: str, username: str, password: str) -> None:
    """Initialize Odoo client (may raise ConnectionError or ValueError)"""
    self.url = url
    self.db = db
    self.username = username
    self.password = password
    self._connect()  # Raises ConnectionError on failure
```

### Logging

**Destination:** stderr (stdout reserved for MCP protocol)

**Levels:**
- `print(..., file=sys.stderr)` for startup/shutdown info
- Logging module for request debugging
- Mask sensitive values (passwords, tokens)

**Example:**
```python
import os
import sys

# Startup logging
print(f"Connecting to Odoo at: {self.url}", file=os.sys.stderr)

# Mask sensitive values
if key == "ODOO_PASSWORD":
    print(f"  {key}: ***hidden***", file=os.sys.stderr)

# Error logging
print(f"Error retrieving models: {str(e)}", file=os.sys.stderr)
```

---

## Formatting & Style

### Black Configuration

**Settings (pyproject.toml):**
```toml
[tool.black]
line-length = 88
target-version = ["py310"]
```

**Before commit:**
```bash
black src/ run_server.py
```

### Import Ordering (isort)

**Settings (pyproject.toml):**
```toml
[tool.isort]
profile = "black"
line_length = 88
```

**Order:**
1. Future imports (`from __future__ import ...`)
2. Standard library (`import sys`, `from datetime import ...`)
3. Third-party (`import requests`, `from mcp import ...`)
4. Local (`from .server import ...`, `from .odoo_client import ...`)

**Example:**
```python
from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import Context, FastMCP
from pydantic import BaseModel, Field

from .odoo_client import OdooClient, get_odoo_client
```

### Line Length & Readability

**Limit:** 88 characters (Black default)

**When to break lines:**
```python
# Long function call
result = odoo_client.search_read(
    model_name,
    domain_list,
    fields=fields,
    offset=offset,
    limit=limit,
    order=order
)

# Long type hint
def method(
    param1: str,
    param2: int,
    param3: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    ...
```

### Spacing & Indentation

**Indentation:** 4 spaces (no tabs)

**Blank lines:**
- 2 blank lines between top-level classes/functions
- 1 blank line between methods in a class
- Minimal blanks within function bodies

**Example:**
```python
class OdooClient:
    """XML-RPC client for Odoo"""

    def __init__(self, url: str) -> None:
        """Initialize client"""
        self.url = url

    def _connect(self) -> None:
        """Setup connection"""
        pass


def get_odoo_client() -> OdooClient:
    """Get or create Odoo client singleton"""
    pass
```

---

## Comments & Documentation

### Docstrings

**Format:** Google-style (3-quote blocks)

**Module-level:**
```python
"""
Brief one-liner.

Longer description explaining purpose and key concepts.
- Feature 1
- Feature 2
"""
```

**Function-level:**
```python
def search_employee(
    ctx: Context,
    name: str,
    limit: int = 20
) -> Dict[str, Any]:
    """
    Search employees by name.

    Parameters:
        name: Employee name or partial match
        limit: Maximum number of results (default 20)

    Returns:
        Dictionary with keys:
        - success (bool): Search succeeded
        - result (list): Matching employees [{"id": int, "name": str}, ...]
        - error (str): Error message if failed
    """
```

**Class-level:**
```python
class OdooClient:
    """
    Client for interacting with Odoo via XML-RPC.

    Handles authentication, model introspection, and method execution.
    """
```

### Inline Comments

**Use sparingly.** Only for non-obvious logic:

```python
# Unwrap unnecessarily nested domain: [[domain]] → [domain]
if (isinstance(domain, list) and len(domain) == 1 and
    isinstance(domain[0], list)):
    domain = domain[0]
```

**Avoid obvious comments:**
```python
# BAD: Converts string to integer
record_id_int = int(record_id)

# GOOD: (no comment needed)
record_id_int = int(record_id)
```

---

## Testing Standards

### Current Status

**No automated test suite.** Testing approach:
1. Manual integration tests against real Odoo instance
2. Type checking via mypy (enforced in CI)
3. Code formatting via black/isort (enforced in pre-commit)

### Future Testing Strategy

When adding automated tests:

**Test file naming:**
```
tests/
├── test_server.py          # Test MCP tools/resources
├── test_odoo_client.py     # Test XML-RPC client
└── conftest.py             # Fixtures
```

**Pytest conventions:**
```python
def test_search_employee_returns_list():
    """Test that search_employee returns list of results"""
    ...

def test_execute_method_with_invalid_model_raises_error():
    """Test that invalid model name raises ValueError"""
    ...

class TestOdooClient:
    """Tests for OdooClient class"""

    def test_connect_with_invalid_credentials_raises_error(self):
        """Test connection failure handling"""
        ...
```

---

## Security Considerations

### Secrets Management

**Rules:**
1. Never hardcode credentials in source
2. Use environment variables or config files
3. Mask passwords in logs and error messages
4. Never commit `.env` files or `odoo_config.json`

**Configuration Loading (Priority):**
```
1. Environment variables (ODOO_URL, ODOO_DB, etc.)
2. ~/.config/odoo/config.json
3. ~/.odoo_config.json
4. ./odoo_config.json (local, not in git)
```

### Input Validation

**Pydantic Validation:**
- All tool inputs validated via BaseModel
- Type coercion automatic (string → int if needed)
- Custom validators for domain format

**Example:**
```python
class DomainCondition(BaseModel):
    field: str
    operator: str
    value: Any

    def to_tuple(self) -> List:
        """Convert to Odoo domain tuple"""
        if self.operator not in ["=", "!=", ">", "<", "in", "not in"]:
            raise ValueError(f"Invalid operator: {self.operator}")
        return [self.field, self.operator, self.value]
```

### SSL/TLS

**Default:** Verification enabled (`verify_ssl=true`)

**Disable only for testing:**
```python
client = OdooClient(
    url="http://localhost:8069",
    db="test",
    username="admin",
    password="admin",
    verify_ssl=False  # Testing only
)
```

---

## Performance Optimization

### Caching

**No explicit caching currently.** Odoo client is stateless per-request.

**Future optimization:**
- Cache model metadata (`get_models()`) with TTL
- Cache field definitions (`get_model_fields()`) locally
- Implement request deduplication for high-volume queries

### Timeout Management

**Default:** 30 seconds (configurable)

**Adjust for:**
- Slow networks: increase to 60+
- Fast local dev: decrease to 10
- Large exports: increase to 120

**Example:**
```python
client = OdooClient(
    url="https://odoo.example.com",
    db="production",
    username="api_user",
    password="api_key",
    timeout=60  # Slower remote instance
)
```

### Batch Operations

**Recommended for bulk updates:**
```python
# Good: Single RPC call with bulk IDs
odoo.write_records("res.partner", [1, 2, 3, 4, 5], {"active": False})

# Avoid: Multiple RPC calls in loop
for id in [1, 2, 3, 4, 5]:
    odoo.write_records("res.partner", [id], {"active": False})
```

---

## Pre-Commit Checklist

Before committing code:

- [ ] Run `black src/ run_server.py` (formatting)
- [ ] Run `isort src/ run_server.py` (import order)
- [ ] Run `mypy src/` (type checking)
- [ ] Run `ruff check src/` (linting)
- [ ] Verify no secrets/credentials in files
- [ ] Update docstrings for new functions
- [ ] Test manually against Odoo instance (if possible)
- [ ] Update CHANGELOG.md with changes

---

## Odoo Version Compatibility

### Target Versions
- **Minimum:** Odoo 13
- **Maximum:** Odoo 18+
- **Actively tested:** Odoo 16-18

### Breaking Changes Handling

**Odoo 18 (user_ids vs user_id):**
```python
# Odoo < 18: user_id (many2one)
domain = [("user_id", "=", user_id)]

# Odoo >= 18: user_ids (many2many)
domain = [("user_ids", "in", [user_id])]

# Handle in code:
if hasattr(fields.get("user_ids"), "string"):
    field_name = "user_ids"
else:
    field_name = "user_id"
```

**Version Detection:**
- Use `ir.model.fields` to detect field availability
- Document breaking changes in comments
- Add fallback logic where feasible

---

## Documentation Standards

### Code Comments
- Explain **why**, not **what** (code is self-documenting for "what")
- Keep comments up-to-date with code changes
- Use proper grammar and punctuation

### API Documentation
- Update README.md for new tools/resources
- Add docstrings matching tool description
- Include examples for complex features
- Keep parameter documentation in sync

---

## Release & Versioning

**Format:** Semantic versioning (MAJOR.MINOR.PATCH)

**Current:** 0.0.3

**Increment when:**
- MAJOR: Breaking changes to API or Odoo compatibility
- MINOR: New tools, features, backward-compatible
- PATCH: Bug fixes, security patches

**Before release:**
1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Create git tag: `v0.0.3`
4. Push to GitHub (triggers PyPI publish via GitHub Actions)

