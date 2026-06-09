"""
In-memory DuckDB layer for the telecom device dataset.

Responsibilities:
- Load the bundled CSV into a single in-memory DuckDB connection at startup.
- Expose schema introspection and aggregate helpers.
- Provide a guarded `safe_execute` that only allows read-only SELECT/WITH
  queries and enforces a hard row limit.
"""

from __future__ import annotations

import logging
import os
import re
import threading
from pathlib import Path
from typing import Any

import duckdb

logger = logging.getLogger(__name__)

# ── Configuration ───────────────────────────────────────────────────

TABLE_NAME = "devices"
DEFAULT_MAX_ROWS = 10_000
ABSOLUTE_MAX_ROWS = 50_000

# Resolve CSV path: env override > /app/data (Docker) > repo path (local dev)
_DEFAULT_CSV_CANDIDATES = [
    Path("/app/data/telecom_device_analysis_dummy_data.csv"),
    Path(__file__).resolve().parent.parent.parent
    / "data"
    / "telecom_device_analysis_dummy_data.csv",
]


def _resolve_csv_path() -> Path:
    env_path = os.environ.get("TELECOM_CSV_PATH")
    if env_path:
        p = Path(env_path)
        if p.is_file():
            return p
        raise FileNotFoundError(f"TELECOM_CSV_PATH does not exist: {env_path}")
    for candidate in _DEFAULT_CSV_CANDIDATES:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        "Could not locate telecom CSV in any default location: "
        + ", ".join(str(c) for c in _DEFAULT_CSV_CANDIDATES)
    )


# ── Connection management ───────────────────────────────────────────

_conn: duckdb.DuckDBPyConnection | None = None
_init_lock = threading.Lock()


def init_db() -> duckdb.DuckDBPyConnection:
    """Create the in-memory DB and load the CSV. Idempotent."""
    global _conn
    if _conn is not None:
        return _conn
    with _init_lock:
        if _conn is not None:
            return _conn
        csv_path = _resolve_csv_path()
        logger.info("Initialising in-memory DuckDB from CSV: %s", csv_path)
        conn = duckdb.connect(database=":memory:")
        # Reduce memory footprint for analytical workloads
        conn.execute("PRAGMA threads=4")
        # Load CSV with auto-detected types; dates auto-detected as DATE
        conn.execute(
            f"""
            CREATE TABLE {TABLE_NAME} AS
            SELECT * FROM read_csv_auto(?, header=True);
            """,
            [str(csv_path)],
        )
        row_count = conn.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}").fetchone()[0]
        logger.info("Loaded %d rows into table '%s'", row_count, TABLE_NAME)
        _conn = conn
        return _conn


def get_conn() -> duckdb.DuckDBPyConnection:
    if _conn is None:
        return init_db()
    return _conn


def get_row_count() -> int:
    conn = get_conn()
    return conn.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}").fetchone()[0]


def get_schema() -> list[dict[str, Any]]:
    """Return list of {name, type, nullable} for the devices table."""
    conn = get_conn()
    rows = conn.execute(f"PRAGMA table_info('{TABLE_NAME}')").fetchall()
    cols = [d[0] for d in conn.description]
    return [dict(zip(cols, r)) for r in rows]


def get_sample(limit: int = 5) -> list[dict[str, Any]]:
    """Return first N rows for LLM context."""
    return _rows_to_dicts(get_conn().execute(f"SELECT * FROM {TABLE_NAME} LIMIT {int(limit)}"))


# ── Safety: read-only SQL validation ────────────────────────────────

_FORBIDDEN_PATTERN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|ATTACH|DETACH|COPY|"
    r"PRAGMA|INSTALL|LOAD|EXPORT|IMPORT|VACUUM|CHECKPOINT|TRUNCATE|"
    r"GRANT|REVOKE|SET|RESET|CALL|USE)\b",
    re.IGNORECASE,
)
_ALLOWED_FIRST_KEYWORD = re.compile(r"^\s*(SELECT|WITH)\b", re.IGNORECASE)


class SQLValidationError(ValueError):
    """Raised when a SQL string fails the read-only safety checks."""


def _strip_sql_comments(sql: str) -> str:
    """Remove -- line comments and /* block */ comments."""
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    sql = re.sub(r"--[^\n]*", " ", sql)
    return sql


def validate_sql(sql: str) -> str:
    """Return the trimmed SQL if safe; otherwise raise SQLValidationError."""
    if not isinstance(sql, str) or not sql.strip():
        raise SQLValidationError("SQL must be a non-empty string")
    trimmed = sql.strip().rstrip(";").strip()
    if ";" in trimmed:
        raise SQLValidationError("Multiple statements are not allowed")
    cleaned = _strip_sql_comments(trimmed)
    if not _ALLOWED_FIRST_KEYWORD.match(cleaned):
        raise SQLValidationError("Only SELECT or WITH queries are allowed")
    forbidden = _FORBIDDEN_PATTERN.search(cleaned)
    if forbidden:
        raise SQLValidationError(
            f"Disallowed keyword in SQL: {forbidden.group(0).upper()}"
        )
    return trimmed


def _rows_to_dicts(cursor: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    cols = [d[0] for d in cursor.description] if cursor.description else []
    rows = cursor.fetchall()
    return [
        {c: _to_jsonable(v) for c, v in zip(cols, row)}
        for row in rows
    ]


def _to_jsonable(value: Any) -> Any:
    """Convert DuckDB return types into JSON-serialisable Python primitives."""
    import datetime
    import decimal

    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (datetime.date, datetime.datetime, datetime.time)):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    return str(value)


def safe_execute(
    sql: str,
    params: list[Any] | None = None,
    max_rows: int = DEFAULT_MAX_ROWS,
) -> dict[str, Any]:
    """Validate then execute a read-only query.

    Returns a dict with `columns`, `rows`, `row_count`, `truncated`, `sql`.
    Raises `SQLValidationError` for unsafe input.
    DuckDB errors propagate as `duckdb.Error`.
    """
    if max_rows is None or max_rows <= 0:
        max_rows = DEFAULT_MAX_ROWS
    max_rows = min(int(max_rows), ABSOLUTE_MAX_ROWS)

    safe_sql = validate_sql(sql)

    # Wrap user query so we cap rows even if they forget LIMIT.
    # Fetch one extra row to detect truncation.
    fetch_limit = max_rows + 1
    wrapped = f"SELECT * FROM ({safe_sql}) AS _user_q LIMIT {fetch_limit}"

    conn = get_conn()
    cursor = conn.execute(wrapped, params or [])
    rows = cursor.fetchall()
    cols = [d[0] for d in cursor.description] if cursor.description else []

    truncated = len(rows) > max_rows
    if truncated:
        rows = rows[:max_rows]

    serialised = [
        {c: _to_jsonable(v) for c, v in zip(cols, row)}
        for row in rows
    ]
    return {
        "columns": cols,
        "rows": serialised,
        "row_count": len(serialised),
        "truncated": truncated,
        "max_rows": max_rows,
        "sql": safe_sql,
    }


# ── High-level helpers used by MCP tools ────────────────────────────

_ALLOWED_GROUP_BY = {
    "Manufacturer",
    "Model_Name",
    "Network_Type",
    "OS_Version",
    "Top_App_Category",
    "Subsidy_Type",
    "Preferred_Channel",
    "Bundling_Status",
    "Biometric_Type",
    "Storage_Capacity_GB",
    "Wireless_Charging",
    "Device_Insurance",
    "Trade_in_Program",
}

_ALLOWED_FILTER_COLUMNS = {
    "Manufacturer": "string",
    "Model_Name": "string",
    "Model_Code": "string",
    "Network_Type": "string",
    "OS_Version": "string",
    "Top_App_Category": "string",
    "Subsidy_Type": "string",
    "Preferred_Channel": "string",
    "Bundling_Status": "string",
    "Biometric_Type": "string",
}


def list_devices(
    manufacturer: str | None = None,
    model_name: str | None = None,
    network_type: str | None = None,
    os_version: str | None = None,
    min_battery_health: float | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Filtered SELECT against the devices table."""
    where: list[str] = []
    params: list[Any] = []
    if manufacturer:
        where.append("Manufacturer = ?")
        params.append(manufacturer)
    if model_name:
        where.append("Model_Name = ?")
        params.append(model_name)
    if network_type:
        where.append("Network_Type = ?")
        params.append(network_type)
    if os_version:
        where.append("OS_Version = ?")
        params.append(os_version)
    if min_battery_health is not None:
        where.append("Battery_Health_Pct >= ?")
        params.append(float(min_battery_health))

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    capped = max(1, min(int(limit), 500))
    sql = f"SELECT * FROM {TABLE_NAME} {where_sql} LIMIT {capped}"
    cursor = get_conn().execute(sql, params)
    cols = [d[0] for d in cursor.description]
    rows = cursor.fetchall()
    return {
        "columns": cols,
        "rows": [
            {c: _to_jsonable(v) for c, v in zip(cols, row)} for row in rows
        ],
        "row_count": len(rows),
        "filters_applied": dict(
            zip(
                [
                    "manufacturer",
                    "model_name",
                    "network_type",
                    "os_version",
                    "min_battery_health",
                ],
                [manufacturer, model_name, network_type, os_version, min_battery_health],
            )
        ),
    }


def device_stats(
    group_by: str,
    metrics: list[str] | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Aggregate the devices table grouped by a whitelisted column."""
    if group_by not in _ALLOWED_GROUP_BY:
        raise SQLValidationError(
            f"group_by must be one of: {sorted(_ALLOWED_GROUP_BY)}"
        )

    metric_sql_map = {
        "count": "COUNT(*) AS count",
        "avg_battery_health": "ROUND(AVG(Battery_Health_Pct), 2) AS avg_battery_health",
        "avg_data_usage": "ROUND(AVG(Avg_Data_Usage_GB), 2) AS avg_data_usage",
        "avg_launch_price": "ROUND(AVG(Launch_Price), 0) AS avg_launch_price",
        "avg_months_in_use": "ROUND(AVG(Months_in_Use), 1) AS avg_months_in_use",
        "avg_brand_loyalty": "ROUND(AVG(Brand_Loyalty_Score), 2) AS avg_brand_loyalty",
        "total_remaining_installment": "SUM(Remaining_Installment) AS total_remaining_installment",
        "avg_repair_history": "ROUND(AVG(Repair_History_Count), 2) AS avg_repair_history",
    }
    if not metrics:
        metrics = ["count", "avg_battery_health", "avg_data_usage", "avg_launch_price"]
    selected = []
    for m in metrics:
        if m not in metric_sql_map:
            raise SQLValidationError(
                f"Unknown metric '{m}'. Allowed: {sorted(metric_sql_map)}"
            )
        selected.append(metric_sql_map[m])

    capped = max(1, min(int(limit), 200))
    sql = (
        f"SELECT {group_by}, {', '.join(selected)} "
        f"FROM {TABLE_NAME} GROUP BY {group_by} "
        f"ORDER BY count DESC NULLS LAST LIMIT {capped}"
        if "count" in metrics
        else (
            f"SELECT {group_by}, {', '.join(selected)} "
            f"FROM {TABLE_NAME} GROUP BY {group_by} LIMIT {capped}"
        )
    )
    cursor = get_conn().execute(sql)
    cols = [d[0] for d in cursor.description]
    rows = cursor.fetchall()
    return {
        "group_by": group_by,
        "metrics": metrics,
        "columns": cols,
        "rows": [
            {c: _to_jsonable(v) for c, v in zip(cols, row)} for row in rows
        ],
        "row_count": len(rows),
        "sql": sql,
    }


def get_table_overview() -> dict[str, Any]:
    """Schema + sample rows + row count, useful for LLMs generating SQL."""
    return {
        "table": TABLE_NAME,
        "row_count": get_row_count(),
        "columns": get_schema(),
        "allowed_group_by": sorted(_ALLOWED_GROUP_BY),
        "sample_rows": get_sample(5),
    }
