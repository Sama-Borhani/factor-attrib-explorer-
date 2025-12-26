from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

import pandas as pd


def _load_parquet(p: Path) -> pd.DataFrame:
    df = pd.read_parquet(p)
    df.index = pd.to_datetime(df.index)
    return df.sort_index()


def _make_equal_weight_portfolio(returns: pd.DataFrame, tickers: Tuple[str, ...], weights: Dict[str, float]) -> pd.Series:
    w = pd.Series({t: weights[t] for t in tickers}, dtype=float)
    w = w / w.sum()
    r = returns[list(tickers)].copy()
    # Simple missing policy for v1: drop weeks where any holding missing
    r = r.dropna(how="any")
    port = (r * w).sum(axis=1)
    port.name = "PORT_RET"
    return port


def build_frames(
    returns_path: Path,
    ff3_us_path: Path,
    ff3_devx_path: Path,
    out_dir: Path,
    weights: Dict[str, float],
    equity_us: Tuple[str, ...],
    equity_intl: Tuple[str, ...],
    total_universe: Tuple[str, ...],
) -> Dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)

    rets = _load_parquet(returns_path)

    ff_us = _load_parquet(ff3_us_path)
    ff_dx = _load_parquet(ff3_devx_path)

    # Portfolio returns
    port_total = _make_equal_weight_portfolio(rets, total_universe, weights)
    port_us = _make_equal_weight_portfolio(rets, equity_us, weights)
    port_intl = _make_equal_weight_portfolio(rets, equity_intl, weights)

    # Align with factors by intersection of dates
    # Equity US frame: y = (port_us - RF_us), X = US factors (MKT_RF, SMB, HML)
    df_us = pd.concat([port_us, ff_us], axis=1, join="inner").dropna()
    df_us["Y"] = df_us["PORT_RET"] - df_us["RF"]
    frame_us = df_us[["Y", "MKT_RF", "SMB", "HML"]].copy()

    # Equity Intl frame: y = (port_intl - RF_devx), X = Dev ex US factors
    df_dx = pd.concat([port_intl, ff_dx], axis=1, join="inner").dropna()
    df_dx["Y"] = df_dx["PORT_RET"] - df_dx["RF"]
    frame_dx = df_dx[["Y", "MKT_RF", "SMB", "HML"]].copy()

    # Total macro driver frame: y = total portfolio return, X = macro proxies (ETF returns)
    # Macro proxies chosen from within universe; keep it transparent.
    proxies = ["SPY", "TLT", "DBC", "GLD", "VNQ"]
    missing = [p for p in proxies if p not in rets.columns]
    if missing:
        raise ValueError(f"Missing macro proxy returns for: {missing}")

    # Align y and X on same dates
    df_macro = pd.concat([port_total, rets[proxies]], axis=1, join="inner").dropna()
    df_macro = df_macro.rename(columns={"PORT_RET": "Y"})
    # regressors are proxy returns
    frame_macro = df_macro[["Y"] + proxies].copy()

    # Write frames
    p_us = out_dir / "frame_equity_us.parquet"
    p_dx = out_dir / "frame_equity_intl.parquet"
    p_macro = out_dir / "frame_total_macro.parquet"
    frame_us.to_parquet(p_us)
    frame_dx.to_parquet(p_dx)
    frame_macro.to_parquet(p_macro)

    return {"frame_equity_us": p_us, "frame_equity_intl": p_dx, "frame_total_macro": p_macro}
