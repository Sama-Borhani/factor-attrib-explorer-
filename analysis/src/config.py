from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Config:
    # Universe (10 ETFs)
    tickers: tuple = ("SPY","QQQ","IWM","VTV","VUG","EFA","TLT","GLD","VNQ","DBC")
    weights: dict = None  # filled in __post_init__ style below

    # Sleeves
    equity_us: tuple = ("SPY","QQQ","IWM","VTV","VUG")
    equity_intl: tuple = ("EFA",)
    equity_all: tuple = ("SPY","QQQ","IWM","VTV","VUG","EFA")

    # Time + frequency
    start: str = "2015-01-01"
    end: str | None = None
    freq: str = "W-FRI"  # weekly Friday

    # Rolling regression
    rolling_window_weeks: int = 52
    rolling_windows_weeks: tuple[int, ...] = (26, 52)
    min_nobs: int = 45

    # Regimes (portfolio realized vol)
    vol_window_weeks: int = 8
    vol_percentile: float = 0.75
    vol_lookback_weeks: int = 104  # trailing 2 years

    # Paths
    root: Path = Path(__file__).resolve().parents[2]
    out_data: Path = root / "analysis" / "outputs" / "data"
    out_json: Path = root / "analysis" / "outputs" / "json"
    out_reports: Path = root / "analysis" / "outputs" / "reports"

def get_config() -> Config:
    cfg = Config(weights={t: 0.10 for t in Config().tickers})
    return cfg
