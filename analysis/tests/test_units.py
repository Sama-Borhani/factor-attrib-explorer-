import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def test_factor_units_decimals():
    factors_dir = ROOT / "analysis" / "outputs" / "data" / "factors"
    us = pd.read_parquet(factors_dir / "F-F_Research_Data_Factors_weekly.parquet")
    med = us["MKT_RF"].abs().median()
    assert med < 0.2, f"Units too large (median abs={med}). Expected decimals, not percent."