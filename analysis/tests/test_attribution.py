from pathlib import Path

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
