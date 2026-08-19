"""Package-level smoke tests."""

from __future__ import annotations

import importlib.metadata

import osf
import osf.cli as cli


def test_package_has_version() -> None:
    """The package exposes a __version__ string."""
    assert hasattr(osf, "__version__")
    assert isinstance(osf.__version__, str)
    assert osf.__version__  # non-empty


def test_version_matches_pyproject() -> None:
    """osf.__version__ matches the version declared in pyproject.toml."""
    metadata_version = importlib.metadata.version("openstockfeed")
    assert metadata_version == osf.__version__


def test_cli_module_exposes_main() -> None:
    """The CLI module exposes a callable main() entry point."""
    assert callable(cli.main)


def test_default_ticker_is_aapl() -> None:
    """The CLI's argparse default for --ticker is AAPL."""
    import inspect
    import re

    import osf.cli as cli_module

    source = inspect.getsource(cli_module)
    # argparse default for --ticker is "AAPL" — search the source for the
    # add_argument call so any accidental change to the default is caught.
    match = re.search(
        r'add_argument\([^)]*"--ticker"[^\)]*default="(?P<default>[A-Z]+)"',
        source,
        re.DOTALL,
    )
    assert match is not None, "could not find --ticker default in cli.py"
    assert match.group("default") == "AAPL"