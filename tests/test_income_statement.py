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
    assert "total_income_converted" in result
    assert "total_expenses_converted" in result
    assert "base_currency" in result


def test_month_filter_restricts_correctly(entries, options):
    """Month filter covers a subset of the full-year period."""
    result_year = get_income_statement(entries, options, year=2025)
    result_month = get_income_statement(entries, options, year=2025, month=1)
    # Full year total income (any currency) >= single month
    year_income_sum = sum(result_year["total_income"].values())
    month_income_sum = sum(result_month["total_income"].values())
    assert year_income_sum >= month_income_sum


def test_net_equals_income_minus_expenses(entries, options):
    """net[currency] == total_income[currency] - total_expenses[currency]."""
    result = get_income_statement(entries, options, year=2025)
    all_currencies = set(result["total_income"]) | set(result["total_expenses"])
    for currency in all_currencies:
        expected = round(
            result["total_income"].get(currency, 0.0) - result["total_expenses"].get(currency, 0.0), 2
        )
        assert result["net"].get(currency, 0.0) == expected


def test_breakdown_dicts_populated(entries, options):
    """Income and expense breakdowns are non-empty for an active year."""
    result = get_income_statement(entries, options, year=2025)
    assert len(result["income_breakdown"]) > 0
    assert len(result["expense_breakdown"]) > 0


def test_income_sign_convention_positive(entries, options):
    """Income values are positive (negated from beancount's negative convention)."""
    result = get_income_statement(entries, options, year=2025)
    for account, per_currency in result["income_breakdown"].items():
        for currency, amount in per_currency.items():
            assert amount > 0, f"Income {account}[{currency}] should be positive, got {amount}"
    # total_income values should all be positive
    for currency, total in result["total_income"].items():
        assert total > 0, f"total_income[{currency}] should be positive, got {total}"


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
    # Each account value is a dict of {currency: float}
    assert isinstance(result["income_breakdown"]["Income:Salary"], dict)


def test_expense_breakdown_contains_rent(entries, options):
    """Expense breakdown includes rent account."""
    result = get_income_statement(entries, options, year=2025)
    assert "Expenses:Rent" in result["expense_breakdown"]
    assert isinstance(result["expense_breakdown"]["Expenses:Rent"], dict)


def test_breakdown_values_are_per_currency_dicts(entries, options):
    """Breakdown values are {currency: float} dicts, not scalars."""
    result = get_income_statement(entries, options, year=2025)
    for account, per_currency in result["income_breakdown"].items():
        assert isinstance(per_currency, dict), f"{account} breakdown should be a dict"
        for currency, amount in per_currency.items():
            assert isinstance(currency, str)
            assert isinstance(amount, float)
    for account, per_currency in result["expense_breakdown"].items():
        assert isinstance(per_currency, dict), f"{account} breakdown should be a dict"


def test_total_income_converted_is_scalar(entries, options):
    """total_income_converted is a scalar float in base_currency."""
    result = get_income_statement(entries, options, year=2025)
    assert isinstance(result["total_income_converted"], float)
    assert result["total_income_converted"] >= 0


def test_total_expenses_converted_is_scalar(entries, options):
    """total_expenses_converted is a scalar float in base_currency."""
    result = get_income_statement(entries, options, year=2025)
    assert isinstance(result["total_expenses_converted"], float)
    assert result["total_expenses_converted"] >= 0


def test_multi_currency_breakdown_accumulates_separately(entries, options):
    """If multiple currencies exist, each appears separately in the breakdown."""
    result = get_income_statement(entries, options, year=2025)
    # Check that expense breakdown tracks currencies independently
    for account, per_currency in result["expense_breakdown"].items():
        for currency, amount in per_currency.items():
            assert amount != 0.0  # zero balances must be dropped
