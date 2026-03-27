"""Test fixtures for mcp-beancount tests."""

from __future__ import annotations

import os
import pathlib

import pytest

from mcp_beancount.loader import BeancountLoader


# Path to the sample ledger in the project root
SAMPLE_BEANCOUNT = pathlib.Path(__file__).parent.parent / "sample.beancount"


@pytest.fixture(scope="session")
def loader() -> BeancountLoader:
    """BeancountLoader loaded from sample.beancount."""
    return BeancountLoader(str(SAMPLE_BEANCOUNT), reload_on_call=False)


@pytest.fixture(scope="session")
def entries(loader: BeancountLoader):
    """Beancount entries from sample.beancount."""
    e, _err, _opts = loader.get()
    return e


@pytest.fixture(scope="session")
def options(loader: BeancountLoader):
    """Beancount options dict from sample.beancount."""
    _e, _err, opts = loader.get()
    return opts
