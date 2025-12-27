import json
from pathlib import Path

p = Path("site/public/data/meta.json")
m = json.loads(p.read_text())

tickers = m.get("tickers", [])
if not tickers or not isinstance(tickers, list):
    raise SystemExit("meta.json: missing/invalid 'tickers' list")

# if weights is wrong (strings), overwrite with equal weights
w = m.get("weights")
if isinstance(w, list) and w and isinstance(w[0], str):
    m["weights"] = [1.0 / len(tickers)] * len(tickers)
    p.write_text(json.dumps(m, indent=2))
    print("Fixed: weights were strings -> wrote equal numeric weights")
else:
    print("No change: weights doesn't look like string tickers")
