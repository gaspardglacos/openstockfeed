import os
import certifi
import requests
from io import StringIO
from datetime import date, timedelta

os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()
os.environ["CURL_CA_BUNDLE"] = certifi.where()

import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt


start = "2025-02-10"
end_date = date.today()
end = (end_date + timedelta(days=1)).isoformat()

futures_symbol = "GCN26.CMX"


def download_spot_gold_from_stooq():
    print("Downloading spot gold from Stooq...")

    d1 = start.replace("-", "")
    d2 = end_date.strftime("%Y%m%d")

    url = f"https://stooq.com/q/d/l/?s=xauusd&d1={d1}&d2={d2}&i=d"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(url, headers=headers, timeout=30, verify=certifi.where())

    if response.status_code != 200:
        raise RuntimeError(f"Stooq download failed. HTTP status: {response.status_code}")

    if "No data" in response.text or len(response.text.strip()) < 20:
        raise RuntimeError("Stooq returned no usable spot gold data.")

    df = pd.read_csv(StringIO(response.text))

    if df.empty:
        raise RuntimeError("Spot gold CSV is empty.")

    df.columns = [str(c).strip() for c in df.columns]

    if "Date" not in df.columns or "Close" not in df.columns:
        raise RuntimeError(f"Unexpected Stooq columns: {list(df.columns)}")

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Close"] = pd.to_numeric(df["Close"], errors="coerce")

    df = df[["Date", "Close"]].dropna()
    df = df.rename(columns={"Close": "Gold Spot XAU/USD"})
    df = df.set_index("Date").sort_index()

    return df["Gold Spot XAU/USD"]


def download_futures_from_yahoo(symbol):
    print(f"Downloading futures from Yahoo: {symbol}...")

    df = yf.download(
        symbol,
        start=start,
        end=end,
        auto_adjust=False,
        progress=False,
        threads=False
    )

    if df.empty:
        raise RuntimeError(
            f"No data downloaded for {symbol}. "
            "Yahoo may not provide historical data for this exact futures contract."
        )

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    if "Close" not in df.columns:
        raise RuntimeError(f"No Close column found for {symbol}. Columns found: {list(df.columns)}")

    close = df["Close"].copy()
    close.name = "GCN26 Futures"

    return close


spot_close = download_spot_gold_from_stooq()
futures_close = download_futures_from_yahoo(futures_symbol)

data = pd.concat([spot_close, futures_close], axis=1).dropna()

if data.empty:
    raise RuntimeError(
        "Both series downloaded, but there are no overlapping dates. "
        "This can happen if Yahoo has limited GCN26 history."
    )

data["Basis"] = data["GCN26 Futures"] - data["Gold Spot XAU/USD"]
data["Basis %"] = data["Basis"] / data["Gold Spot XAU/USD"] * 100

print("\nDownloaded data successfully.")
print(data.tail())

print("\nSummary:")
print(f"Start date: {data.index[0].date()}")
print(f"End date:   {data.index[-1].date()}")

print("\nStart prices:")
print(data.iloc[0][["Gold Spot XAU/USD", "GCN26 Futures"]])

print("\nLatest prices:")
print(data.iloc[-1][["Gold Spot XAU/USD", "GCN26 Futures"]])

spot_return = data["Gold Spot XAU/USD"].iloc[-1] / data["Gold Spot XAU/USD"].iloc[0] - 1
futures_return = data["GCN26 Futures"].iloc[-1] / data["GCN26 Futures"].iloc[0] - 1

print("\nReturns:")
print(f"Gold Spot return:     {spot_return:.2%}")
print(f"GCN26 Futures return: {futures_return:.2%}")

print("\nLatest basis:")
print(f"Basis:   ${data['Basis'].iloc[-1]:.2f}")
print(f"Basis %: {data['Basis %'].iloc[-1]:.2f}%")

# Chart 1:
