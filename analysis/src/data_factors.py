from __future__ import annotations

from pathlib import Path
from typing import Dict

import pandas as pd
from pandas_datareader.famafrench import FamaFrenchReader


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={
        "Mkt-RF": "MKT_RF",
        "MKT-RF": "MKT_RF",
        "Mkt_RF": "MKT_RF",
        "RF": "RF",
    })


def _percent_to_decimal(df: pd.DataFrame) -> pd.DataFrame:
    return df / 100.0


def _as_datetime_index(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.index, pd.PeriodIndex):
        df.index = df.index.to_timestamp()
    else:
        df.index = pd.to_datetime(df.index)
    return df.sort_index()


def _to_weekly_compound(df: pd.DataFrame, freq: str = "W-FRI") -> pd.DataFrame:
    """
    Convert factor returns to weekly by compounding.
    Works for daily or monthly too (it just compounds within each weekly bucket).
    """
    return (1 + df).resample(freq).prod() - 1


def fetch_ff_factors_weekly(
    dataset_key: str,
    start: str,
    end: str | None,
    cache_dir: Path,
    out_filename: str,
    force: bool = False,
    freq: str = "W-FRI",
) -> Path:
    """
    Fetch Ken French factor dataset (any native freq), normalize columns, convert to decimals,
    resample to weekly by compounding, and cache as parquet with your chosen filename.
    """
    _ensure_dir(cache_dir)
    out_path = cache_dir / out_filename

    if out_path.exists() and (not force):
        return out_path

    rdr = FamaFrenchReader(dataset_key, start=start, end=end)
    data = rdr.read()
    df = data[0].copy()

    df = _as_datetime_index(df)
    df = _normalize_cols(df)

    needed = {"MKT_RF", "SMB", "HML", "RF"}
    missing = needed - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns {missing} in dataset {dataset_key}. Columns found: {list(df.columns)}")

    df = df[["MKT_RF", "SMB", "HML", "RF"]]
    df = _percent_to_decimal(df)

    # Always output weekly W-FRI
    df_weekly = _to_weekly_compound(df, freq=freq).dropna(how="all")

    df_weekly.to_parquet(out_path)
    return out_path


def fetch_all_factors(start: str, end: str | None, cache_dir: Path, force: bool = False) -> Dict[str, Path]:
    """
    US + Developed ex US FF3, standardized to weekly W-FRI, decimals.
    You can name the output files however you want.
    """
    us_path = fetch_ff_factors_weekly(
        dataset_key="F-F_Research_Data_Factors",
        start=start,
        end=end,
        cache_dir=cache_dir,
        out_filename="F-F_Research_Data_Factors_weekly.parquet",
        force=force,
        freq="W-FRI",
    )

    devx_path = fetch_ff_factors_weekly(
        dataset_key="Developed_ex_US_3_Factors",
        start=start,
        end=end,
        cache_dir=cache_dir,
        out_filename="Developed_ex_US_3_Factors.parquet",
        force=force,
        freq="W-FRI",
    )

    return {"ff3_us": us_path, "ff3_dev_ex_us": devx_path}
