"""query tool — execute BQL (Beancount Query Language) statements."""

from __future__ import annotations

import datetime
from typing import Any

from mcp_beancount.allowlist import AllowList


def run_bql_query(
    entries: list[Any],
    options: dict[str, Any],
    bql: str,
    allowlist: AllowList | None = None,
) -> dict[str, Any]:
    """Execute a BQL query and return results as columns + rows.

    Uses beanquery (beancount 3.x) for query execution.

    Args:
        entries: Beancount entries from loader.get().
        options: Beancount options dict.
        bql: BQL query string.
        allowlist: Optional AllowList; filters rows where any column value
                   looks like an account name and doesn't match.

    Returns:
        dict with:
          - "columns": list of column name strings
          - "rows": list of dicts mapping column name → value (as string)
        On error:
          - "error": error message string
          - "rows": []
    """
    if allowlist is None:
        allowlist = AllowList([])

    try:
        import beanquery
        from beanquery.sources.beancount import attach

        conn = beanquery.connect("")
        attach(conn, "beancount:", entries=entries, errors=[], options=options)
        cursor = conn.execute(bql)
    except Exception as exc:
        return {"error": str(exc), "rows": []}

    if cursor.description is None:
        return {"columns": [], "rows": []}

    columns = [col.name for col in cursor.description]

    rows: list[dict[str, Any]] = []
    try:
        for row in cursor:
            row_dict: dict[str, Any] = {}
            for col_name, value in zip(columns, row):
                row_dict[col_name] = _serialize_value(value)
            rows.append(row_dict)
    except Exception as exc:
        return {"error": str(exc), "rows": []}

    # Apply allowlist: filter rows where any value is an account-like string
    if not allowlist.is_empty():
        rows = _filter_rows_by_allowlist(rows, columns, allowlist)

    return {"columns": columns, "rows": rows}


def _serialize_value(value: Any) -> Any:
    """Convert beancount query result values to JSON-serializable types."""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime.date):
        return value.isoformat()
    # beancount Inventory, Amount, Position objects — convert to str
    return str(value)


def _filter_rows_by_allowlist(
    rows: list[dict[str, Any]],
    columns: list[str],
    allowlist: AllowList,
) -> list[dict[str, Any]]:
    """Filter rows based on allowlist, checking account-like columns."""
    account_cols = [
        col for col in columns
        if "account" in col.lower()
    ]
    if not account_cols:
        return rows

    filtered = []
    for row in rows:
        keep = True
        for col in account_cols:
            val = row.get(col)
            if isinstance(val, str) and ":" in val:
                if not allowlist.allows(val):
                    keep = False
                    break
        if keep:
            filtered.append(row)
    return filtered
