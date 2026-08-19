#!/usr/bin/env python3

import argparse
import json
import re
import shutil
import tempfile
import time
from datetime import datetime

import psutil
import requests
from playwright.sync_api import sync_playwright
from playwright.sync_api import Error as PlaywrightError


def _register_signal_handlers(cleanup: callable) -> None:
    import signal
    try:
        signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt))
    except (ValueError, AttributeError, OSError):
        pass
    if hasattr(signal, "SIGBREAK"):
        try:
            signal.signal(signal.SIGBREAK, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt))
        except (ValueError, AttributeError, OSError):
            pass


def build_url(ticker: str) -> str:
    return f"https://tradingeconomics.com/{ticker.lower()}:us"


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def is_number(value: str) -> bool:
    value = clean_text(value)
    return bool(re.fullmatch(r"-?\d+(?:,\d{3})*(?:\.\d+)?", value))


def normalize_price(value: str, max_chars: int = 7) -> str | None:
    value = clean_text(value).replace(",", "")

    match = re.search(r"\d+(?:\.\d+)?", value)
    if not match:
        return None

    return match.group(0)[:max_chars]


def extract_from_texts(texts: list[str], symbol: str) -> dict:
    raw_price = None
    daily_change = None
    percent_change = None
    monthly = None
    yearly = None
    forecast = None

    for index, text in enumerate(texts):
        if text == "Stock Price":
            for next_text in texts[index + 1:index + 8]:
                if is_number(next_text):
                    raw_price = next_text
                    break

        if text == "Daily Change":
            found = []

            for next_text in texts[index + 1:index + 8]:
                if is_number(next_text) or "%" in next_text:
                    found.append(next_text)

            if len(found) >= 1:
                daily_change = found[0]
            if len(found) >= 2:
                percent_change = found[1]

        if text == "Monthly":
            for next_text in texts[index + 1:index + 5]:
                if "%" in next_text:
                    monthly = next_text
                    break

        if text == "Yearly":
            for next_text in texts[index + 1:index + 5]:
                if "%" in next_text:
                    yearly = next_text
                    break

        if "Forecast" in text:
            for next_text in texts[index + 1:index + 8]:
                if is_number(next_text):
                    forecast = next_text
                    break

    if raw_price is None:
        return {
            "symbol": symbol,
            "price": None,
            "error": "Stock Price not found",
            "text_preview": texts[:80],
        }

    return {
        "symbol": symbol,
        "price": normalize_price(raw_price),
        "raw_price": raw_price,
        "daily_change": daily_change,
        "percent_change": percent_change,
        "monthly": monthly,
        "yearly": yearly,
        "forecast": forecast,
    }


def extract_with_playwright_visible_text(page, symbol: str) -> dict:
    body_text = page.locator("body").inner_text(timeout=0)

    texts = body_text.splitlines()
    texts = [clean_text(text) for text in texts if clean_text(text)]

    return extract_from_texts(texts, symbol)


def print_price_change(data: dict, previous_price: str | None) -> None:
    print(data.get("price"), flush=True)


def send_webhook(webhook_url: str, payload: dict, timeout: float) -> None:
    try:
        response = requests.post(
            webhook_url,
            json=payload,
            timeout=timeout,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "stock-live-webhook/1.0",
            },
        )
        response.raise_for_status()
    except Exception:
        pass


def get_process_tree_pids(root_pid: int) -> set[int]:
    pids = set()

    try:
        root = psutil.Process(root_pid)
        pids.add(root.pid)

        for child in root.children(recursive=True):
            pids.add(child.pid)

    except psutil.Error:
        pass

    return pids


def kill_pids(pids: set[int]) -> None:
    processes = []

    for pid in pids:
        try:
            processes.append(psutil.Process(pid))
        except psutil.Error:
            pass

    for process in processes:
        try:
            process.terminate()
        except psutil.Error:
            pass

    _, alive = psutil.wait_procs(processes, timeout=3)

    for process in alive:
        try:
            process.kill()
        except psutil.Error:
            pass


def _is_edge_process_name(name: str | None) -> bool:
    lowered = (name or "").lower()
    return "msedge" in lowered or "msedgewebview2" in lowered


def discover_edge_pids(timeout: float = 5.0) -> set[int]:
    pre_snapshot: set[int] = set()

    try:
        for proc in psutil.process_iter(["name"]):
            try:
                if _is_edge_process_name(proc.info["name"]):
                    pre_snapshot.add(proc.pid)
            except (psutil.Error, OSError):
                pass
    except psutil.Error:
        pass

    deadline = time.monotonic() + max(0.0, timeout)
    discovered: set[int] = set()

    while time.monotonic() < deadline:
        try:
            for proc in psutil.process_iter(["name"]):
                try:
                    if proc.pid in pre_snapshot:
                        continue
                    if _is_edge_process_name(proc.info["name"]):
                        discovered.add(proc.pid)
                except (psutil.Error, OSError):
                    pass
        except psutil.Error:
            pass

        if discovered:
            break

        time.sleep(0.05)

    expanded: set[int] = set()

    for pid in discovered:
        expanded.update(get_process_tree_pids(pid))

    return expanded


def build_browser(headless: bool):
    user_data_dir = tempfile.mkdtemp(prefix="osf_edge_profile_")
    user_agent = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0 Safari/537.36"
    )
    launch_args = [
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--window-size=1400,1000",
    ]

    playwright = sync_playwright().start()
    msedge_pid = None
    tracked_pids = set()
    browser = None

    try:
        browser = playwright.chromium.launch(
            channel="msedge",
            headless=headless,
            args=launch_args,
        )
        context = browser.new_context(user_agent=user_agent)
        page = context.new_page()

        try:
            tracked_pids = discover_edge_pids(timeout=5.0)
            if tracked_pids:
                msedge_pid = next(iter(tracked_pids))
        except Exception:
            pass

    except PlaywrightError as exc:
        try:
            shutil.rmtree(user_data_dir, ignore_errors=True)
        finally:
            playwright.stop()
        raise SystemExit(
            "Error: Microsoft Edge is required. "
            "Install from https://www.microsoft.com/edge and try again."
        ) from exc

    return playwright, browser, page, msedge_pid, tracked_pids, user_data_dir


def close_browser(playwright, browser, msedge_pid, tracked_pids, user_data_dir) -> None:
    print("Closing Playwright Edge session...", flush=True)

    if msedge_pid:
        tracked_pids.update(get_process_tree_pids(msedge_pid))

    if browser is not None:
        try:
            browser.close()
        except Exception:
            pass

    if playwright is not None:
        try:
            playwright.stop()
        except Exception:
            pass

    time.sleep(1)

    still_alive = set()

    for pid in tracked_pids:
        try:
            if psutil.pid_exists(pid):
                process = psutil.Process(pid)
                name = process.name().lower()

                if "msedge" in name or "msedgewebview2" in name:
                    still_alive.add(pid)

        except psutil.Error:
            pass

    if still_alive:
        kill_pids(still_alive)

    if user_data_dir:
        try:
            shutil.rmtree(user_data_dir, ignore_errors=True)
        except Exception:
            pass

    print("Edge and Playwright closed.", flush=True)


def main():
    parser = argparse.ArgumentParser(
        description="Live scrape a stock price from Trading Economics using Playwright + Microsoft Edge."
    )
    parser.add_argument(
        "-t",
        "--ticker",
        default="AAPL",
        help="Stock ticker to scrape. Default: AAPL. Examples: MSFT, TSLA, NVDA",
    )
    parser.add_argument(
        "-i",
        "--interval",
        type=float,
        default=0.001,
        help="Seconds between DOM polls. Default: 0.001",
    )
    parser.add_argument(
        "--output",
        help="Optional JSONL output file. Only writes when price changes.",
    )
    parser.add_argument(
        "--webhook-url",
        help="Optional webhook URL. Sends POST JSON only when price changes.",
    )
    parser.add_argument(
        "--webhook-timeout",
        type=float,
        default=3.0,
        help="Webhook request timeout in seconds.",
    )
    parser.add_argument(
        "--visible",
        action="store_true",
        help="Run Edge visibly. By default, Edge runs headless.",
    )
    parser.add_argument(
        "--no-print-first",
        action="store_true",
        help="Do not print the first detected price.",
    )

    args = parser.parse_args()

    symbol = args.ticker.upper()
    url = build_url(symbol)

    playwright = None
    browser = None
    page = None
    msedge_pid = None
    tracked_pids = set()
    user_data_dir = None

    last_price = None
    poll_count = 0

    _register_signal_handlers(close_browser)

    try:
        playwright, browser, page, msedge_pid, tracked_pids, user_data_dir = build_browser(
            headless=not args.visible
        )

        page.goto(url)
        time.sleep(5)

        if msedge_pid:
            tracked_pids.update(get_process_tree_pids(msedge_pid))

        print(f"Watching {symbol}. Press Ctrl+C to stop.", flush=True)

        while True:
            started = time.perf_counter()
            timestamp = datetime.now().isoformat(timespec="milliseconds")
            poll_count += 1

            try:
                data = extract_with_playwright_visible_text(page, symbol)

                data["timestamp"] = timestamp
                data["source"] = "Trading Economics"
                data["url"] = url
                data["poll_count"] = poll_count

                current_price = data.get("price")

                if current_price is not None:
                    is_first_price = last_price is None
                    has_changed = current_price != last_price

                    if has_changed and (not is_first_price or not args.no_print_first):
                        print_price_change(data, last_price)

                        if args.output:
                            with open(args.output, "a", encoding="utf-8") as file:
                                file.write(json.dumps(data, ensure_ascii=False) + "\n")

                        if args.webhook_url:
                            send_webhook(args.webhook_url, data, args.webhook_timeout)

                    last_price = current_price

            except Exception:
                pass

            elapsed = time.perf_counter() - started
            sleep_for = max(0, args.interval - elapsed)
            time.sleep(sleep_for)

    except KeyboardInterrupt:
        print("\nStopped manually.", flush=True)

    finally:
        close_browser(playwright, browser, msedge_pid, tracked_pids, user_data_dir)


if __name__ == "__main__":
    main()
