# Playwright Migration Design

**Date:** 2026-08-02
**Status:** Draft — pending user review
**Scope:** Replace Selenium with Playwright in `osf/cli.py` while preserving the existing CLI surface, behavior, and process-cleanup guarantees.

## Background and motivation

`osf/cli.py` currently drives a headless Chrome session through Selenium 4. Selenium works, but each DOM poll re-enters the WebDriver command protocol, which is the bottleneck the user is trying to remove. Playwright reuses a persistent CDP session and is materially faster on tight poll loops.

The repository is **not** a git repository (no `.git/` directory), so this design cannot be "committed" in the normal sense; the spec is written to disk for review and the implementation will edit files in place.

## Goals

- Switch the scraping engine from Selenium to Playwright **sync** API.
- Reuse the Microsoft Edge that is already installed at `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe` via Playwright's `channel="msedge"`. **No Chromium download**; no `playwright install` step.
- Preserve every CLI flag and behavior: `-t/--ticker`, `-i/--interval`, `--output`, `--webhook-url`, `--webhook-timeout`, `--visible`, `--no-print-first`.
- Preserve the no-orphan-processes guarantee from the current Selenium code by keeping the `psutil` process-tree walk.
- Fail with an actionable error message when Edge is missing or incompatible.

## Non-goals

- Adding a test suite (none exists today; out of scope for this migration).
- Async / `asyncio` rewrite of `main()`.
- A `--engine` flag to keep Selenium available.
- Switching the WebDriver target away from Trading Economics.
- Changing the price-change detection or webhook payload schema.

## Current environment (verified 2026-08-02)

- Python 3.14.6 on Windows 11 (arm64).
- `playwright` is **not** installed (`pip show playwright` → "not found"; `import playwright` → `ModuleNotFoundError`).
- No Playwright browser cache at `~/.cache/ms-playwright` or `%LOCALAPPDATA%\ms-playwright`.
- Google Chrome is **not** installed at the standard `C:\Program Files\Google\Chrome\Application\chrome.exe` paths.
- Microsoft Edge is installed at `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`.

## Architecture

### New module shape

`osf/cli.py` keeps the same public surface (`main()`) and the same helpers for URL building, text normalization, and price extraction. Two functions are renamed/replaced:

- `build_driver(headless: bool)` → `build_browser(headless: bool)` returning a tuple:
  `(playwright, browser, page, msedge_pid, tracked_pids, user_data_dir)`. (`page` is the active page; `msedge_pid` is the first PID discovered after launch; `tracked_pids` is the full set, including the Edge process tree, used for cleanup.)
- `close_driver(...)` → `close_browser(playwright, browser, msedge_pid, tracked_pids, user_data_dir)` with the same PID-tracking and tempdir cleanup logic.

### Lifecycle

1. `sync_playwright()` is entered as a context manager so the driver process is reaped on any exit path, including exceptions during launch.
2. `chromium.launch(channel="msedge", headless=headless, args=[...])` is called with the same Chrome-style flags the current Selenium code uses. The args translate cleanly to Edge:
   - `--disable-blink-features=AutomationControlled`
   - `--no-sandbox`
   - `--disable-dev-shm-usage`
   - `--disable-gpu`
   - `--window-size=1400,1000`
   - Custom `--user-agent=...` string.
3. The browser is wrapped in a `new_context()` so the user-data-dir is scoped to a `tempfile.mkdtemp(prefix="osf_edge_profile_")` directory, mirroring the current Selenium tempdir.
4. `browser.process.pid` is recorded as the seed PID; `get_process_tree_pids` (unchanged) collects children via `psutil`.
5. After `page.goto(url)`, the loop waits 5 seconds for the Trading Economics DOM to stabilize, then enters the existing poll loop.
6. Each iteration calls `page.locator("body").inner_text(timeout=0)` (timeout 0 = no implicit wait, to keep the existing sub-millisecond poll cadence).
7. The price-change detection, JSONL write, and webhook POST logic are unchanged.
8. On `KeyboardInterrupt` or normal exit, `close_browser` runs:
   - Update `tracked_pids` from the current `browser.process.pid`.
   - `browser.close()` then `playwright.stop()` via the context manager.
   - Sleep 1s, find any surviving `msedge.exe` / `msedgewebview2.exe` processes (Playwright does not always start a separate `chromedriver`; the equivalent is the browser process itself), and `kill_pids` them with the existing 3s grace period.
   - Remove the tempdir.

### Why `sync_playwright` and not async

The existing `main()` is a single-threaded blocking loop driven by `time.perf_counter()`. The async API would require restructuring the whole function, adding no real benefit for a single-page polling CLI. `sync_playwright` is the lowest-diff path.

## Dependencies and packaging

### `requirements.txt`

Add `playwright`. Remove `selenium`. Keep `psutil` and `requests`.

```text
certifi
requests
pandas
yfinance
matplotlib
psutil
playwright
```

### `pyproject.toml`

Replace `selenium` with `playwright` in `project.dependencies`. Leave `requires-python = ">=3.10"`.

### `openstockfeed.egg-info/requires.txt`

Regenerate by running `pip install -e .` after the source change. Not edited by hand.

### `README.md`

- Replace "Google Chrome installed" with "Microsoft Edge installed (any recent version)".
- Remove the "Selenium 4 usually manages ChromeDriver automatically" line; Playwright bundles its own driver.
- Add a one-line note: "Playwright reuses your installed Edge; no `playwright install` is required."

## Error handling

| Condition | Behavior |
| --- | --- |
| `chromium.launch` raises `playwright.sync_api.Error` (Edge missing, version too old, sandbox failure) | Catch, print `Error: Microsoft Edge is required. Install from https://www.microsoft.com/edge and try again.`, exit 1. |
| `page.locator("body").inner_text(timeout=0)` raises | Swallowed by the existing `except Exception: pass` so transient DOM hiccups don't kill the watcher. |
| `Ctrl+C` during launch | `finally` in `build_browser` removes the user-data-dir; `playwright.stop()` is called by the `sync_playwright` context manager. |
| `Ctrl+C` during polling | Existing `KeyboardInterrupt` handler runs `close_browser`. |
| Webhook request fails | Same `except Exception: pass` as today; price is still printed. |

## Verification

No automated tests. The migration is verified by four manual smoke tests, all runnable from the project root after `pip install -r requirements.txt`:

1. **Smoke A — help:** `osf --help` prints the same argparse output as before (no Selenium error).
2. **Smoke B — headless run:** `osf -t AAPL --no-print-first --interval 0.5` for ~15s. Expect: one line printed, then clean exit. After exit, `tasklist | findstr msedge` returns no rows.
3. **Smoke C — JSONL output:** `osf -t TSLA --interval 0.5 --output tsla.jsonl --no-print-first`. Inspect `tsla.jsonl` for valid JSONL lines matching the existing schema.
4. **Smoke D — visible mode:** `osf -t NVDA --visible --no-print-first` opens a real Edge window. `Ctrl+C` closes both the window and the process tree.

All four must pass before the migration is declared complete. Any regression versus the Selenium baseline (extra processes, different output, different CLI surface) is a blocker.

## Migration steps

1. Edit `osf/cli.py` per the architecture section. Keep all helper functions except the two driver-related ones.
2. Update `pyproject.toml` and `requirements.txt`.
3. Update `README.md` to reflect the Edge requirement and drop the ChromeDriver note.
4. Run `pip install -e .` to regenerate `openstockfeed.egg-info/requires.txt`.
5. Run Smoke A–D and report results.
6. If a smoke step fails, halt and surface the failure; do not declare success on partial verification.

## Risks and mitigations

- **Risk:** Playwright's bundled driver may not support the exact Edge version installed. **Mitigation:** Playwright's `channel="msedge"` is maintained against current stable Edge; if launch fails, the actionable error message tells the user what to do.
- **Risk:** The Trading Economics DOM may differ from what Selenium rendered, breaking `extract_from_texts`. **Mitigation:** `inner_text()` returns the rendered visible text in the same way Selenium's `.text` did, so the extractor should be unchanged. If a regression is found, the extractor is the first place to inspect.
- **Risk:** `psutil` cleanup misses a child process and Edge is left running. **Mitigation:** the existing 3-second grace + force-kill pattern stays; we add `msedgewebview2.exe` to the name match list (Edge on Windows uses this helper process).
