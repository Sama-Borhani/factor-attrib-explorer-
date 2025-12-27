# factor-attrib-explorer-
**Deployment URL:** _TBD (add Vercel URL after first deploy)_

Interactive factor attribution and regime diagnostics explorer for a global multi-asset portfolio. Explains what drives returns and risk across calm vs stress regimes using region-aware Fama-French equity factors and macro driver attribution. Static, reproducible, and interview-ready.

## Screenshots
Place 3–5 screenshots in `outputs/screenshots/` and update the links below after running the site locally:

- `outputs/screenshots/dashboard-rolling-betas.png`
- `outputs/screenshots/dashboard-attribution.png`
- `outputs/screenshots/dashboard-regime-comparison.png`

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

## Reproduction steps
### 1) Clone
```bash
git clone <repo-url>
cd factor-attrib-explorer-
```

### 2) Python environment
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r analysis/requirements.txt
```

### 3) Run pipeline (data + outputs)
```bash
python -m analysis.run_pipeline
```

### 4) Frontend setup
```bash
cd site
npm install
npm run dev
```
Open http://localhost:3000

### 5) Build the site
```bash
cd site
npm run build
```

### 6) Run tests
```bash
pytest analysis/tests
```

### 7) Deployment (Vercel)
1. Create a new Vercel project pointing at this repo.
2. Root directory: `site`
3. Build command: `npm run build`
4. Output directory: `.next`
5. Deploy on pushes to `main`.

## CI/CD
- PR validation: `.github/workflows/pr-validation.yml` runs lint + tests.
- Data refresh: `.github/workflows/data-refresh.yml` runs weekly and on demand.

## Configuration guide
- Core settings live in `analysis/src/config.py` (tickers, weights, dates, frequency, rolling windows, factor set, regime params).
- Exported JSON is written to `site/public/data/` by the pipeline.

## Known limitations
- Factor datasets are FF3 only; FF5 is a placeholder in the UI.
- Weekly aggregation only; daily mode is not implemented yet.
- Data refresh depends on upstream APIs (yfinance, Ken French).

## License
See `LICENSE`.
