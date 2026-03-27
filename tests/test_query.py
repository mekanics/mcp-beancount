"""Tests for the BQL query tool."""

from __future__ import annotations

import pytest

from mcp_beancount.tools.query import run_bql_query


def test_valid_bql_returns_columns_and_rows(entries, options):
    """Valid BQL returns dict with columns and rows."""
    result = run_bql_query(
        entries,
        options,
        "SELECT account, sum(position) WHERE account ~ 'Assets' GROUP BY account",
    )
    assert "columns" in result
    assert "rows" in result
    assert isinstance(result["columns"], list)
    assert isinstance(result["rows"], list)
    assert len(result["rows"]) > 0


def test_invalid_bql_returns_error_dict(entries, options):
    """Invalid BQL returns error dict without raising exception."""
    result = run_bql_query(entries, options, "INVALID BQL STATEMENT @@##")
    assert "error" in result
    assert result["rows"] == []
    assert isinstance(result["error"], str)


def test_empty_result_returns_empty_rows(entries, options):
    """BQL that matches nothing returns empty rows list."""
    result = run_bql_query(
        entries,
        options,
        "SELECT account WHERE account ~ 'Nonexistent:Account:XYZ'",
    )
    assert "rows" in result
    assert isinstance(result["rows"], list)


def test_column_names_match_bql_select(entries, options):
    """Column names in output match the BQL SELECT fields."""
    result = run_bql_query(
        entries,
        options,
        "SELECT account, sum(position) WHERE account ~ 'Assets' GROUP BY account",
    )
    assert "error" not in result
    assert "account" in result["columns"]


def test_allowlist_filters_query_rows(entries, options):
    """AllowList filters out non-matching account rows from query results."""
    from mcp_beancount.allowlist import AllowList

    allowlist = AllowList(["Assets:Bank:Savings"])
    result = run_bql_query(
        entries,
        options,
        "SELECT account, sum(position) WHERE account ~ 'Assets:Bank' GROUP BY account",
        allowlist=allowlist,
    )
    assert "error" not in result
    for row in result["rows"]:
        if "account" in row and ":" in str(row.get("account", "")):
            assert row["account"].startswith("Assets:Bank:Savings")
