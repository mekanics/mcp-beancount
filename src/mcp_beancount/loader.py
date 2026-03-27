"""BeancountLoader — wraps beancount.loader.load_file with optional caching."""

from __future__ import annotations

import threading
from typing import Any

from beancount import loader as beancount_loader


class BeancountLoader:
    """Load and optionally cache a Beancount ledger file.

    Args:
        path: Absolute path to the .beancount file.
        reload_on_call: If True, reload the file on every call to get().
    """

    def __init__(self, path: str, reload_on_call: bool = False) -> None:
        self._path = path
        self._reload_on_call = reload_on_call
        self._lock = threading.Lock()
        self._cache: tuple[Any, Any, Any] | None = None

    def load(self) -> tuple[Any, Any, Any]:
        """Load (or reload) the ledger file and update the cache.

        Returns:
            (entries, errors, options) tuple from beancount.loader.load_file.
        """
        entries, errors, options = beancount_loader.load_file(self._path)
        with self._lock:
            self._cache = (entries, errors, options)
        return entries, errors, options

    def get(self) -> tuple[Any, Any, Any]:
        """Return cached or freshly loaded (entries, errors, options).

        If reload_on_call is True, always reloads. Otherwise, loads once
        and returns the cached result on subsequent calls.
        """
        if self._reload_on_call:
            return self.load()

        with self._lock:
            if self._cache is not None:
                return self._cache

        return self.load()
