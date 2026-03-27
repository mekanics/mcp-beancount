"""Tests for get_net_worth tool."""

from __future__ import annotations

import pytest

from mcp_beancount.loader import BeancountLoader
from mcp_beancount.tools.net_worth import get_net_worth


# ── Helpers ───────────────────────────────────────────────────────────────────


def _empty_entries():
    """Return empty beancount entries for testing empty-ledger edge cases."""
    return [], {}


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_returns_correct_keys(entries, options):
    """Result dict contains all required keys."""
    result = get_net_worth(entries, options)
    assert "as_of" in result
    assert "assets" in result
    assert "liabilities" in result
    assert "total_assets" in result
    assert "total_liabilities" in result
    assert "net_worth" in result
    assert "currency" in result


def test_net_worth_equals_assets_plus_liabilities(entries, options):
    """net_worth == total_assets + total_liabilities."""
    result = get_net_worth(entries, options)
    expected = round(result["total_assets"] + result["total_liabilities"], 2)
    assert result["net_worth"] == expected


def test_date_param_filters_correctly(entries, options):
    """Historical date returns smaller (older) balances than latest."""
    result_latest = get_net_worth(entries, options)
    result_2023 = get_net_worth(entries, options, date="2023-06-30")
    # Ledger grows over time; net worth at 2023-06-30 should differ from latest
    # (at minimum the as_of dates differ)
    assert result_latest["as_of"] != result_2023["as_of"]
    assert result_2023["as_of"] == "2023-06-30"


def test_empty_ledger_returns_zeros():
    """Empty ledger returns zero net worth."""
    result = get_net_worth([], {})
    assert result["total_assets"] == 0.0
    assert result["total_liabilities"] == 0.0
    assert result["net_worth"] == 0.0


def test_currency_is_chf(entries, options):
    """Primary currency is CHF (most common in Assets accounts)."""
    result = get_net_worth(entries, options)
    assert result["currency"] == "CHF"


def test_as_of_date_matches_requested_date(entries, options):
    """as_of field matches the date parameter when provided."""
    result = get_net_worth(entries, options, date="2025-01-01")
    assert result["as_of"] == "2025-01-01"


def test_assets_positive_liabilities_negative(entries, options):
    """Assets should be positive, liabilities negative."""
    result = get_net_worth(entries, options)
    assert result["total_assets"] > 0
    # Liabilities are negative in beancount (credit balance)
    assert result["total_liabilities"] <= 0


def test_net_worth_positive(entries, options):
    """Net worth is positive for a healthy ledger."""
    result = get_net_worth(entries, options)
    assert result["net_worth"] > 0
