# OpenStockFeed

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/gbeharel/openstockfeed/actions/workflows/ci.yml/badge.svg)](https://github.com/gbeharel/openstockfeed/actions/workflows/ci.yml)

OpenStockFeed is a lightweight command-line tool that watches live stock prices from a browser-rendered market page and outputs a new value only when the price changes.

It uses **Playwright** (via the Microsoft Edge channel) to keep a headless browser session open, polls the live page DOM at a configurable interval, and can optionally send price-change events to a webhook or save them to a JSONL file.

## Why

Most free price APIs have rate limits, CORS restrictions, or require API keys. Many data sources render prices client-side, which is inconvenient for headless servers. OpenStockFeed takes the pragmatic route: drive a real headless Edge, scrape the DOM, emit only on change.

## Installation

```bash
pip install openstockfeed
```

## Quick Start

```bash
osf --help
```

## Features

- Live stock price watching from Trading Economics pages
- Installable from PyPI as `openstockfeed`
- CLI command: `osf` (and `python -m osf`)
- Headless Edge by default
- Ticker selection with `-t` / `--ticker`
- Prints only when the price changes
- Optional webhook support
- Optional JSONL output
- Automatic Edge and EdgeDriver cleanup on exit
- Configurable polling interval
- Cross-platform: Windows, macOS, Linux

## Requirements

- Python 3.10+
- Microsoft Edge installed (any recent version)

Playwright reuses your installed Edge via `channel="msedge"`, so no separate `playwright install` download is required.

## Examples

```bash
# Watch the default ticker, AAPL
osf

# Watch a specific ticker
osf -t MSFT

# Equivalent long form
osf --ticker MSFT

# Run with a visible Edge window
osf -t AAPL --visible

# Use a slower polling interval
osf -t AAPL --interval 0.05

# Use a faster polling interval
osf -t AAPL --interval 0.001

# Save price changes to a JSONL file
osf -t TSLA --output tsla_changes.jsonl

# Send price changes to a webhook
osf -t NVDA --webhook-url https://your-webhook-url.com

# Set a custom webhook timeout
osf -t NVDA --webhook-url https://your-webhook-url.com --webhook-timeout 5

# Do not print the first detected price
osf -t AAPL --no-print-first

# Combine multiple options
osf -t MSFT --interval 0.005 --output msft_changes.jsonl

# Run visibly while debugging
osf -t TSLA --visible --interval 0.01

# Display help
osf --help
```

## Development

```bash
git clone https://github.com/gbeharel/openstockfeed.git
cd openstockfeed
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
pip install -e .
pytest
```

## Project layout

```
openstockfeed/
├── osf/                 # Python package
│   ├── __init__.py
│   └── cli.py           # CLI entry point (`osf` and `python -m osf`)
├── tests/               # Pytest suite
├── .github/workflows/   # CI
├── pyproject.toml       # Build metadata
├── requirements.txt     # Runtime dependencies
└── requirements-dev.txt # Test/lint dependencies
```

## License

MIT — see [LICENSE](LICENSE).

## Contributing

Issues and pull requests welcome. Please run `pytest` before submitting.