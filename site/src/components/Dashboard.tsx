"use client";

import React, { useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { loadJson } from "@/lib/loadJson";
import { alignByIntersection } from "@/lib/alignByDate";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

type Meta = {
  tickers: string[];
  weights: number[];
  frequency: string;
  rolling_window_weeks: number;
  min_nobs: number;
  regime: { vol_window_weeks: number; percentile: number; lookback_weeks: number };
};

type ExposureRow = {
  date: string;
  alpha: number;
  r2: number;
  nobs: number;
  beta_MKT_RF: number;
  beta_SMB: number;
  beta_HML: number;
};

type AttribRow = { date: string; [k: string]: any };

type RegimeRow = {
  date: string;
  regime: "calm" | "stress";
  vol: number;
  vol_thresh: number;
};

type Aligned = {
  exposures: ExposureRow[];
  attribution: AttribRow[];
  regimes: RegimeRow[];
};

export default function Dashboard() {
  const [meta, setMeta] = useState<Meta | null>(null);

  const [which, setWhich] = useState<"us" | "intl">("us");
  const [regimeFilter, setRegimeFilter] = useState<"all" | "calm" | "stress">("all");
  const [windowSel, setWindowSel] = useState<"3m" | "1y" | "2y" | "max">("1y");

  // Raw (un-aligned) data
  const [expUs, setExpUs] = useState<ExposureRow[]>([]);
  const [expIntl, setExpIntl] = useState<ExposureRow[]>([]);
  const [attUs, setAttUs] = useState<AttribRow[]>([]);
  const [attIntl, setAttIntl] = useState<AttribRow[]>([]);
  const [regAll, setRegAll] = useState<RegimeRow[]>([]);

  const [loadErr, setLoadErr] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;

    (async () => {
      setLoadErr(null);

      const m = await loadJson<Meta>("/data/meta.json");
      const [eUs, eIntl, aUs, aIntl, r] = await Promise.all([
        loadJson<ExposureRow[]>("/data/exposures_equity_us.json"),
        loadJson<ExposureRow[]>("/data/exposures_equity_intl.json"),
        loadJson<AttribRow[]>("/data/attribution_equity_us.json"),
        loadJson<AttribRow[]>("/data/attribution_equity_intl.json"),
        loadJson<RegimeRow[]>("/data/regimes.json"),
      ]);

      if (!alive) return;

      setMeta(m);
      setExpUs(eUs);
      setExpIntl(eIntl);
      setAttUs(aUs);
      setAttIntl(aIntl);
      setRegAll(r);

      console.log("[load] OK", {
        us: { exp: eUs.length, att: aUs.length },
        intl: { exp: eIntl.length, att: aIntl.length },
        regimes: r.length,
      });
    })().catch((err) => {
      console.error(err);
      if (!alive) return;
      setLoadErr(String(err));
    });

    return () => {
      alive = false;
    };
  }, []);

  const exposureRows = which === "us" ? expUs : expIntl;
  const attribRows = which === "us" ? attUs : attIntl;

  // ✅ Align exactly once, based on universe
  const aligned: Aligned = useMemo(() => {
    if (!exposureRows.length || !attribRows.length || !regAll.length) {
      return { exposures: [], attribution: [], regimes: [] };
    }
    return alignByIntersection(exposureRows, attribRows, regAll) as Aligned;
  }, [exposureRows, attribRows, regAll]);

  // Build regime map from aligned regimes (so it matches plotted dates)
  const regimeByDate = useMemo(() => {
    const map = new Map<string, "calm" | "stress">();
    for (const r of aligned.regimes) map.set(r.date, r.regime);
    return map;
  }, [aligned.regimes]);

  function applyWindow<T extends { date: string }>(rows: T[]): T[] {
    if (windowSel === "max") return rows;
    if (!rows.length) return rows;

    const last = new Date(rows[rows.length - 1].date);
    const cutoff = new Date(last);

    if (windowSel === "3m") cutoff.setMonth(cutoff.getMonth() - 3);
    if (windowSel === "1y") cutoff.setFullYear(cutoff.getFullYear() - 1);
    if (windowSel === "2y") cutoff.setFullYear(cutoff.getFullYear() - 2);

    return rows.filter((r) => new Date(r.date) >= cutoff);
  }

  function applyRegime<T extends { date: string }>(rows: T[]): T[] {
    if (regimeFilter === "all") return rows;
    return rows.filter((r) => regimeByDate.get(r.date) === regimeFilter);
  }

  const exposureFiltered = useMemo(
    () => applyRegime(applyWindow(aligned.exposures)),
    [aligned.exposures, windowSel, regimeFilter, regimeByDate]
  );

  const attribFiltered = useMemo(
    () => applyRegime(applyWindow(aligned.attribution)),
    [aligned.attribution, windowSel, regimeFilter, regimeByDate]
  );

  const xExp = useMemo(() => exposureFiltered.map((r) => r.date), [exposureFiltered]);
  const xAtt = useMemo(() => attribFiltered.map((r) => r.date), [attribFiltered]);

  const contribKeys = useMemo(() => {
    if (!attribFiltered.length) return [];
    return Object.keys(attribFiltered[0]).filter((k) => k.startsWith("contrib_"));
  }, [attribFiltered]);

  const stressPct = useMemo(() => {
    if (!aligned.regimes.length) return 0;
    const stress = aligned.regimes.filter((r) => r.regime === "stress").length;
    return Math.round((100 * stress) / aligned.regimes.length);
  }, [aligned.regimes]);

  const points = aligned.exposures.length; // should be 455 for US

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", padding: 24, fontFamily: "system-ui, -apple-system, Segoe UI, Roboto" }}>
      <h1 style={{ fontSize: 28, marginBottom: 6 }}>Factor Attribution & Regime Explorer</h1>
      <div style={{ opacity: 0.8, marginBottom: 16 }}>
        Loads static JSON from <code>/public/data</code>. No backend.
      </div>

      {loadErr ? (
        <div style={{ padding: 12, border: "1px solid #f5c2c7", background: "#f8d7da", borderRadius: 10, marginBottom: 14 }}>
          <b>Data load error:</b> {loadErr}
        </div>
      ) : null}

      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 18 }}>
        <label>
          Universe:&nbsp;
          <select value={which} onChange={(e) => setWhich(e.target.value as any)}>
            <option value="us">US Equity (FF3 US)</option>
            <option value="intl">International Equity (Dev ex US FF3)</option>
          </select>
        </label>

        <label>
          Window:&nbsp;
          <select value={windowSel} onChange={(e) => setWindowSel(e.target.value as any)}>
            <option value="3m">3M</option>
            <option value="1y">1Y</option>
            <option value="2y">2Y</option>
            <option value="max">Max</option>
          </select>
        </label>

        <label>
          Regime:&nbsp;
          <select value={regimeFilter} onChange={(e) => setRegimeFilter(e.target.value as any)}>
            <option value="all">All</option>
            <option value="calm">Calm</option>
            <option value="stress">Stress</option>
          </select>
        </label>

        <div style={{ opacity: 0.8 }}>
          Stress weeks (aligned): <b>{stressPct}%</b>
        </div>
        <div style={{ opacity: 0.7 }}>
          Points: <b>{points}</b>
        </div>
      </div>

      <div style={{ border: "1px solid #e5e5e5", borderRadius: 12, padding: 14, marginBottom: 16 }}>
        <h2 style={{ fontSize: 18, margin: "0 0 8px 0" }}>Rolling exposures (betas)</h2>
        <Plot
          data={[
            { x: xExp, y: exposureFiltered.map((r) => r.beta_MKT_RF), type: "scatter", mode: "lines", name: "MKT" },
            { x: xExp, y: exposureFiltered.map((r) => r.beta_SMB), type: "scatter", mode: "lines", name: "SMB" },
            { x: xExp, y: exposureFiltered.map((r) => r.beta_HML), type: "scatter", mode: "lines", name: "HML" },
          ]}
          layout={{
            autosize: true,
            height: 380,
            margin: { l: 50, r: 20, t: 10, b: 40 },
            xaxis: { title: "Date" },
            yaxis: { title: "Beta" },
            legend: { orientation: "h" },
          }}
          style={{ width: "100%" }}
          config={{ displayModeBar: false }}
        />
      </div>

      <div style={{ border: "1px solid #e5e5e5", borderRadius: 12, padding: 14, marginBottom: 16 }}>
        <h2 style={{ fontSize: 18, margin: "0 0 8px 0" }}>Return attribution (factor contributions)</h2>
        <Plot
          data={[
            ...contribKeys.map((k) => ({
              x: xAtt,
              y: attribFiltered.map((r) => (r[k] ?? 0) as number),
              type: "scatter",
              mode: "lines",
              stackgroup: "one",
              name: k.replace("contrib_", ""),
            })),
          ]}
          layout={{
            autosize: true,
            height: 380,
            margin: { l: 50, r: 20, t: 10, b: 40 },
            xaxis: { title: "Date" },
            yaxis: { title: "Contribution" },
            legend: { orientation: "h" },
          }}
          style={{ width: "100%" }}
          config={{ displayModeBar: false }}
        />
      </div>

      <div style={{ border: "1px solid #e5e5e5", borderRadius: 12, padding: 14 }}>
        <h2 style={{ fontSize: 18, margin: "0 0 8px 0" }}>Method snapshot</h2>
        {meta ? (
          <ul style={{ margin: 0, paddingLeft: 18, opacity: 0.9 }}>
            <li>Frequency: {meta.frequency}</li>
            <li>Rolling window: {meta.rolling_window_weeks} weeks (min obs {meta.min_nobs})</li>
            <li>
              Regime rule: vol {meta.regime.vol_window_weeks}w, percentile {meta.regime.percentile}, lookback {meta.regime.lookback_weeks}w
            </li>
          </ul>
        ) : (
          <div>Loading…</div>
        )}
        <div style={{ marginTop: 10, opacity: 0.75, fontSize: 13 }}>
          Limitations: factor datasets are US / Developed ex-US only; weekly aggregation; no forecasting.
        </div>
      </div>
    </div>
  );
}
