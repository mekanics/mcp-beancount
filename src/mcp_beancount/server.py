"""mcp-beancount server — FastMCP entry point."""

from __future__ import annotations

import os

from fastmcp import FastMCP

from mcp_beancount.allowlist import AllowList
from mcp_beancount.loader import BeancountLoader
from mcp_beancount.tools.balances import get_balances as _get_balances
from mcp_beancount.tools.income_statement import get_income_statement as _get_income_statement
from mcp_beancount.tools.net_worth import get_net_worth as _get_net_worth
from mcp_beancount.tools.query import run_bql_query
from mcp_beancount.tools.transactions import get_transactions as _get_transactions

# ── Configuration ─────────────────────────────────────────────────────────────

_beancount_file = os.environ.get("BEANCOUNT_FILE", "")
if not _beancount_file:
    raise ValueError(
        "BEANCOUNT_FILE environment variable is not set. "
        "Set it to the absolute path of your Beancount ledger file, e.g.:\n"
        "  export BEANCOUNT_FILE=/home/alex/finances/ledger.beancount"
    )

_reload_on_call = os.environ.get("BEANCOUNT_RELOAD", "false").lower() in ("true", "1", "yes")
_allowlist_raw = os.environ.get("ACCOUNT_ALLOWLIST", "")

loader = BeancountLoader(path=_beancount_file, reload_on_call=_reload_on_call)
allowlist = AllowList.from_env(_allowlist_raw)

# ── FastMCP app ────────────────────────────────────────────────────────────────

mcp = FastMCP("mcp-beancount")


# ── Tool definitions ──────────────────────────────────────────────────────────


@mcp.tool()
def get_net_worth(date: str | None = None) -> dict:
    """Get net worth (assets minus liabilities) as of a given date.

    Args:
        date: ISO 8601 date string (e.g. "2026-01-01"). If omitted, uses the
              latest transaction date in the ledger.

    Returns:
        dict with keys:
          - as_of: ISO date string
          - base_currency: str (from operating_currency or BASE_CURRENCY env)
          - assets: {account: {currency: float}}
          - liabilities: {account: {currency: float}}
          - total_assets: {currency: float}
          - total_liabilities: {currency: float}
          - net_worth: {currency: float}  (per-currency, no conversion)
          - net_worth_converted: float  (scalar in base_currency, via price directives)
          - skipped_positions: [currency]  (currencies with no price directive)
    """
    entries, _errors, options = loader.get()
    return _get_net_worth(entries, options, date=date)


@mcp.tool()
def get_balances(account_pattern: str) -> list[dict]:
    """Get non-zero account balances matching a pattern.

    Args:
        account_pattern: Account prefix or glob pattern (e.g. "Assets:",
                         "Assets:Bank:*", "Expenses:Food").

    Returns:
        List of dicts: [{"account": str, "balance": float, "currency": str}]
    """
    entries, _errors, options = loader.get()
    return _get_balances(entries, options, account_pattern, allowlist=allowlist)


@mcp.tool()
def get_income_statement(year: int, month: int | None = None) -> dict:
    """Get income and expense summary for a year or year+month period.

    Args:
        year: 4-digit year (e.g. 2026).
        month: Optional month 1-12. If omitted, covers the full year.

    Returns:
        dict with period, total_income, total_expenses, net,
        income_breakdown, expense_breakdown.
    """
    entries, _errors, options = loader.get()
    return _get_income_statement(entries, options, year=year, month=month)


@mcp.tool()
def get_transactions(
    account: str | None = None,
    since: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """Get recent transactions, optionally filtered.

    Args:
        account: Account name prefix filter (e.g. "Expenses:Food"). Optional.
        since: ISO 8601 date string; only return transactions on/after this
               date. Optional.
        limit: Max number of transactions to return (capped at 200). Default 50.

    Returns:
        List of transaction dicts sorted by date descending (most recent first).
    """
    entries, _errors, options = loader.get()
    return _get_transactions(entries, options, account=account, since=since, limit=limit)


@mcp.tool()
def query(bql: str) -> dict:
    """Execute a BQL (Beancount Query Language) query.

    Args:
        bql: BQL query string (e.g. "SELECT account, sum(position) WHERE
             account ~ 'Assets' GROUP BY account").

    Returns:
        dict with "columns" (list of column names) and "rows" (list of dicts).
        On error: {"error": "...", "rows": []}.
    """
    entries, _errors, options = loader.get()
    return run_bql_query(entries, options, bql, allowlist=allowlist)


# ── Entry point ────────────────────────────────────────────────────────────────


def main() -> None:
    """Run the MCP server.

    Transport, host, and port are configured via FastMCP native env vars
    (read automatically by FastMCP 3.x via pydantic-settings):
      FASTMCP_TRANSPORT  (default: streamable-http)
      FASTMCP_HOST       (default: 0.0.0.0)
      FASTMCP_PORT       (default: 8000)
    """
    mcp.run()


if __name__ == "__main__":
    main()
