from analysis.src.config import get_config

def main():
    cfg = get_config()
    print("CONFIG LOADED")
    print("Tickers:", cfg.tickers)
    print("Weights sum:", sum(cfg.weights.values()))
    print("Frequency:", cfg.freq)
    print("Rolling window:", cfg.rolling_window_weeks, "weeks | min_nobs:", cfg.min_nobs)
    print("Regime:", f"vol_window={cfg.vol_window_weeks}w, p={cfg.vol_percentile}, lookback={cfg.vol_lookback_weeks}w")
    print("Output paths:", cfg.out_data, cfg.out_json, cfg.out_reports)

if __name__ == "__main__":
    main()
