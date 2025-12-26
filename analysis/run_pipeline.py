from analysis.src.config import get_config
from analysis.src.data_prices import fetch_prices_weekly
from analysis.src.data_factors import fetch_all_factors
from analysis.src.build_frames import build_frames
from analysis.src.rolling_model import run_rolling_from_parquet

def main():
    cfg = get_config()
    print("CONFIG LOADED")
    print("Tickers:", cfg.tickers)
    print("Weights sum:", sum(cfg.weights.values()))
    print("Frequency:", cfg.freq)
    print("Rolling window:", cfg.rolling_window_weeks, "weeks | min_nobs:", cfg.min_nobs)
    print("Regime:", f"vol_window={cfg.vol_window_weeks}w, p={cfg.vol_percentile}, lookback={cfg.vol_lookback_weeks}w")
    print("Output paths:", cfg.out_data, cfg.out_json, cfg.out_reports)

    # 1) Prices
    print("\n[1/4] Fetching prices -> weekly returns (cached)")
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
    print("\n[2/4] Fetching Fama-French factors (cached)")
    factors_dir = cfg.out_data / "factors"
    factors = fetch_all_factors(start=cfg.start, end=cfg.end, cache_dir=factors_dir, force=False)
    print("Saved:", factors)

    # 3) Frames
    print("\n[3/4] Building model frames")
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

    # 4) Rolling exposures (Milestone 2)
    print("\n[4/4] Running rolling regressions -> exposures (cached)")
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
    print("\nMilestone 2 complete if all files exist and no errors occurred.")

if __name__ == "__main__":
    main()
