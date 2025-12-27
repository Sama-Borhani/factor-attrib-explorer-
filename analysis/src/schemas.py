from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class MetaModel(BaseModel):
    tickers: List[str]
    weights: Dict[str, float]
    frequency: str
    rolling_window_weeks: int
    min_nobs: int
    factor_set: str
    regime: Dict[str, Any]


class ExposureRow(BaseModel):
    date: str
    alpha: float
    r2: float
    nobs: int
    rolling_window_weeks: int
    min_nobs: int

    class Config:
        extra = "allow"


class AttributionRow(BaseModel):
    date: str
    y: float
    alpha_contrib: float
    explained_return: float
    residual_return: float
    explained_share: Optional[float]
    cum_explained_return: float
    cum_residual_return: float

    class Config:
        extra = "allow"


class RegimeRow(BaseModel):
    date: str
    regime: str
    vol: float
    vol_thresh: float


class RegimesPayload(BaseModel):
    metadata: Dict[str, Any]
    stress_fraction: Optional[float]
    summary: Dict[str, Dict[str, float]]
    data: List[RegimeRow]


class ManifestModel(BaseModel):
    build_timestamp: str
    git_commit: Optional[str]
    config: Dict[str, Any]
    regime_rule: Dict[str, Any]
    units: Dict[str, str]
    disclaimers: List[str]
