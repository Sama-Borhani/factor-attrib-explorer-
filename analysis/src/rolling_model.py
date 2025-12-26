from __future__ import annotations

from pathlib import Path
from typing import List

import numpy as np
import pandas as pd
import statsmodels.api as sm


def run_rolling_ols(
    frame: pd.DataFrame,
    y_col: str,
    x_cols: List[str],
    window: int,
    min_nobs: int,
) -> pd.DataFrame:
    """
    Rolling OLS using a simple loop (robust + transparent).
    frame: must be sorted by datetime index and have no NaNs in y/x.
    Returns DataFrame indexed by end-of-window date with:
      alpha, betas..., r2, nobs
    """
    df = frame[[y_col] + x_cols].dropna().copy()
    df = df.sort_index()

    y = df[y_col].values
    X = df[x_cols].values
    dates = df.index

    out_rows = []
    out_index = []

    for end_i in range(len(df)):
        start_i = end_i - window + 1
        if start_i < 0:
            continue

        y_w = y[start_i : end_i + 1]
        X_w = X[start_i : end_i + 1, :]

        # enforce minimum observations
        if len(y_w) < min_nobs:
            continue

        X_w_const = sm.add_constant(X_w, has_constant="add")
        model = sm.OLS(y_w, X_w_const, missing="drop").fit()

        row = {
            "alpha": float(model.params[0]),
            "r2": float(model.rsquared),
            "nobs": int(model.nobs),
        }

        # betas
        for j, c in enumerate(x_cols, start=1):
            row[f"beta_{c}"] = float(model.params[j])

        out_rows.append(row)
        out_index.append(dates[end_i])

    out = pd.DataFrame(out_rows, index=pd.DatetimeIndex(out_index, name="date"))
    return out


def run_rolling_from_parquet(
    frame_path: Path,
    out_path: Path,
    window: int,
    min_nobs: int,
    y_col: str = "Y",
) -> Path:
    frame = pd.read_parquet(frame_path)
    frame.index = pd.to_datetime(frame.index)
    frame = frame.sort_index()

    x_cols = [c for c in frame.columns if c != y_col]
    exposures = run_rolling_ols(frame, y_col=y_col, x_cols=x_cols, window=window, min_nobs=min_nobs)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    exposures.to_parquet(out_path)
    return out_path
