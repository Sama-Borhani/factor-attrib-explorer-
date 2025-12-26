from __future__ import annotations
from pathlib import Path
import json
import numpy as np
import pandas as pd

def compute_regimes(
    returns: pd.Series,
    vol_window_weeks: int,
    lookback_weeks: int,
    percentile: float,
) -> pd.DataFrame:
    """
    Regime label without look-ahead:
    - vol_t = rolling std over vol_window
    - threshold_t computed from trailing lookback of vol (ending at t-1)
    - stress_t = vol_t >= threshold_t
    """
    r = returns.dropna().sort_index().copy()
    vol = r.rolling(vol_window_weeks).std()
    thresh = vol.shift(1).rolling(lookback_weeks).quantile(percentile)
    df = pd.DataFrame({"ret": r, "vol": vol, "vol_thresh": thresh})
    df["is_stress"] = (df["vol"] >= df["vol_thresh"]).astype("Int64")
    df = df.dropna()
    df["regime"] = df["is_stress"].map({0: "calm", 1: "stress"})
    return df

def regimes_and_summary(
    returns_path: Path,
    exposures_path: Path,
    out_regimes_path: Path,
    out_summary_path: Path,
    vol_window_weeks: int,
    lookback_weeks: int,
    percentile: float,
    weights: dict[str, float] | None = None,
) -> tuple[Path, Path]:
    rets = pd.read_parquet(returns_path)
    rets.index = pd.to_datetime(rets.index)
    rets = rets.sort_index()

    # Use explicit weights (config weights if provided, else equal-weight)
    if weights is None:
        w = pd.Series(1.0 / rets.shape[1], index=rets.columns, dtype=float)
    else:
        w = pd.Series(weights, dtype=float)
        # Align weights to columns we actually have
        w = w.reindex(rets.columns).fillna(0.0)
        w = w / w.sum()

    port = (rets * w).sum(axis=1)
    port.name = "port_ret"

    regimes = compute_regimes(
        returns=port,
        vol_window_weeks=vol_window_weeks,
        lookback_weeks=lookback_weeks,
        percentile=percentile,
    )
    out_regimes_path.parent.mkdir(parents=True, exist_ok=True)
    regimes.to_parquet(out_regimes_path)

    exp = pd.read_parquet(exposures_path)
    exp.index = pd.to_datetime(exp.index)
    exp = exp.sort_index()

    merged = exp.join(regimes[["regime"]], how="inner").dropna()
    summary = merged.groupby("regime").mean(numeric_only=True).to_dict()

    out_summary_path.parent.mkdir(parents=True, exist_ok=True)
    out_summary_path.write_text(json.dumps(summary, indent=2))

    return out_regimes_path, out_summary_path