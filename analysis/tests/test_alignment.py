import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def test_outputs_exist():
    assert (ROOT/"analysis/outputs/data/returns_weekly.parquet").exists()
    assert (ROOT/"analysis/outputs/data/factors").exists()
    assert (ROOT/"analysis/outputs/data/frames").exists()

def test_frames_no_nans_and_monotonic():
    frames_dir = ROOT / "analysis" / "outputs" / "data" / "frames"
    for name in ["frame_equity_us.parquet", "frame_equity_intl.parquet", "frame_total_macro.parquet"]:
        df = pd.read_parquet(frames_dir / name)
        assert df.index.is_monotonic_increasing
        assert df.isna().sum().sum() == 0
        assert len(df) > 50


def test_factor_index_is_datetime():
    import pandas as pd
    from pathlib import Path

    ROOT = Path(__file__).resolve().parents[2]
    factors_dir = ROOT / "analysis" / "outputs" / "data" / "factors"
    us = pd.read_parquet(factors_dir / "F-F_Research_Data_Factors_weekly.parquet")
    assert hasattr(us.index, "dtype")
    assert "datetime" in str(us.index.dtype).lower()
