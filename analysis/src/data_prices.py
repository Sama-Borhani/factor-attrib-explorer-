from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Dict, Tuple

import pandas as pd
import yfinance as yf


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _to_weekly_prices(adj_close: pd.DataFrame, freq: str) -> pd.DataFrame:
    # Use last available trading close in each weekly bucket (W-FRI)
    weekly = adj_close.resample(freq).last()
    weekly = weekly.dropna(how="all")
    return weekly


def _simple_returns(prices: pd.DataFrame) -> pd.DataFrame:
    rets = prices.pct_change()
    rets = rets.dropna(how="all")
    return rets


def fetch_prices_weekly(
    tickers: Tuple[str, ...],
    start: str,
    end: str | None,
    freq: str,
    cache_dir: Path,
    force: bool = False,
) -> Dict[str, Path]:
    """
    Downloads adjusted close prices via yfinance, converts to weekly prices and returns,
    and caches parquet outputs.

    Returns paths to cached files.
    """
    _ensure_dir(cache_dir)

    raw_path = cache_dir / "prices_raw.parquet"
    weekly_path = cache_dir / "prices_weekly.parquet"
    rets_path = cache_dir / "returns_weekly.parquet"
    report_path = cache_dir.parent / "reports" / "prices_quality_report.json"
    _ensure_dir(report_path.parent)

    if (not force) and raw_path.exists() and weekly_path.exists() and rets_path.exists():
        return {
            "raw": raw_path,
            "weekly_prices": weekly_path,
            "weekly_returns": rets_path,
            "report": report_path,
        }

    raw = yf.download(
        tickers=list(tickers),
        start=start,
        end=end,
        auto_adjust=False,      # we explicitly use Adj Close
        progress=False,
        group_by="column",
        actions=False,
    )

    # yfinance returns a multiindex when multiple tickers.
    # Prefer "Adj Close" for total-return-like series.
    if isinstance(raw.columns, pd.MultiIndex):
        if "Adj Close" in raw.columns.levels[0]:
            adj = raw["Adj Close"].copy()
        elif "Close" in raw.columns.levels[0]:
            adj = raw["Close"].copy()
        else:
            raise ValueError("Could not find Adj Close or Close in yfinance output.")
    else:
        # Single ticker case
        adj = raw.rename(columns={"Adj Close": tickers[0]}).get("Adj Close", raw.get("Close"))

    adj.index = pd.to_datetime(adj.index)
    adj = adj.sort_index()

    # Cache raw adjusted close daily
    adj.to_parquet(raw_path)

    weekly_prices = _to_weekly_prices(adj, freq=freq)
    weekly_prices.to_parquet(weekly_path)

    weekly_returns = _simple_returns(weekly_prices)
    weekly_returns.to_parquet(rets_path)

    # Quality report
    missing_pct = (weekly_prices.isna().mean() * 100).round(2).to_dict()
    coverage = {}
    for t in tickers:
        s = weekly_prices[t].dropna()
        coverage[t] = {
            "start": str(s.index.min().date()) if not s.empty else None,
            "end": str(s.index.max().date()) if not s.empty else None,
            "rows_non_missing": int(s.shape[0]),
        }

    report = {
        "tickers": list(tickers),
        "freq": freq,
        "start": start,
        "end": end,
        "rows_weekly_prices": int(weekly_prices.shape[0]),
        "rows_weekly_returns": int(weekly_returns.shape[0]),
        "missing_pct_weekly_prices": missing_pct,
        "coverage": coverage,
        "note": "Weekly prices use last available trading day in each W-FRI bucket. Returns are simple pct_change.",
    }

    pd.Series(report).to_json(report_path, indent=2)

    return {
        "raw": raw_path,
        "weekly_prices": weekly_path,
        "weekly_returns": rets_path,
        "report": report_path,
    }
