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
import pandas as pd

from analysis.src.attribution import compute_attribution

ROOT = Path(__file__).resolve().parents[2]


def test_attribution_identity_and_lag():
    frame_path = ROOT / "analysis" / "outputs" / "data" / "frames" / "frame_equity_us.parquet"
    exposures_path = ROOT / "analysis" / "outputs" / "data" / "exposures" / "exposures_equity_us.parquet"

    frame = pd.read_parquet(frame_path).sort_index()
    exposures = pd.read_parquet(exposures_path).sort_index()

    attrib = compute_attribution(frame=frame, exposures=exposures, y_col="Y")
    x_cols = [c for c in frame.columns if c != "Y"]

    summed = attrib[["alpha_contrib"] + [f"contrib_{c}" for c in x_cols]].sum(axis=1)
    residual = attrib["y"] - summed
    assert (residual - attrib["residual"]).abs().max() < 1e-12

    first_date = attrib.index[0]
    first_pos = exposures.index.get_loc(first_date)
    assert first_pos > 0
    prev_date = exposures.index[first_pos - 1]
    factor = x_cols[0]
    expected = exposures.loc[prev_date, f"beta_{factor}"] * frame.loc[first_date, factor]
    assert abs(attrib.loc[first_date, f"contrib_{factor}"] - expected) < 1e-12


def test_residual_not_dominant_everywhere():
    attrib_path = ROOT / "analysis" / "outputs" / "data" / "attribution" / "attrib_equity_us.parquet"
    attrib = pd.read_parquet(attrib_path).sort_index()

    median_resid = attrib["residual"].abs().median()
    median_y = attrib["y"].abs().median()
    assert median_resid <= 5 * median_y
