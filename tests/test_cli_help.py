"""CLI smoke tests that don't require a browser.

These tests verify the CLI is wired up correctly (argparse, ``--help``,
``python -m osf``) without launching Playwright or Microsoft Edge.
"""

from __future__ import annotations

import subprocess
import sys

import pytest


HELP_MARKERS = [
    "--ticker",
    "--interval",
    "--output",
    "--webhook-url",
    "--visible",
]


@pytest.mark.parametrize("flag", ["--help", "-h"])
def test_help_flag_exits_zero(flag: str) -> None:
    """``osf --help`` and ``osf -h`` exit with status 0."""
    result = subprocess.run(
        [sys.executable, "-m", "osf", flag],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, (
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_help_lists_all_documented_options() -> None:
    """``osf --help`` lists every option mentioned in the README."""
    result = subprocess.run(
        [sys.executable, "-m", "osf", "--help"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0
    help_text = result.stdout
    for marker in HELP_MARKERS:
        assert marker in help_text, f"missing option {marker!r} in --help output"


def test_python_dash_m_osf_is_callable() -> None:
    """``python -m osf`` is a valid entry point (no ImportError)."""
    # We expect --help to succeed; if -m wiring is broken, Python prints
    # "No module named osf" to stderr and exits non-zero.
    result = subprocess.run(
        [sys.executable, "-m", "osf", "--help"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert "No module named" not in result.stderr