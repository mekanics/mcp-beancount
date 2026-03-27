"""Tests for AllowList."""

from __future__ import annotations

import pytest

from mcp_beancount.allowlist import AllowList
from mcp_beancount.tools.balances import get_balances


def test_empty_allowlist_no_filtering():
    """Empty allowlist allows all accounts."""
    al = AllowList([])
    assert al.allows("Assets:Bank:Checking")
    assert al.allows("Expenses:Food")
    assert al.is_empty()


def test_single_prefix_filters_correctly():
    """Single prefix allows only matching accounts."""
    al = AllowList(["Assets:"])
    assert al.allows("Assets:Bank:Checking")
    assert al.allows("Assets:Savings")
    assert not al.allows("Expenses:Food")
    assert not al.allows("Liabilities:CreditCard")


def test_multiple_prefixes_or_logic():
    """Multiple prefixes use OR logic."""
    al = AllowList(["Assets:Bank", "Expenses:Food"])
    assert al.allows("Assets:Bank:Checking")
    assert al.allows("Expenses:Food")
    assert not al.allows("Expenses:Rent")
    assert not al.allows("Liabilities:CreditCard")


def test_nonmatching_account_filtered_out():
    """Account not matching any prefix is excluded."""
    al = AllowList(["Income:"])
    accounts = ["Assets:Bank", "Income:Salary", "Expenses:Food"]
    filtered = al.filter(accounts)
    assert filtered == ["Income:Salary"]


def test_from_env_parses_comma_separated():
    """from_env parses comma-separated string correctly."""
    al = AllowList.from_env("Assets:Bank,Expenses:")
    assert al.allows("Assets:Bank:Checking")
    assert al.allows("Expenses:Food")
    assert not al.allows("Liabilities:CreditCard")


def test_from_env_none_returns_empty():
    """from_env with None returns empty allowlist."""
    al = AllowList.from_env(None)
    assert al.is_empty()
    assert al.allows("Anything:Goes")


def test_from_env_empty_string_returns_empty():
    """from_env with empty string returns empty allowlist."""
    al = AllowList.from_env("")
    assert al.is_empty()


def test_allowlist_applied_in_get_balances(entries, options):
    """AllowList restricts get_balances results to allowed prefix only."""
    allowlist = AllowList(["Assets:"])
    result = get_balances(entries, options, "Assets:", allowlist=allowlist)
    # All returned accounts should start with Assets:
    for item in result:
        assert item["account"].startswith("Assets:")
    # Now verify that without allowlist, we still only see Assets: (pattern match)
    # But with a restrictive allowlist, non-Assets should be excluded
    strict_allowlist = AllowList(["Assets:Bank:Savings"])
    result_strict = get_balances(entries, options, "Assets:", allowlist=strict_allowlist)
    for item in result_strict:
        assert item["account"].startswith("Assets:Bank:Savings")
