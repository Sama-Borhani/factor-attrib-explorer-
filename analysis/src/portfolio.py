from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json
import math
from typing import Dict

import pandas as pd


@dataclass(frozen=True)
class PortfolioSummary:
    tickers: list[str]
    weights: dict[str, float]
    start: str
    end: str
    frequency: str
    compounding: str
    missing_price_policy: str
    annualized_return: float
    annualized_vol: float
    max_drawdown: float


def _freq_to_periods_per_year(freq: str) -> int:
    if freq.upper().startswith("W"):
        return 52
    if freq.upper().startswith("D"):
        return 252
    if freq.upper().startswith("M"):
        return 12
    raise ValueError(f"Unsupported frequency for annualization: {freq}")


def _normalize_weights(weights: Dict[str, float], columns: pd.Index) -> pd.Series:
    w = pd.Series(weights, dtype=float).reindex(columns).fillna(0.0)
    total = float(w.sum())
    if total <= 0:
        raise ValueError("Weights must sum to a positive value.")
    return w / total


def compute_portfolio_returns(
    returns: pd.DataFrame,
    weights: Dict[str, float],
    missing_price_policy: str = "drop_any",
) -> pd.Series:
    r = returns.copy()
    w = _normalize_weights(weights, r.columns)

    if missing_price_policy == "drop_any":
        r = r.dropna(how="any")
    elif missing_price_policy == "drop_all":
        r = r.dropna(how="all")
    else:
        raise ValueError(f"Unknown missing_price_policy: {missing_price_policy}")

    port = (r * w).sum(axis=1)
    port.name = "port_ret"
    return port


def _max_drawdown(returns: pd.Series) -> float:
    wealth = (1 + returns).cumprod()
    running_max = wealth.cummax()
    drawdown = wealth / running_max - 1
    return float(drawdown.min())


def summarize_portfolio(
    returns: pd.DataFrame,
    weights: Dict[str, float],
    freq: str,
    missing_price_policy: str = "drop_any",
    compounding: str = "geometric",
) -> PortfolioSummary:
    port = compute_portfolio_returns(returns, weights, missing_price_policy=missing_price_policy)
    if port.empty:
        raise ValueError("Portfolio returns are empty after applying missing-price policy.")

    periods_per_year = _freq_to_periods_per_year(freq)
    total_periods = len(port)

    if compounding == "geometric":
        annualized_return = float((1 + port).prod() ** (periods_per_year / total_periods) - 1)
    elif compounding == "simple":
        annualized_return = float(port.mean() * periods_per_year)
    else:
        raise ValueError(f"Unknown compounding assumption: {compounding}")

    annualized_vol = float(port.std(ddof=1) * math.sqrt(periods_per_year))
    max_drawdown = _max_drawdown(port)

    start = str(port.index.min().date())
    end = str(port.index.max().date())

    summary = PortfolioSummary(
        tickers=list(returns.columns),
        weights=_normalize_weights(weights, returns.columns).to_dict(),
        start=start,
        end=end,
        frequency=freq,
        compounding=compounding,
        missing_price_policy=missing_price_policy,
        annualized_return=annualized_return,
        annualized_vol=annualized_vol,
        max_drawdown=max_drawdown,
    )
    return summary


def write_portfolio_summary(
    returns_path: Path,
    out_path: Path,
    weights: Dict[str, float],
    freq: str,
    missing_price_policy: str = "drop_any",
    compounding: str = "geometric",
) -> Path:
    df = pd.read_parquet(returns_path)
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    summary = summarize_portfolio(
        returns=df,
        weights=weights,
        freq=freq,
        missing_price_policy=missing_price_policy,
        compounding=compounding,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(asdict(summary), indent=2))
    return out_path
