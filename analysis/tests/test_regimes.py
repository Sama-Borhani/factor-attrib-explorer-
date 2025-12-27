from pathlib import Path
import json

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]


def test_regime_labels_and_fraction():
    regimes_path = ROOT / "analysis" / "outputs" / "data" / "regimes" / "regimes.parquet"
    summary_path = ROOT / "analysis" / "outputs" / "reports" / "regime_summary.json"

    regimes = pd.read_parquet(regimes_path)
    assert set(regimes["regime"].unique()) <= {"calm", "stress"}

    summary = json.loads(summary_path.read_text())
    stress_fraction = summary["stress_fraction"]
    assert 0.15 <= stress_fraction <= 0.35
