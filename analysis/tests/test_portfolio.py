from pathlib import Path
import json

import pandas as pd

from analysis.src.portfolio import compute_portfolio_returns

ROOT = Path(__file__).resolve().parents[2]


def test_weights_sum_to_one():
    summary_path = ROOT / "analysis" / "outputs" / "reports" / "portfolio_summary.json"
    data = json.loads(summary_path.read_text())
    weights = pd.Series(data["weights"], dtype=float)
    assert abs(weights.sum() - 1.0) < 1e-6


def test_portfolio_matches_weighted_sum_spot_check():
    returns_path = ROOT / "analysis" / "outputs" / "data" / "returns_weekly.parquet"
    df = pd.read_parquet(returns_path)
    df.index = pd.to_datetime(df.index)

    summary_path = ROOT / "analysis" / "outputs" / "reports" / "portfolio_summary.json"
    data = json.loads(summary_path.read_text())
    weights = data["weights"]

    port = compute_portfolio_returns(df, weights=weights, missing_price_policy="drop_any")
    manual = (df.dropna(how="any") * pd.Series(weights)).sum(axis=1)

    aligned = port.loc[manual.index].head(5)
    assert (aligned - manual.head(5)).abs().max() < 1e-12
