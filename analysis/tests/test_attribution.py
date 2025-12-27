from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]


def test_attribution_identity_and_lagged_betas():
    frame_path = ROOT / "analysis" / "outputs" / "data" / "frames" / "frame_equity_us.parquet"
    exposures_path = ROOT / "analysis" / "outputs" / "data" / "exposures" / "exposures_equity_us.parquet"
    attrib_path = ROOT / "analysis" / "outputs" / "data" / "attribution" / "attrib_equity_us.parquet"

    frame = pd.read_parquet(frame_path).sort_index()
    exposures = pd.read_parquet(exposures_path).sort_index()
    attrib = pd.read_parquet(attrib_path).sort_index()

    # Lagged betas: attribution should not start on the same date as first exposure
    assert attrib.index.min() > exposures.index.min()

    # Identity: y_t = alpha_{t-1} + sum(beta_{t-1} * x_t) + residual_t
    x_cols = [c for c in frame.columns if c != "Y"]
    exp_lag = exposures.shift(1)
    df = pd.concat([frame[["Y"] + x_cols], exp_lag], axis=1, join="inner").dropna()

    explained = df["alpha"]
    for c in x_cols:
        explained = explained + df[f"beta_{c}"] * df[c]

    residual = df["Y"] - explained

    aligned = attrib.loc[df.index]
    diff_explained = (aligned["explained_return"] - explained).abs()
    diff_residual = (aligned["residual_return"] - residual).abs()

    assert np.nanmax(diff_explained) < 1e-10
    assert np.nanmax(diff_residual) < 1e-10
