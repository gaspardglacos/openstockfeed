# OpenStockFeed

OpenStockFeed is a lightweight command-line tool that watches live stock prices from a browser-rendered market page and outputs a new value only when the price changes.

It uses Selenium to keep a headless Chrome session open, reads the live page DOM at a lightning fast interval, and can optionally send price-change events to a webhook or save them to a JSONL file.

## Installation

```bash
pip install openstockfeed

## Quick Start

After installing OpenStockFeed, run:

```bash
osf --help

## Features

- Live stock price watching from Trading Economics pages
- Installable from PyPI as `openstockfeed`
- CLI command: `osf`
- Headless Chrome by default
- Ticker selection with `-t` / `--ticker`
- Prints only when the price changes
- Optional webhook support
- Optional JSONL output
- Automatic Chrome and ChromeDriver cleanup on exit
- Configurable polling interval

## Requirements

- Python 3.10+
- Microsoft Edge installed (any recent version)
- Windows, macOS, or Linux

Playwright reuses your installed Edge; no `playwright install` is required.

## Examples

# Watch the default ticker, AAPL
osf

# Watch a specific ticker
osf -t MSFT

# Equivalent long form
osf --ticker MSFT

# Run with a visible Chrome window
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
