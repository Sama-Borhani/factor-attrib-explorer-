import argparse

from analysis.src.export_json import export_json_bundle
from analysis.src.config import get_config
from analysis.src.data_prices import fetch_prices_weekly
from analysis.src.data_factors import fetch_all_factors
from analysis.src.build_frames import build_frames
from analysis.src.rolling_model import run_rolling_from_parquet
from analysis.src.attribution import attribution_from_parquets
from analysis.src.regimes import regimes_and_summary
from analysis.src.portfolio import write_portfolio_summary

def _print_config(cfg) -> None:
    print("CONFIG LOADED")
    print("Tickers:", cfg.tickers)
    print("Weights sum:", sum(cfg.weights.values()))
    print("Frequency:", cfg.freq)
    print("Rolling window:", cfg.rolling_window_weeks, "weeks | min_nobs:", cfg.min_nobs)
    print("Regime:", f"vol_window={cfg.vol_window_weeks}w, p={cfg.vol_percentile}, lookback={cfg.vol_lookback_weeks}w")
    print("Output paths:", cfg.out_data, cfg.out_json, cfg.out_reports)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run factor attribution pipeline.")
    parser.add_argument("--dry-run", action="store_true", help="Print config and exit.")
    args = parser.parse_args()

    cfg = get_config()
    _print_config(cfg)

    if args.dry_run:
        return

    # 1) Prices
    print("\n[1/6] Fetching prices -> weekly returns (cached)")
    price_out = fetch_prices_weekly(
        tickers=cfg.tickers,
        start=cfg.start,
        end=cfg.end,
        freq=cfg.freq,
        cache_dir=cfg.out_data,
        force=False,
    )
    print("Saved:", price_out)

    # 2) Factors
    print("\n[2/6] Fetching Fama-French factors (cached)")
    factors_dir = cfg.out_data / "factors"
    factors = fetch_all_factors(start=cfg.start, end=cfg.end, cache_dir=factors_dir, force=False)
    print("Saved:", factors)

    # 3) Frames
    print("\n[3/6] Building model frames")
    frames_dir = cfg.out_data / "frames"
    frames = build_frames(
        returns_path=price_out["weekly_returns"],
        ff3_us_path=factors["ff3_us"],
        ff3_devx_path=factors["ff3_dev_ex_us"],
        out_dir=frames_dir,
        weights=cfg.weights,
        equity_us=cfg.equity_us,
        equity_intl=cfg.equity_intl,
        total_universe=cfg.tickers,
    )
    print("Saved frames:", frames)

    # 3b) Portfolio summary
    print("\n[3b/6] Portfolio summary")
    summary_path = write_portfolio_summary(
        returns_path=price_out["weekly_returns"],
        out_path=cfg.out_reports / "portfolio_summary.json",
        weights=cfg.weights,
        freq=cfg.freq,
        missing_price_policy="drop_any",
        compounding="geometric",
    )
    print("Saved portfolio summary:", summary_path)

    # 4) Rolling exposures
    print("\n[4/6] Running rolling regressions -> exposures (cached)")
    exposures_dir = cfg.out_data / "exposures"

    exp_us = run_rolling_from_parquet(
        frame_path=frames["frame_equity_us"],
        out_path=exposures_dir / "exposures_equity_us.parquet",
        window=cfg.rolling_window_weeks,
        min_nobs=cfg.min_nobs,
        y_col="Y",
    )

    exp_intl = run_rolling_from_parquet(
        frame_path=frames["frame_equity_intl"],
        out_path=exposures_dir / "exposures_equity_intl.parquet",
        window=cfg.rolling_window_weeks,
        min_nobs=cfg.min_nobs,
        y_col="Y",
    )

    exp_macro = run_rolling_from_parquet(
        frame_path=frames["frame_total_macro"],
        out_path=exposures_dir / "exposures_total_macro.parquet",
        window=cfg.rolling_window_weeks,
        min_nobs=cfg.min_nobs,
        y_col="Y",
    )

    print("Saved exposures:", exp_us, exp_intl, exp_macro)

    # 5) Attribution
    print("\n[5/6] Attribution (lagged exposures, no look-ahead)")
    attrib_dir = cfg.out_data / "attribution"

    a_us = attribution_from_parquets(
        frame_path=frames["frame_equity_us"],
        exposures_path=cfg.out_data / "exposures" / "exposures_equity_us.parquet",
        out_path=attrib_dir / "attrib_equity_us.parquet",
        y_col="Y",
    )

    a_intl = attribution_from_parquets(
        frame_path=frames["frame_equity_intl"],
        exposures_path=cfg.out_data / "exposures" / "exposures_equity_intl.parquet",
        out_path=attrib_dir / "attrib_equity_intl.parquet",
        y_col="Y",
    )

    a_macro = attribution_from_parquets(
        frame_path=frames["frame_total_macro"],
        exposures_path=cfg.out_data / "exposures" / "exposures_total_macro.parquet",
        out_path=attrib_dir / "attrib_total_macro.parquet",
        y_col="Y",
    )

    print("Saved attribution:", a_us, a_intl, a_macro)

    # 6) Regimes
    print("\n[6/6] Regime labeling + summary")
    out_regimes = cfg.out_data / "regimes" / "regimes.parquet"
    out_summary = cfg.out_reports / "regime_summary.json"
    r_path, s_path = regimes_and_summary(
        returns_path=cfg.out_data / "returns_weekly.parquet",
        exposures_path=cfg.out_data / "exposures" / "exposures_equity_us.parquet",
        out_regimes_path=out_regimes,
        out_summary_path=out_summary,
        vol_window_weeks=cfg.vol_window_weeks,
        lookback_weeks=cfg.vol_lookback_weeks,
        percentile=cfg.vol_percentile,
        weights=cfg.weights,
    )
    print("Saved regimes + summary:", r_path, s_path)
    print("\nMilestone 3 complete if all files exist and no errors occurred.")
    # 7) Export JSON for site (Milestone 4)
    print("\n[7/7] Exporting JSON bundle for site")
    meta = {
        "tickers": list(cfg.tickers),
        "weights": list(cfg.weights),
        "frequency": cfg.freq,
        "rolling_window_weeks": cfg.rolling_window_weeks,
        "min_nobs": cfg.min_nobs,
        "regime": {
            "vol_window_weeks": cfg.vol_window_weeks,
            "percentile": cfg.vol_percentile,
            "lookback_weeks": cfg.vol_lookback_weeks,
        },
    }

    paths = export_json_bundle(
        out_json_dir=cfg.out_json,
        meta=meta,
        exposures_us_path=cfg.out_data / "exposures" / "exposures_equity_us.parquet",
        exposures_intl_path=cfg.out_data / "exposures" / "exposures_equity_intl.parquet",
        attrib_us_path=cfg.out_data / "attribution" / "attrib_equity_us.parquet",
        attrib_intl_path=cfg.out_data / "attribution" / "attrib_equity_intl.parquet",
        regimes_path=cfg.out_data / "regimes" / "regimes.parquet",
        regime_summary_path=cfg.out_reports / "regime_summary.json",
    )
    print("Saved JSON:", paths)

if __name__ == "__main__":
    main()
