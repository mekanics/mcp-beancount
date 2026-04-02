"""Tests for convert_chain in mcp_beancount.tools.utils."""

from __future__ import annotations

import os
import tempfile

import beancount.loader as bloader
import pytest
from beancount.core import prices as bc_prices
from beancount.core.amount import Amount
from beancount.core.number import Decimal

from mcp_beancount.tools.net_worth import get_net_worth
from mcp_beancount.tools.utils import convert_chain


# ── Helpers ───────────────────────────────────────────────────────────────────


def _build_price_map(ledger_text: str):
    """Load entries from inline ledger string and return its price map."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".beancount", delete=False) as f:
        f.write(ledger_text)
        fname = f.name
    try:
        entries, _errors, options = bloader.load_file(fname)
    finally:
        os.unlink(fname)
    return bc_prices.build_price_map(entries), entries, options


# ── Unit tests: convert_chain ─────────────────────────────────────────────────


def test_direct_same_currency():
    """When amt.currency == target, return immediately without price lookup."""
    _price_map, _entries, _options = _build_price_map(
        "option \"operating_currency\" \"CHF\"\n"
    )
    result = convert_chain(Amount(Decimal("100"), "CHF"), "CHF", _price_map)
    assert result is not None
    assert result.currency == "CHF"
    assert result.number == Decimal("100")


def test_two_hop_success():
    """2-hop: VT→USD at 110, USD→CHF at 0.90 → 10 VT = 990 CHF."""
    ledger = """
option "operating_currency" "CHF"
2026-01-01 price VT 110.00 USD
2026-01-01 price USD 0.90 CHF
"""
    price_map, _entries, _options = _build_price_map(ledger)
    result = convert_chain(Amount(Decimal("10"), "VT"), "CHF", price_map)
    assert result is not None
    assert result.currency == "CHF"
    assert result.number == pytest.approx(Decimal("990.00"), rel=Decimal("1e-4"))


def test_unreachable_returns_none():
    """Commodity with no price chain returns None."""
    ledger = """
option "operating_currency" "CHF"
2026-01-01 price USD 0.90 CHF
"""
    price_map, _entries, _options = _build_price_map(ledger)
    # MAGIC has no price directives — no path to CHF
    result = convert_chain(Amount(Decimal("50"), "MAGIC"), "CHF", price_map)
    assert result is None


def test_direct_hop():
    """Direct 1-hop conversion still works."""
    ledger = """
option "operating_currency" "CHF"
2026-01-01 price USD 0.90 CHF
"""
    price_map, _entries, _options = _build_price_map(ledger)
    result = convert_chain(Amount(Decimal("100"), "USD"), "CHF", price_map)
    assert result is not None
    assert result.currency == "CHF"
    assert result.number == pytest.approx(Decimal("90.00"), rel=Decimal("1e-4"))


# ── Integration test: get_net_worth with 2-hop ────────────────────────────────


VT_MULTI_HOP_LEDGER = """
option "operating_currency" "CHF"

2026-01-01 open Assets:Bank:CHF CHF
2026-01-01 open Assets:Broker:VT VT
2026-01-01 open Equity:Opening CHF

2026-01-01 price VT 110.00 USD
2026-01-01 price USD 0.90 CHF

2026-01-15 * "Opening balances"
  Assets:Bank:CHF       10000 CHF
  Assets:Broker:VT      10 VT
  Equity:Opening       -10000 CHF
  Equity:Opening       -10 VT
"""


def test_integration_vt_not_in_skipped_positions():
    """BQL convert(value()) is single-hop: VT priced in USD (not CHF directly)
    cannot be converted to CHF via BQL, so VT appears in skipped_positions.

    Note: the old convert_chain() implementation supported multi-hop (VT→USD→CHF).
    The BQL-based implementation uses beanquery's convert() which only does direct
    single-hop conversion. Positions that cannot be converted directly appear in
    skipped_positions and are excluded from net_worth_converted.
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".beancount", delete=False) as f:
        f.write(VT_MULTI_HOP_LEDGER)
        fname = f.name
    try:
        entries, _errors, options = bloader.load_file(fname)
    finally:
        os.unlink(fname)

    result = get_net_worth(entries, options, date="2026-12-31")
    # BQL convert(value()) is single-hop: VT→USD→CHF chain is not supported
    assert "VT" in result["skipped_positions"], (
        f"Expected VT in skipped_positions (BQL is single-hop), got: {result['skipped_positions']}"
    )
    # net_worth_converted only includes the CHF portion (10000 CHF)
    assert result["net_worth_converted"] == pytest.approx(10000.0, rel=1e-4)
