# factor-attrib-explorer-
Interactive factor attribution and regime diagnostics explorer for a global multi-asset portfolio. Explains what drives returns and risk across calm vs stress regimes using region-aware Fama-French equity factors and macro driver attribution. Static, reproducible, and interview-ready.

## Project spec
**Goal:** explain what drives portfolio returns and how exposures differ in calm vs stress markets.

**Universe**
- 10–15 liquid ETFs (currently 10), fixed weights (equal-weight OK).

**Frequency**
- Weekly (W-FRI). Daily optional later.

**Factor set**
- Fama-French 3 factors first (FF3), FF5 later.

**Rolling windows**
- 26w and 52w (start with one in pipeline).

**Regime rule**
- Realized volatility percentile: stress = top 25% (rolling vol window with trailing lookback).

**Deliverables**
- `/analysis/src/config.py` as single source of truth (tickers, weights, dates, freq, windows, factor set, regime params).
- `README.md` Project spec section (this page).

**Done gate (Milestone 0)**
- `python -m analysis.run_pipeline --dry-run` prints config and exits cleanly.
