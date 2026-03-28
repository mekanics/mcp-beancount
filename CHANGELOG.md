# Changelog

All notable changes to mcp-beancount are documented here.

## [Unreleased]

### Breaking Changes

- **`get_net_worth` return shape changed** — The tool now returns per-currency dicts
  instead of scalar floats. Callers must update to the new shape.

  **Before:**
  ```json
  {
    "as_of": "2026-03-28",
    "assets": {"Assets:Bank:UBS": 50000.0, "Assets:Broker:IBKR": 30000.0},
    "liabilities": {"Liabilities:CreditCard": -2000.0},
    "total_assets": 80000.0,
    "total_liabilities": -2000.0,
    "net_worth": 78000.0,
    "currency": "CHF"
  }
  ```

  **After:**
  ```json
  {
    "as_of": "2026-03-28",
    "base_currency": "CHF",
    "assets": {
      "Assets:Bank:UBS":    {"CHF": 50000.0},
      "Assets:Broker:IBKR": {"USD": 30000.0}
    },
    "liabilities": {
      "Liabilities:CreditCard": {"CHF": -2000.0}
    },
    "total_assets":       {"CHF": 50000.0, "USD": 30000.0},
    "total_liabilities":  {"CHF": -2000.0},
    "net_worth":          {"CHF": 48000.0, "USD": 30000.0},
    "net_worth_converted": 74700.0,
    "skipped_positions":  []
  }
  ```

### Added

- **Multi-currency net worth** — assets and liabilities are now tracked per currency
  without silent mixing. Each account entry is `{currency: amount}`.
- **`net_worth_converted`** — scalar total in `base_currency`, computed via beancount's
  `price` directives and `price_map`. Always present.
- **`skipped_positions`** — list of currencies/commodities that had no price directive
  as of the cutoff date and were therefore excluded from `net_worth_converted`.
- **`base_currency` field** — resolved from `operating_currency[0]` in the ledger options,
  or overridden via `BASE_CURRENCY` environment variable.
- **`BASE_CURRENCY` env var** — allows overriding the base currency without changing the
  ledger file.

### Fixed

- **Silent currency mixing** — previously, USD nominal values were silently added to CHF
  totals when an account had no CHF balance. This is now fixed: each currency stays in
  its own bucket.
