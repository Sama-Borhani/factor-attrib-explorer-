from __future__ import annotations

from pathlib import Path
from typing import List

import pandas as pd


def compute_attribution(
    frame: pd.DataFrame,
    exposures: pd.DataFrame,
    y_col: str = "Y",
) -> pd.DataFrame:
    """
    Attribution identity (no look-ahead):
      explained_t = alpha_{t-1} + sum_j beta_{j,t-1} * x_{j,t}
      residual_t  = y_t - explained_t

    frame: columns [Y, X1, X2, ...] indexed by date
    exposures: columns [alpha, beta_X1, beta_X2, ...] indexed by date
    """
    frame = frame.copy()
    frame.index = pd.to_datetime(frame.index)
    frame = frame.sort_index()

    exposures = exposures.copy()
    exposures.index = pd.to_datetime(exposures.index)
    exposures = exposures.sort_index()

    x_cols: List[str] = [c for c in frame.columns if c != y_col]
    exp_lag = exposures.shift(1)

    needed_cols = ["alpha"] + [f"beta_{c}" for c in x_cols]
    exp_lag = exp_lag[needed_cols]

    df = pd.concat([frame[[y_col] + x_cols], exp_lag], axis=1, join="inner").dropna()

    out = pd.DataFrame(index=df.index)
    out["y"] = df[y_col]
    out["alpha_contrib"] = df["alpha"]

    explained = df["alpha"].copy()

    for c in x_cols:
        contrib = df[f"beta_{c}"] * df[c]
        out[f"contrib_{c}"] = contrib
        explained = explained + contrib

    out["explained"] = explained
    out["residual"] = out["y"] - out["explained"]
    return out


def attribution_from_parquets(
    frame_path: Path,
    exposures_path: Path,
    out_path: Path,
    y_col: str = "Y",
) -> Path:
    frame = pd.read_parquet(frame_path)
    exposures = pd.read_parquet(exposures_path)

    attrib = compute_attribution(frame=frame, exposures=exposures, y_col=y_col)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    attrib.to_parquet(out_path)
    return out_path
