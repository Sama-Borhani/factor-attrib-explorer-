from __future__ import annotations

import json
from pathlib import Path
import pandas as pd


def _df_to_records(df: pd.DataFrame, date_col: str = "date") -> list[dict]:
    df = df.copy()
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    df[date_col] = df.index.strftime("%Y-%m-%d")
    df = df.reset_index(drop=True)
    return df.to_dict(orient="records")


def export_json_bundle(
    out_json_dir: Path,
    meta: dict,
    exposures_us_path: Path,
    exposures_intl_path: Path,
    attrib_us_path: Path,
    attrib_intl_path: Path,
    regimes_path: Path,
    regime_summary_path: Path,
) -> dict[str, Path]:
    out_json_dir.mkdir(parents=True, exist_ok=True)

    # meta
    meta_path = out_json_dir / "meta.json"
    meta_path.write_text(json.dumps(meta, indent=2))

    # exposures
    exp_us = pd.read_parquet(exposures_us_path)
    exp_intl = pd.read_parquet(exposures_intl_path)
    (out_json_dir / "exposures_equity_us.json").write_text(json.dumps(_df_to_records(exp_us), indent=2))
    (out_json_dir / "exposures_equity_intl.json").write_text(json.dumps(_df_to_records(exp_intl), indent=2))

    # attribution (keep only the columns we actually plot)
    a_us = pd.read_parquet(attrib_us_path)
    a_intl = pd.read_parquet(attrib_intl_path)

    keep_cols = [c for c in a_us.columns if c in {"y","alpha_contrib","explained","residual"} or c.startswith("contrib_")]
    (out_json_dir / "attribution_equity_us.json").write_text(json.dumps(_df_to_records(a_us[keep_cols]), indent=2))

    keep_cols_i = [c for c in a_intl.columns if c in {"y","alpha_contrib","explained","residual"} or c.startswith("contrib_")]
    (out_json_dir / "attribution_equity_intl.json").write_text(json.dumps(_df_to_records(a_intl[keep_cols_i]), indent=2))

    # regimes
    reg = pd.read_parquet(regimes_path)
    reg = reg[["regime", "vol", "vol_thresh"]].copy()
    (out_json_dir / "regimes.json").write_text(json.dumps(_df_to_records(reg), indent=2))

    # regime summary (already json)
    out_sum = out_json_dir / "regime_summary.json"
    out_sum.write_text(Path(regime_summary_path).read_text())

    return {
        "meta": meta_path,
        "exposures_us": out_json_dir / "exposures_equity_us.json",
        "exposures_intl": out_json_dir / "exposures_equity_intl.json",
        "attrib_us": out_json_dir / "attribution_equity_us.json",
        "attrib_intl": out_json_dir / "attribution_equity_intl.json",
        "regimes": out_json_dir / "regimes.json",
        "regime_summary": out_sum,
    }
