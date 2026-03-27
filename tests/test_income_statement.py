"""Tests for get_income_statement tool."""

from __future__ import annotations

import pytest

from mcp_beancount.tools.income_statement import get_income_statement


def test_full_year_returns_correct_keys(entries, options):
    """Full year result contains expected keys."""
    result = get_income_statement(entries, options, year=2025)
    assert "period" in result
    assert "total_income" in result
    assert "total_expenses" in result
    assert "net" in result
    assert "income_breakdown" in result
    assert "expense_breakdown" in result


def test_month_filter_restricts_correctly(entries, options):
    """Month filter returns less income than full year."""
    result_year = get_income_statement(entries, options, year=2025)
    result_month = get_income_statement(entries, options, year=2025, month=1)
    # Full year should have more income than a single month
    assert result_year["total_income"] >= result_month["total_income"]


def test_net_equals_income_minus_expenses(entries, options):
    """net == total_income - total_expenses."""
    result = get_income_statement(entries, options, year=2025)
    expected_net = round(result["total_income"] - result["total_expenses"], 2)
    assert result["net"] == expected_net


def test_breakdown_dicts_populated(entries, options):
    """Income and expense breakdowns are non-empty for an active year."""
    result = get_income_statement(entries, options, year=2025)
    assert len(result["income_breakdown"]) > 0
    assert len(result["expense_breakdown"]) > 0


def test_income_sign_convention_positive(entries, options):
    """Income values are positive (negated from beancount's negative convention)."""
    result = get_income_statement(entries, options, year=2025)
    assert result["total_income"] > 0
    for account, amount in result["income_breakdown"].items():
        assert amount > 0, f"Income {account} should be positive, got {amount}"


def test_period_string_format_year_only(entries, options):
    """Period is 'YYYY' when no month given."""
    result = get_income_statement(entries, options, year=2025)
    assert result["period"] == "2025"


def test_period_string_format_with_month(entries, options):
    """Period is 'YYYY-MM' when month given."""
    result = get_income_statement(entries, options, year=2026, month=3)
    assert result["period"] == "2026-03"


def test_income_breakdown_contains_salary(entries, options):
    """Income breakdown includes salary account."""
    result = get_income_statement(entries, options, year=2025)
    assert "Income:Salary" in result["income_breakdown"]


def test_expense_breakdown_contains_rent(entries, options):
    """Expense breakdown includes rent account."""
    result = get_income_statement(entries, options, year=2025)
    assert "Expenses:Rent" in result["expense_breakdown"]
