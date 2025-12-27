from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import pandas as pd

from analysis.src.schemas import (
    AttributionRow,
    ExposureRow,
    ManifestModel,
    MetaModel,
    RegimesPayload,
)


def _df_to_records(df: pd.DataFrame, date_col: str = "date") -> list[dict]:
    df = df.copy()
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    df[date_col] = df.index.strftime("%Y-%m-%d")
    df = df.reset_index(drop=True)
    return df.to_dict(orient="records")


def _validate(model, data):
    if hasattr(model, "model_validate"):
        return model.model_validate(data)
    return model.parse_obj(data)


def _model_dump_json(model, indent: int = 2) -> str:
    if hasattr(model, "model_dump_json"):
        return model.model_dump_json(indent=indent)
    return model.json(indent=indent)


def _find_git_root(start: Path) -> Path | None:
    current = start.resolve()
    for _ in range(10):
        if (current / ".git").exists():
            return current
        if current.parent == current:
            break
        current = current.parent
    return None


def _git_commit_hash(start: Path) -> str | None:
    try:
        repo_root = _find_git_root(start)
        if repo_root is None:
            return None
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except Exception:
        return None


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

    # meta (validated)
    meta_model = _validate(MetaModel, meta)
    meta_path = out_json_dir / "meta.json"
    meta_path.write_text(_model_dump_json(meta_model, indent=2))

    # exposures
    exp_us = pd.read_parquet(exposures_us_path)
    exp_intl = pd.read_parquet(exposures_intl_path)
    for df in (exp_us, exp_intl):
        df["rolling_window_weeks"] = meta.get("rolling_window_weeks")
        df["min_nobs"] = meta.get("min_nobs")

    exp_us_rows = _df_to_records(exp_us)
    exp_intl_rows = _df_to_records(exp_intl)
    for row in exp_us_rows:
        _validate(ExposureRow, row)
    for row in exp_intl_rows:
        _validate(ExposureRow, row)

    (out_json_dir / "exposures_equity_us.json").write_text(json.dumps(exp_us_rows, indent=2))
    (out_json_dir / "exposures_equity_intl.json").write_text(json.dumps(exp_intl_rows, indent=2))

    # attribution
    a_us = pd.read_parquet(attrib_us_path)
    a_intl = pd.read_parquet(attrib_intl_path)

    keep_cols = [
        c
        for c in a_us.columns
        if c
        in {
            "y",
            "alpha_contrib",
            "explained_return",
            "residual_return",
            "explained_share",
            "cum_explained_return",
            "cum_residual_return",
        }
        or c.startswith("contrib_")
        or c.startswith("cum_contrib_")
    ]
    attrib_us_rows = _df_to_records(a_us[keep_cols])
    attrib_intl_rows = _df_to_records(a_intl[keep_cols_i])
    for row in attrib_us_rows:
        if not any(k.startswith("contrib_") for k in row.keys()):
            raise ValueError("Attribution row missing factor contributions.")
        _validate(AttributionRow, row)
    for row in attrib_intl_rows:
        if not any(k.startswith("contrib_") for k in row.keys()):
            raise ValueError("Attribution row missing factor contributions.")
        _validate(AttributionRow, row)

    (out_json_dir / "attribution_equity_us.json").write_text(json.dumps(attrib_us_rows, indent=2))

    keep_cols_i = [
        c
        for c in a_intl.columns
        if c
        in {
            "y",
            "alpha_contrib",
            "explained_return",
            "residual_return",
            "explained_share",
            "cum_explained_return",
            "cum_residual_return",
        }
        or c.startswith("contrib_")
        or c.startswith("cum_contrib_")
    ]
    (out_json_dir / "attribution_equity_intl.json").write_text(json.dumps(attrib_intl_rows, indent=2))

    # regimes
    reg = pd.read_parquet(regimes_path)
    reg = reg[["regime", "vol", "vol_thresh"]].copy()
    reg_rows = _df_to_records(reg)

    summary_payload = json.loads(Path(regime_summary_path).read_text())
    regimes_payload = {
        "metadata": summary_payload.get("metadata", {}),
        "stress_fraction": summary_payload.get("stress_fraction"),
        "summary": summary_payload.get("summary", {}),
        "data": reg_rows,
    }
    _validate(RegimesPayload, regimes_payload)

    (out_json_dir / "regimes.json").write_text(json.dumps(regimes_payload, indent=2))

    # regime summary (already json)
    out_sum = out_json_dir / "regime_summary.json"
    out_sum.write_text(json.dumps(summary_payload, indent=2))

    # manifest
    manifest = {
        "build_timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit_hash(out_json_dir),
        "config": {
            "tickers": meta_model.tickers,
            "weights": meta_model.weights,
            "frequency": meta_model.frequency,
            "rolling_window_weeks": meta_model.rolling_window_weeks,
            "min_nobs": meta_model.min_nobs,
            "factor_set": meta_model.factor_set,
        },
        "regime_rule": meta_model.regime,
        "units": {
            "returns": "decimals (e.g., 0.01 = 1%)",
            "factors": "decimals (e.g., 0.01 = 1%)",
            "volatility": "standard deviation of returns (decimals)",
        },
        "disclaimers": [
            "This project is for educational and illustrative purposes only.",
            "No forecasting or trading signals are produced.",
            "Past performance does not guarantee future results.",
        ],
    }
    manifest_model = _validate(ManifestModel, manifest)
    manifest_path = out_json_dir / "manifest.json"
    manifest_path.write_text(_model_dump_json(manifest_model, indent=2))

    return {
        "meta": meta_path,
        "exposures_us": out_json_dir / "exposures_equity_us.json",
        "exposures_intl": out_json_dir / "exposures_equity_intl.json",
        "attrib_us": out_json_dir / "attribution_equity_us.json",
        "attrib_intl": out_json_dir / "attribution_equity_intl.json",
        "regimes": out_json_dir / "regimes.json",
        "regime_summary": out_sum,
        "manifest": manifest_path,
    }
