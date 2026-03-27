"""AllowList — account prefix filtering for mcp-beancount."""

from __future__ import annotations


class AllowList:
    """Filter accounts by a list of allowed prefixes.

    Args:
        prefixes: List of account name prefixes (e.g. ["Assets:Bank", "Expenses:"]).
                  If empty, no filtering is applied (all accounts pass).
    """

    def __init__(self, prefixes: list[str]) -> None:
        # Strip whitespace from each prefix
        self._prefixes = [p.strip() for p in prefixes if p.strip()]

    @classmethod
    def from_env(cls, value: str | None) -> "AllowList":
        """Parse a comma-separated prefix string from an env var value.

        Args:
            value: Comma-separated string like "Assets:Bank,Expenses:" or None.

        Returns:
            AllowList instance (empty = no filtering).
        """
        if not value:
            return cls([])
        prefixes = [p.strip() for p in value.split(",") if p.strip()]
        return cls(prefixes)

    def is_empty(self) -> bool:
        """Return True if no prefixes are configured (no filtering)."""
        return len(self._prefixes) == 0

    def allows(self, account: str) -> bool:
        """Return True if the account matches any configured prefix.

        If the allowlist is empty, all accounts are allowed.

        Args:
            account: Full account name (e.g. "Assets:Bank:Checking").
        """
        if self.is_empty():
            return True
        return any(account.startswith(prefix) for prefix in self._prefixes)

    def filter(self, accounts: list[str]) -> list[str]:
        """Return only accounts that pass the allowlist filter.

        Args:
            accounts: List of account name strings.

        Returns:
            Filtered list.
        """
        if self.is_empty():
            return accounts
        return [a for a in accounts if self.allows(a)]
