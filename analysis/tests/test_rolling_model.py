from pathlib import Path

import pandas as pd

from analysis.src.config import get_config

ROOT = Path(__file__).resolve().parents[2]


def test_rolling_window_valid_and_warmup():
    cfg = get_config()
    frame_path = ROOT / "analysis" / "outputs" / "data" / "frames" / "frame_equity_us.parquet"
    exposures_path = ROOT / "analysis" / "outputs" / "data" / "exposures" / "exposures_equity_us.parquet"

    frame = pd.read_parquet(frame_path)
    exposures = pd.read_parquet(exposures_path)

    x_cols = [c for c in frame.columns if c != "Y"]
    assert cfg.rolling_window_weeks > len(x_cols) + 1

    frame = frame.sort_index()
    exposures = exposures.sort_index()

    expected_len = max(0, len(frame) - cfg.rolling_window_weeks + 1)
    assert len(exposures) == expected_len

    first_possible = frame.index[cfg.rolling_window_weeks - 1]
    assert exposures.index.min() >= first_possible


def test_no_lookahead_and_stderr_present():
    frame_path = ROOT / "analysis" / "outputs" / "data" / "frames" / "frame_equity_us.parquet"
    exposures_path = ROOT / "analysis" / "outputs" / "data" / "exposures" / "exposures_equity_us.parquet"

    frame = pd.read_parquet(frame_path).sort_index()
    exposures = pd.read_parquet(exposures_path).sort_index()

    assert exposures.index.max() == frame.index.max()
    assert "stderr_alpha" in exposures.columns
    assert any(c.startswith("stderr_beta_") for c in exposures.columns)
