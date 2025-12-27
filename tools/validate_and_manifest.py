import json
from pathlib import Path
from typing import Any, Dict, List, Tuple
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

DATA_DIR = Path("site/public/data")

META = DATA_DIR / "meta.json"
EXP_US = DATA_DIR / "exposures_equity_us.json"
EXP_INTL = DATA_DIR / "exposures_equity_intl.json"
ATT_US = DATA_DIR / "attribution_equity_us.json"
ATT_INTL = DATA_DIR / "attribution_equity_intl.json"
REG = DATA_DIR / "regimes.json"
MANIFEST = DATA_DIR / "manifest.json"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def is_sorted_unique(dates: List[str]) -> Tuple[bool, bool]:
    sorted_ok = dates == sorted(dates)
    unique_ok = len(dates) == len(set(dates))
    return sorted_ok, unique_ok


def require_list_of_dicts(name: str, obj: Any) -> List[Dict[str, Any]]:
    if not isinstance(obj, list):
        raise ValueError(f"{name}: expected list, got {type(obj)}")
    for i, row in enumerate(obj[:5]):
        if not isinstance(row, dict):
            raise ValueError(f"{name}: row {i} expected dict, got {type(row)}")
    return obj  # type: ignore


def require_dates(name: str, rows: List[Dict[str, Any]]) -> List[str]:
    dates = []
    for i, r in enumerate(rows):
        if "date" not in r:
            raise ValueError(f"{name}: row {i} missing 'date'")
        if not isinstance(r["date"], str):
            raise ValueError(f"{name}: row {i} 'date' must be string")
        dates.append(r["date"])
    return dates


def align_by_intersection(
    exposures: List[Dict[str, Any]],
    attribution: List[Dict[str, Any]],
    regimes: List[Dict[str, Any]],
) -> Dict[str, Any]:
    Sexp = set(r["date"] for r in exposures)
    Satt = set(r["date"] for r in attribution)
    Sreg = set(r["date"] for r in regimes)

    common = sorted([d for d in Sexp if d in Satt and d in Sreg])
    C = set(common)

    exp2 = [r for r in exposures if r["date"] in C]
    att2 = [r for r in attribution if r["date"] in C]
    reg2 = [r for r in regimes if r["date"] in C]

    return {
        "exposures": exp2,
        "attribution": att2,
        "regimes": reg2,
        "start": common[0] if common else None,
        "end": common[-1] if common else None,
        "aligned_n": len(common),
    }


class RegimeCfg(BaseModel):
    vol_window_weeks: int = Field(..., ge=1)
    percentile: float = Field(..., gt=0, lt=1)
    lookback_weeks: int = Field(..., ge=1)


class Meta(BaseModel):
    tickers: List[str]
    weights: List[float]
    frequency: str
    rolling_window_weeks: int = Field(..., ge=1)
    min_nobs: int = Field(..., ge=1)
    regime: RegimeCfg

    @field_validator("tickers")
    @classmethod
    def tickers_nonempty(cls, v):
        if not v:
            raise ValueError("tickers must not be empty")
        return v

    @model_validator(mode="after")
    def weights_match(self):
        if len(self.tickers) != len(self.weights):
            raise ValueError(f"tickers/weights length mismatch: {len(self.tickers)} vs {len(self.weights)}")
        return self


def validate_dataset(path: Path, name: str) -> Dict[str, Any]:
    rows = require_list_of_dicts(name, load_json(path))
    dates = require_dates(name, rows)
    sorted_ok, unique_ok = is_sorted_unique(dates)
    if not sorted_ok or not unique_ok:
        raise ValueError(f"{name}: dates sorted={sorted_ok}, unique={unique_ok}")
    return {"rows": rows, "n": len(rows), "start": dates[0], "end": dates[-1]}


def main():
    # Validate meta
    meta_raw = load_json(META)
    meta = Meta.model_validate(meta_raw)

    # Validate datasets
    exp_us = validate_dataset(EXP_US, "exposures_us")
    exp_intl = validate_dataset(EXP_INTL, "exposures_intl")
    att_us = validate_dataset(ATT_US, "attribution_us")
    att_intl = validate_dataset(ATT_INTL, "attribution_intl")
    reg = validate_dataset(REG, "regimes")

    # Align US and INTL separately
    aligned_us = align_by_intersection(exp_us["rows"], att_us["rows"], reg["rows"])
    aligned_intl = align_by_intersection(exp_intl["rows"], att_intl["rows"], reg["rows"])

    # sanity: aligned counts must match
    for label, A in [("US", aligned_us), ("INTL", aligned_intl)]:
        if not (len(A["exposures"]) == len(A["attribution"]) == len(A["regimes"])):
            raise ValueError(f"{label}: aligned lengths mismatch")

    print("✅ Data validation PASSED\n")

    print("US:")
    print(f"  raw:     exp={exp_us['n']} att={att_us['n']} reg={reg['n']}")
    print(f"  aligned: exp={len(aligned_us['exposures'])} att={len(aligned_us['attribution'])} reg={len(aligned_us['regimes'])}")
    print(f"  range:   {aligned_us['start']} → {aligned_us['end']}\n")

    print("INTL:")
    print(f"  raw:     exp={exp_intl['n']} att={att_intl['n']} reg={reg['n']}")
    print(f"  aligned: exp={len(aligned_intl['exposures'])} att={len(aligned_intl['attribution'])} reg={len(aligned_intl['regimes'])}")
    print(f"  range:   {aligned_intl['start']} → {aligned_intl['end']}\n")

    manifest = {
        "meta": meta.model_dump(),
        "raw": {
            "us": {"exp": exp_us["n"], "att": att_us["n"], "reg": reg["n"], "start": exp_us["start"], "end": exp_us["end"]},
            "intl": {"exp": exp_intl["n"], "att": att_intl["n"], "reg": reg["n"], "start": exp_intl["start"], "end": exp_intl["end"]},
        },
        "aligned": {
            "us": {"exp": len(aligned_us["exposures"]), "att": len(aligned_us["attribution"]), "reg": len(aligned_us["regimes"]), "start": aligned_us["start"], "end": aligned_us["end"]},
            "intl": {"exp": len(aligned_intl["exposures"]), "att": len(aligned_intl["attribution"]), "reg": len(aligned_intl["regimes"]), "start": aligned_intl["start"], "end": aligned_intl["end"]},
        },
        "notes": {
            "alignment_rule": "intersection of dates across exposures, attribution, regimes",
            "data_dir": str(DATA_DIR),
        },
    }

    MANIFEST.write_text(json.dumps(manifest, indent=2))
    print(f"🧾 Wrote manifest: {MANIFEST.resolve()}")


if __name__ == "__main__":
    try:
        main()
    except ValidationError as e:
        print("❌ Pydantic validation failed:\n", e)
        raise
