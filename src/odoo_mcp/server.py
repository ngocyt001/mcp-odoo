"""
MCP server for Odoo integration

Provides MCP tools and resources for interacting with Odoo ERP systems
"""

import json
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, AsyncIterator, Dict, List, Optional, Union, cast

from mcp.server.fastmcp import Context, FastMCP
from pydantic import BaseModel, Field

from . import postgres_client
from .odoo_client import OdooClient, get_odoo_client


@dataclass
class AppContext:
    """Application context for the MCP server"""

    odoo: OdooClient


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """
    Application lifespan for initialization and cleanup
    """
    # Initialize Odoo client on startup
    odoo_client = get_odoo_client()

    try:
        yield AppContext(odoo=odoo_client)
    finally:
        # No cleanup needed for Odoo client
        pass


# Create MCP server
mcp = FastMCP(
    "Odoo MCP Server",
    description="MCP Server for interacting with Odoo ERP systems (Odoo 16 / 18 / 19)",
    dependencies=["requests"],
    lifespan=app_lifespan,
)


# ----- MCP Resources -----


@mcp.resource(
    "odoo://models", description="List all available models in the Odoo system"
)
def get_models() -> str:
    """Lists all available models in the Odoo system"""
    odoo_client = get_odoo_client()
    models = odoo_client.get_models()
    return json.dumps(models, indent=2)


@mcp.resource(
    "odoo://model/{model_name}",
    description="Get detailed information about a specific model including fields",
)
def get_model_info(model_name: str) -> str:
    """
    Get information about a specific model

    Parameters:
        model_name: Name of the Odoo model (e.g., 'res.partner')
    """
    odoo_client = get_odoo_client()
    try:
        # Get model info
        model_info = odoo_client.get_model_info(model_name)

        # Get field definitions
        fields = odoo_client.get_model_fields(model_name)
        model_info["fields"] = fields

        return json.dumps(model_info, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


@mcp.resource(
    "odoo://record/{model_name}/{record_id}",
    description="Get detailed information of a specific record by ID",
)
def get_record(model_name: str, record_id: str) -> str:
    """
    Get a specific record by ID

    Parameters:
        model_name: Name of the Odoo model (e.g., 'res.partner')
        record_id: ID of the record
    """
    odoo_client = get_odoo_client()
    try:
        record_id_int = int(record_id)
        record = odoo_client.read_records(model_name, [record_id_int])
        if not record:
            return json.dumps(
                {"error": f"Record not found: {model_name} ID {record_id}"}, indent=2
            )
        return json.dumps(record[0], indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


@mcp.resource(
    "odoo://search/{model_name}/{domain}",
    description="Search for records matching the domain",
)
def search_records_resource(model_name: str, domain: str) -> str:
    """
    Search for records that match a domain

    Parameters:
        model_name: Name of the Odoo model (e.g., 'res.partner')
        domain: Search domain in JSON format (e.g., '[["name", "ilike", "test"]]')
    """
    odoo_client = get_odoo_client()
    try:
        # Parse domain from JSON string
        domain_list = json.loads(domain)

        # Set a reasonable default limit
        limit = 10

        # Perform search_read for efficiency
        results = odoo_client.search_read(model_name, domain_list, limit=limit)

        return json.dumps(results, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


# ----- Pydantic models for type safety -----


class DomainCondition(BaseModel):
    """A single condition in a search domain"""

    field: str = Field(description="Field name to search")
    operator: str = Field(
        description="Operator (e.g., '=', '!=', '>', '<', 'in', 'not in', 'like', 'ilike')"
    )
    value: Any = Field(description="Value to compare against")

    def to_tuple(self) -> List:
        """Convert to Odoo domain condition tuple"""
        return [self.field, self.operator, self.value]


class SearchDomain(BaseModel):
    """Search domain for Odoo models"""

    conditions: List[DomainCondition] = Field(
        default_factory=list,
        description="List of conditions for searching. All conditions are combined with AND operator.",
    )

    def to_domain_list(self) -> List[List]:
        """Convert to Odoo domain list format"""
        return [condition.to_tuple() for condition in self.conditions]


class EmployeeSearchResult(BaseModel):
    """Represents a single employee search result."""

    id: int = Field(description="Employee ID")
    name: str = Field(description="Employee name")


class SearchEmployeeResponse(BaseModel):
    """Response model for the search_employee tool."""

    success: bool = Field(description="Indicates if the search was successful")
    result: Optional[List[EmployeeSearchResult]] = Field(
        default=None, description="List of employee search results"
    )
    error: Optional[str] = Field(default=None, description="Error message, if any")


class Holiday(BaseModel):
    """Represents a single holiday."""

    display_name: str = Field(description="Display name of the holiday")
    start_datetime: str = Field(description="Start date and time of the holiday")
    stop_datetime: str = Field(description="End date and time of the holiday")
    employee_id: List[Union[int, str]] = Field(
        description="Employee ID associated with the holiday"
    )
    name: str = Field(description="Name of the holiday")
    state: str = Field(description="State of the holiday")


class SearchHolidaysResponse(BaseModel):
    """Response model for the search_holidays tool."""

    success: bool = Field(description="Indicates if the search was successful")
    result: Optional[List[Holiday]] = Field(
        default=None, description="List of holidays found"
    )
    error: Optional[str] = Field(default=None, description="Error message, if any")


# ----- MCP Tools -----


@mcp.tool(description="Execute a custom method on an Odoo model")
def execute_method(
    ctx: Context,
    model: str,
    method: str,
    args: List = None,
    kwargs: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Execute a custom method on an Odoo model

    Parameters:
        model: The model name (e.g., 'res.partner')
        method: Method name to execute
        args: Positional arguments
        kwargs: Keyword arguments

    Returns:
        Dictionary containing:
        - success: Boolean indicating success
        - result: Result of the method (if success)
        - error: Error message (if failure)
    """
    odoo = ctx.request_context.lifespan_context.odoo
    try:
        args = args or []
        kwargs = kwargs or {}

        # Special handling for search methods like search, search_count, search_read
        search_methods = ["search", "search_count", "search_read"]
        if method in search_methods and args:
            # Search methods usually have domain as the first parameter
            # args: [[domain], limit, offset, ...] or [domain, limit, offset, ...]
            normalized_args = list(
                args
            )  # Create a copy to avoid affecting the original args

            if len(normalized_args) > 0:
                # Process domain in args[0]
                domain = normalized_args[0]
                domain_list = []

                # Check if domain is wrapped unnecessarily ([domain] instead of domain)
                if (
                    isinstance(domain, list)
                    and len(domain) == 1
                    and isinstance(domain[0], list)
                ):
                    # Case [[domain]] - unwrap to [domain]
                    domain = domain[0]

                # Normalize domain similar to search_records function
                if domain is None:
                    domain_list = []
                elif isinstance(domain, dict):
                    if "conditions" in domain:
                        # Object format
                        conditions = domain.get("conditions", [])
                        domain_list = []
                        for cond in conditions:
                            if isinstance(cond, dict) and all(
                                k in cond for k in ["field", "operator", "value"]
                            ):
                                domain_list.append(
                                    [cond["field"], cond["operator"], cond["value"]]
                                )
                elif isinstance(domain, list):
                    # List format
                    if not domain:
                        domain_list = []
                    elif all(isinstance(item, list) for item in domain) or any(
                        item in ["&", "|", "!"] for item in domain
                    ):
                        domain_list = domain
                    elif len(domain) >= 3 and isinstance(domain[0], str):
                        # Case [field, operator, value] (not [[field, operator, value]])
                        domain_list = [domain]
                elif isinstance(domain, str):
                    # String format (JSON)
                    try:
                        parsed_domain = json.loads(domain)
                        if (
                            isinstance(parsed_domain, dict)
                            and "conditions" in parsed_domain
                        ):
                            conditions = parsed_domain.get("conditions", [])
                            domain_list = []
                            for cond in conditions:
                                if isinstance(cond, dict) and all(
                                    k in cond for k in ["field", "operator", "value"]
                                ):
                                    domain_list.append(
                                        [cond["field"], cond["operator"], cond["value"]]
                                    )
                        elif isinstance(parsed_domain, list):
                            domain_list = parsed_domain
                    except json.JSONDecodeError:
                        try:
                            import ast

                            parsed_domain = ast.literal_eval(domain)
                            if isinstance(parsed_domain, list):
                                domain_list = parsed_domain
                        except:
                            domain_list = []

                # Xác thực domain_list
                if domain_list:
                    valid_conditions = []
                    for cond in domain_list:
                        if isinstance(cond, str) and cond in ["&", "|", "!"]:
                            valid_conditions.append(cond)
                            continue

                        if (
                            isinstance(cond, list)
                            and len(cond) == 3
                            and isinstance(cond[0], str)
                            and isinstance(cond[1], str)
                        ):
                            valid_conditions.append(cond)

                    domain_list = valid_conditions

                # Cập nhật args với domain đã chuẩn hóa
                normalized_args[0] = domain_list
                args = normalized_args

                # Log for debugging
                print(f"Executing {method} with normalized domain: {domain_list}")

        result = odoo.execute_method(model, method, *args, **kwargs)
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool(description="Search for employees by name")
def search_employee(
    ctx: Context,
    name: str,
    limit: int = 20,
) -> SearchEmployeeResponse:
    """
    Search for employees by name using Odoo's name_search method.

    Parameters:
        name: The name (or part of the name) to search for.
        limit: The maximum number of results to return (default 20).

    Returns:
        SearchEmployeeResponse containing results or error information.
    """
    odoo = ctx.request_context.lifespan_context.odoo
    model = "hr.employee"
    method = "name_search"

    args = []
    kwargs = {"name": name, "limit": limit}

    try:
        result = odoo.execute_method(model, method, *args, **kwargs)
        parsed_result = [
            EmployeeSearchResult(id=item[0], name=item[1]) for item in result
        ]
        return SearchEmployeeResponse(success=True, result=parsed_result)
    except Exception as e:
        return SearchEmployeeResponse(success=False, error=str(e))


@mcp.tool(description="Search for holidays within a date range")
def search_holidays(
    ctx: Context,
    start_date: str,
    end_date: str,
    employee_id: Optional[int] = None,
) -> SearchHolidaysResponse:
    """
    Searches for holidays within a specified date range.

    Parameters:
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.
        employee_id: Optional employee ID to filter holidays.

    Returns:
        SearchHolidaysResponse:  Object containing the search results.
    """
    odoo = ctx.request_context.lifespan_context.odoo

    # Validate date format using datetime
    try:
        datetime.strptime(start_date, "%Y-%m-%d")
    except ValueError:
        return SearchHolidaysResponse(
            success=False, error="Invalid start_date format. Use YYYY-MM-DD."
        )
    try:
        datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        return SearchHolidaysResponse(
            success=False, error="Invalid end_date format. Use YYYY-MM-DD."
        )

    # Calculate adjusted start_date (subtract one day)
    start_date_dt = datetime.strptime(start_date, "%Y-%m-%d")
    adjusted_start_date_dt = start_date_dt - timedelta(days=1)
    adjusted_start_date = adjusted_start_date_dt.strftime("%Y-%m-%d")

    # Build the domain
    domain = [
        "&",
        ["start_datetime", "<=", f"{end_date} 22:59:59"],
        # Use adjusted date
        ["stop_datetime", ">=", f"{adjusted_start_date} 23:00:00"],
    ]
    if employee_id:
        domain.append(
            ["employee_id", "=", employee_id],
        )

    try:
        holidays = odoo.search_read(
            model_name="hr.leave.report.calendar",
            domain=domain,
        )
        parsed_holidays = [Holiday(**holiday) for holiday in holidays]
        return SearchHolidaysResponse(success=True, result=parsed_holidays)

    except Exception as e:
        err_str = str(e)
        if any(kw in err_str for kw in ("hr.leave", "report.calendar", "does not exist")):
            return SearchHolidaysResponse(
                success=False,
                error=(
                    "hr.leave module is not installed in this Odoo instance. "
                    "Install 'Time Off' (hr_holidays) to use this tool."
                ),
            )
        return SearchHolidaysResponse(success=False, error=err_str)


# ── Odoo 18 compatible tools ──────────────────────────────────────────────────
# Odoo 18 breaking changes vs 16/17:
#   - project.task: user_id (many2one) → user_ids (many2many)
#   - project.task: date_assign removed
#   - hr.leave: date_from/date_to → request_date_from/request_date_to


class Task(BaseModel):
    """A project task (Odoo 18 schema)."""

    id: int
    name: str
    project_id: Optional[Any] = None  # [id, name] or False
    stage_id: Optional[Any] = None    # [id, name] or False
    user_ids: Optional[List[Any]] = None  # list of [id, name]
    date_deadline: Optional[str] = None
    priority: Optional[str] = None
    active: Optional[bool] = None
    description: Optional[str] = None


class SearchTasksResponse(BaseModel):
    success: bool
    result: Optional[List[Task]] = None
    error: Optional[str] = None


class Project(BaseModel):
    """A project record."""

    id: int
    name: str
    partner_id: Optional[Any] = None  # customer
    user_id: Optional[Any] = None     # project manager
    date_start: Optional[str] = None
    date: Optional[str] = None        # deadline
    active: Optional[bool] = None
    task_count: Optional[int] = None


class SearchProjectsResponse(BaseModel):
    success: bool
    result: Optional[List[Project]] = None
    error: Optional[str] = None


# Safe field list for project.task on Odoo 18
_TASK_FIELDS = [
    "id", "name", "project_id", "stage_id",
    "user_ids", "date_deadline", "priority", "active", "description",
]

# Safe field list for project.project on Odoo 18
_PROJECT_FIELDS = [
    "id", "name", "partner_id", "user_id",
    "date_start", "date", "active", "task_count",
]


@mcp.tool(description="Search project tasks (Odoo 18 compatible). Use this instead of execute_method for project.task.")
def search_tasks(
    ctx: Context,
    project_id: Optional[int] = None,
    stage_name: Optional[str] = None,
    active_only: bool = True,
    limit: int = 50,
) -> SearchTasksResponse:
    """
    Search project tasks using Odoo 18 field names.

    Parameters:
        project_id: Filter by project ID (None = all projects).
        stage_name: Filter by stage name (partial, case-insensitive).
        active_only: Only return active tasks (default True).
        limit: Max records to return (default 50).
    """
    odoo = ctx.request_context.lifespan_context.odoo
    try:
        domain: List[Any] = []
        if active_only:
            domain.append(["active", "=", True])
        if project_id is not None:
            domain.append(["project_id", "=", project_id])
        if stage_name:
            domain.append(["stage_id.name", "ilike", stage_name])

        records = odoo.search_read(
            model_name="project.task",
            domain=domain,
            fields=_TASK_FIELDS,
            limit=limit,
        )
        tasks = [Task(**r) for r in records]
        return SearchTasksResponse(success=True, result=tasks)
    except Exception as e:
        return SearchTasksResponse(success=False, error=str(e))


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


@mcp.tool(description="Search projects. Use this to list or look up projects.")
def search_projects(
    ctx: Context,
    name: Optional[str] = None,
    active_only: bool = True,
    limit: int = 20,
) -> SearchProjectsResponse:
    """
    Search project.project records.

    Parameters:
        name: Filter by name (partial, case-insensitive).
        active_only: Only return active projects (default True).
        limit: Max records to return (default 20).
    """
    odoo = ctx.request_context.lifespan_context.odoo
    try:
        domain: List[Any] = []
        if active_only:
            domain.append(["active", "=", True])
        if name:
            domain.append(["name", "ilike", name])

        records = odoo.search_read(
            model_name="project.project",
            domain=domain,
            fields=_PROJECT_FIELDS,
            limit=limit,
        )
        projects = [Project(**r) for r in records]
        return SearchProjectsResponse(success=True, result=projects)
    except Exception as e:
        return SearchProjectsResponse(success=False, error=str(e))


# ── Direct PostgreSQL access tools ───────────────────────────────────────────
# Bypasses XML-RPC for complex queries or data not exposed via Odoo API.
# SECURITY: Only SELECT queries are permitted (enforced in postgres_client).
# NOTE: task_count is a computed ORM field — not in project_project DB schema.
#       Use: SELECT COUNT(*) FROM project_task WHERE project_id = <id>


@mcp.tool(
    description="Execute a read-only SQL SELECT query directly on the Odoo PostgreSQL database."
)
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
        if "LIMIT" not in sql.upper():
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
