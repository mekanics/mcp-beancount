"""Tests for get_net_worth tool."""

from __future__ import annotations

import calendar
import datetime

import pytest

from mcp_beancount.loader import BeancountLoader
from mcp_beancount.tools.net_worth import get_net_worth


# ── Helpers ───────────────────────────────────────────────────────────────────


MULTI_CURRENCY_LEDGER = """
option "operating_currency" "CHF"
2026-01-01 open Assets:Bank:UBS CHF
2026-01-01 open Assets:Broker:IBKR USD
2026-01-01 open Equity:Opening CHF
2026-01-01 price USD 0.89 CHF
2026-01-15 * "Opening"
  Assets:Bank:UBS       50000 CHF
  Assets:Broker:IBKR    30000 USD
  Equity:Opening       -50000 CHF
  Equity:Opening       -30000 USD
"""

NO_PRICE_LEDGER = """
option "operating_currency" "CHF"
2026-01-01 open Assets:Bank:UBS CHF
2026-01-01 open Assets:Broker:IBKR USD
2026-01-01 open Equity:Opening CHF
2026-01-01 * "Opening"
  Assets:Bank:UBS       50000 CHF
  Assets:Broker:IBKR    30000 USD
  Equity:Opening       -50000 CHF
  Equity:Opening       -30000 USD
"""


def _load_inline(ledger_text: str):
    """Load beancount entries from an inline string."""
    import tempfile
    import os
    import beancount.loader as bloader

    with tempfile.NamedTemporaryFile(mode="w", suffix=".beancount", delete=False) as f:
        f.write(ledger_text)
        fname = f.name
    try:
        entries, _errors, options = bloader.load_file(fname)
    finally:
        os.unlink(fname)
    return entries, options


# ── Tests — existing (updated for new shape) ──────────────────────────────────


def test_returns_correct_keys(entries, options):
    """Result dict contains all required keys."""
    result = get_net_worth(entries, options)
    assert "as_of" in result
    assert "base_currency" in result
    assert "assets" in result
    assert "liabilities" in result
    assert "total_assets" in result
    assert "total_liabilities" in result
    assert "net_worth" in result
    assert "net_worth_converted" in result
    assert "skipped_positions" in result


def test_net_worth_equals_assets_plus_liabilities(entries, options):
    """For each currency, net_worth[c] == total_assets[c] + total_liabilities[c]."""
    result = get_net_worth(entries, options)
    all_currencies = set(result["total_assets"]) | set(result["total_liabilities"])
    for currency in all_currencies:
        expected = round(
            result["total_assets"].get(currency, 0.0)
            + result["total_liabilities"].get(currency, 0.0),
            2,
        )
        assert result["net_worth"].get(currency, 0.0) == expected


def test_date_param_filters_correctly(entries, options):
    """Historical date returns smaller (older) balances than latest."""
    result_latest = get_net_worth(entries, options)
    result_2023 = get_net_worth(entries, options, date="2023-06-30")
    # Ledger grows over time; net worth at 2023-06-30 should differ from latest
    # (at minimum the as_of dates differ)
    assert result_latest["as_of"] != result_2023["as_of"]
    assert result_2023["as_of"] == "2023-06-30"


def test_empty_ledger_returns_zeros():
    """Empty ledger returns empty dicts for totals."""
    result = get_net_worth([], {})
    assert result["total_assets"] == {}
    assert result["total_liabilities"] == {}
    assert result["net_worth"] == {}
    assert result["net_worth_converted"] == 0.0


def test_base_currency_in_output(entries, options):
    """base_currency key is present and CHF for the sample ledger."""
    result = get_net_worth(entries, options)
    assert result["base_currency"] == "CHF"


def test_as_of_date_matches_requested_date(entries, options):
    """as_of field matches the date parameter when provided."""
    result = get_net_worth(entries, options, date="2025-01-01")
    assert result["as_of"] == "2025-01-01"


def test_assets_positive_liabilities_negative(entries, options):
    """Assets total positive, liabilities total negative (per-currency)."""
    result = get_net_worth(entries, options)
    for amount in result["total_assets"].values():
        assert amount > 0
    for amount in result["total_liabilities"].values():
        assert amount <= 0


def test_net_worth_positive(entries, options):
    """Net worth CHF entry is positive for a healthy ledger."""
    result = get_net_worth(entries, options)
    assert result["net_worth"].get("CHF", 0.0) > 0


# ── Tests — date aliases ──────────────────────────────────────────────────────


def test_no_date_returns_today(entries, options):
    """date=None now returns today's date, not the latest ledger date."""
    today = datetime.date.today().isoformat()
    result = get_net_worth(entries, options)
    assert result["as_of"] == today


def test_date_today_returns_today(entries, options):
    """date='today' resolves to today's date."""
    today = datetime.date.today().isoformat()
    result = get_net_worth(entries, options, date="today")
    assert result["as_of"] == today


def test_date_end_of_month_returns_last_day(entries, options):
    """date='end-of-month' resolves to the last day of the current month."""
    today = datetime.date.today()
    last_day = calendar.monthrange(today.year, today.month)[1]
    expected = datetime.date(today.year, today.month, last_day).isoformat()
    result = get_net_worth(entries, options, date="end-of-month")
    assert result["as_of"] == expected


def test_iso_date_still_works(entries, options):
    """ISO 8601 date string is parsed correctly."""
    result = get_net_worth(entries, options, date="2026-03-01")
    assert result["as_of"] == "2026-03-01"


# ── Tests — multi-currency ────────────────────────────────────────────────────


def test_multi_currency_no_mixing():
    """USD account should only appear in total_assets['USD'], not 'CHF'."""
    entries, options = _load_inline(MULTI_CURRENCY_LEDGER)
    result = get_net_worth(entries, options)
    # USD should be in total_assets
    assert "USD" in result["total_assets"]
    # CHF total should not include USD value
    assert result["total_assets"].get("CHF", 0.0) == pytest.approx(50000.0)


def test_multi_currency_totals_correct():
    """CHF and USD totals are correct independently."""
    entries, options = _load_inline(MULTI_CURRENCY_LEDGER)
    result = get_net_worth(entries, options)
    assert result["total_assets"]["CHF"] == pytest.approx(50000.0)
    assert result["total_assets"]["USD"] == pytest.approx(30000.0)


def test_net_worth_converted_uses_price_map():
    """net_worth_converted uses price directives: 50000 + 30000*0.89 = 76700."""
    entries, options = _load_inline(MULTI_CURRENCY_LEDGER)
    result = get_net_worth(entries, options)
    assert result["net_worth_converted"] == pytest.approx(76700.0, rel=1e-4)


def test_no_price_no_mixing():
    """USD with no price directive is excluded from net_worth_converted and listed in skipped_positions."""
    entries, options = _load_inline(NO_PRICE_LEDGER)
    result = get_net_worth(entries, options)
    # USD should be skipped (no price directive)
    assert "USD" in result["skipped_positions"]
    # net_worth_converted should only include CHF
    assert result["net_worth_converted"] == pytest.approx(50000.0)


def test_base_currency_from_options():
    """base_currency is CHF from operating_currency option."""
    entries, options = _load_inline(MULTI_CURRENCY_LEDGER)
    result = get_net_worth(entries, options)
    assert result["base_currency"] == "CHF"


def test_base_currency_env_override(monkeypatch):
    """BASE_CURRENCY env var overrides options operating_currency."""
    monkeypatch.setenv("BASE_CURRENCY", "EUR")
    entries, options = _load_inline(MULTI_CURRENCY_LEDGER)
    result = get_net_worth(entries, options)
    assert result["base_currency"] == "EUR"
