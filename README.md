# mcp-beancount

Read-only MCP server that gives AI agents structured access to a [Beancount](https://beancount.github.io/) personal finance ledger.

---

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager

---

## Installation

```bash
uv sync
```

---

## Configuration

| Variable | Required | Default | Description |
|---|---|---|---|
| `BEANCOUNT_FILE` | ✅ | — | Absolute path to your `.beancount` ledger file |
| `ACCOUNT_ALLOWLIST` | ❌ | (none) | Comma-separated account prefix whitelist (e.g. `Assets:Bank,Expenses:`) |
| `BEANCOUNT_RELOAD` | ❌ | `false` | Reload ledger on every tool call (development mode) |

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

---

## Running

```bash
BEANCOUNT_FILE=/path/to/ledger.beancount uv run mcp-beancount
```

Or with a `.env` file (requires `dotenv` or equivalent):

```bash
export BEANCOUNT_FILE=/path/to/ledger.beancount
uv run mcp-beancount
```

---

## MCP Client Configuration

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "beancount": {
      "command": "uv",
      "args": ["run", "--project", "/path/to/mcp-beancount", "mcp-beancount"],
      "env": {
        "BEANCOUNT_FILE": "/absolute/path/to/ledger.beancount",
        "ACCOUNT_ALLOWLIST": ""
      }
    }
  }
}
```

### OpenClaw

Add to your OpenClaw MCP config:

```json
{
  "mcpServers": {
    "beancount": {
      "command": "uv",
      "args": ["run", "--project", "/path/to/mcp-beancount", "mcp-beancount"],
      "env": {
        "BEANCOUNT_FILE": "/absolute/path/to/ledger.beancount"
      }
    }
  }
}
```

---

## Tool Reference

| Tool | Signature | Description |
|---|---|---|
| `get_net_worth` | `(date?: str)` | Net worth (assets − liabilities) as of date, multi-currency with price conversion |
| `get_balances` | `(account_pattern: str)` | Non-zero balances matching account prefix/glob |
| `get_income_statement` | `(year: int, month?: int)` | Income vs expenses for a period |
| `get_transactions` | `(account?: str, since?: str, limit?: int)` | Recent transactions, filterable |
| `query` | `(bql: str)` | Raw BQL query (read-only) |

### Examples

```python
# Net worth today (multi-currency, per-currency breakdown + converted total)
get_net_worth()
# Returns:
# {
#   "as_of": "2026-03-28",
#   "base_currency": "CHF",
#   "assets": {
#     "Assets:Bank:UBS":    {"CHF": 50000.0},
#     "Assets:Broker:IBKR": {"USD": 30000.0}
#   },
#   "liabilities": {
#     "Liabilities:CreditCard": {"CHF": -2000.0}
#   },
#   "total_assets":       {"CHF": 50000.0, "USD": 30000.0},
#   "total_liabilities":  {"CHF": -2000.0},
#   "net_worth":          {"CHF": 48000.0, "USD": 30000.0},
#   "net_worth_converted": 74700.0,   # CHF 48000 + USD 30000 * 0.89
#   "skipped_positions":  []          # currencies with no price directive
# }

# Net worth as of 2025-12-31
get_net_worth(date="2025-12-31")

# All bank account balances
get_balances(account_pattern="Assets:Bank:")

# 2026 income statement
get_income_statement(year=2026)

# Q1 2026 income statement
get_income_statement(year=2026, month=1)

# Last 20 food expenses
get_transactions(account="Expenses:Food", limit=20)

# Transactions since 2026-01-01
get_transactions(since="2026-01-01")

# Raw BQL query
query("SELECT account, sum(position) WHERE account ~ 'Assets' GROUP BY account")
```

---

## Running Tests

```bash
BEANCOUNT_FILE=/path/to/any.beancount uv run pytest
```

Or using the included `sample.beancount` (tests use this automatically via fixtures):

```bash
uv run pytest
```

---

## Security

- **No writes**: the beancount library is inherently read-only
- **No shell calls**: all computation is in-process via the beancount Python API
- **Path isolation**: `BEANCOUNT_FILE` is set at startup; never exposed through tool arguments
- **Allowlist**: optional `ACCOUNT_ALLOWLIST` restricts all tools to specific account prefixes
