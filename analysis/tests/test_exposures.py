import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def test_exposures_exist_and_reasonable():
    p = ROOT / "analysis" / "outputs" / "data" / "exposures" / "exposures_equity_us.parquet"
    df = pd.read_parquet(p)
    assert len(df) > 50
    assert df["r2"].between(0, 1).all()
    assert df["nobs"].min() >= 40
