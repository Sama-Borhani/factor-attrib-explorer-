from __future__ import annotations

import re
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def assert_sorted_unique_dates(dates: List[str], label: str) -> None:
    if dates != sorted(dates):
        raise ValueError(f"{label}: dates are not sorted ascending")
    if len(dates) != len(set(dates)):
        raise ValueError(f"{label}: dates contain duplicates")


class MetaRegime(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vol_window_weeks: int
    percentile: float
    lookback_weeks: int


class Meta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tickers: List[str]
    weights: List[float]
    frequency: str
    rolling_window_weeks: int
    min_nobs: int
    regime: MetaRegime


class ExposureRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: str
    alpha: float
    r2: float
    nobs: int
    beta_MKT_RF: float
    beta_SMB: float
    beta_HML: float

    @field_validator("date")
    @classmethod
    def valid_date(cls, v: str) -> str:
        if not DATE_RE.match(v):
            raise ValueError(f"invalid date format: {v}")
        return v


class RegimeRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: str
    regime: Literal["calm", "stress"]
    vol: float
    vol_thresh: float

    @field_validator("date")
    @classmethod
    def valid_date(cls, v: str) -> str:
        if not DATE_RE.match(v):
            raise ValueError(f"invalid date format: {v}")
        return v


class AttribRow(BaseModel):
    """
    Attribution rows are dynamic because contrib_* keys can vary.
    We still enforce:
      - required date
      - all other keys must be numeric (or null -> treated as 0 downstream)
    """
    model_config = ConfigDict(extra="allow")

    date: str

    @field_validator("date")
    @classmethod
    def valid_date(cls, v: str) -> str:
        if not DATE_RE.match(v):
            raise ValueError(f"invalid date format: {v}")
        return v

    @field_validator("*", mode="before")
    @classmethod
    def numeric_or_null_for_non_date(cls, v: Any, info):
        if info.field_name == "date":
            return v
        # allow null
        if v is None:
            return v
        # allow numbers only
        if isinstance(v, (int, float)):
            return float(v)
        raise ValueError(f"attribution field '{info.field_name}' must be number or null, got {type(v).__name__}")


def validate_attrib_keys(rows: List[AttribRow], label: str) -> None:
    # Ensure all rows share the same key set (common failure mode)
    if not rows:
        return
    base_keys = set(rows[0].__dict__.keys())
    # includes dynamic keys + 'date'
    for i, r in enumerate(rows[1:], start=1):
        k = set(r.__dict__.keys())
        if k != base_keys:
            missing = sorted(base_keys - k)
            extra = sorted(k - base_keys)
            raise ValueError(
                f"{label}: key mismatch at row {i} date={r.date}. "
                f"missing={missing[:10]} extra={extra[:10]}"
            )


def align_by_intersection(
    exposures: List[ExposureRow],
    attribution: List[AttribRow],
    regimes: List[RegimeRow],
):
    Sexp = {r.date for r in exposures}
    Satt = {r.date for r in attribution}
    Sreg = {r.date for r in regimes}

    common = sorted(Sexp & Satt & Sreg)
    C = set(common)

    ex = [r for r in exposures if r.date in C]
    at = [r for r in attribution if r.date in C]
    rg = [r for r in regimes if r.date in C]

    # enforce aligned lengths & same date set
    if not (len(ex) == len(at) == len(rg) == len(common)):
        raise ValueError("alignment produced inconsistent lengths")

    return common, ex, at, rg
