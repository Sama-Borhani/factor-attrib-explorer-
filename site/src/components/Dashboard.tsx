"use client";

import React, { useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { loadJson } from "@/lib/loadJson";
import { alignByIntersection } from "@/lib/alignByDate";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

type Meta = {
  tickers: string[];
  weights: Record<string, number>;
  frequency: string;
  rolling_window_weeks: number;
  min_nobs: number;
  factor_set: string;
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

type RegimesPayload = {
  metadata: {
    vol_window_weeks?: number;
    lookback_weeks?: number;
    percentile?: number;
  };
  stress_fraction?: number;
  summary?: Record<string, Record<string, number>>;
  data: RegimeRow[];
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
  const [modelSel, setModelSel] = useState<"ff3" | "ff5">("ff3");
  const [dateStart, setDateStart] = useState<string>("");
  const [dateEnd, setDateEnd] = useState<string>("");
  const [regSummary, setRegSummary] = useState<Record<string, Record<string, number>> | null>(null);

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
      const [eUs, eIntl, aUs, aIntl, rPayload] = await Promise.all([
        loadJson<ExposureRow[]>("/data/exposures_equity_us.json"),
        loadJson<ExposureRow[]>("/data/exposures_equity_intl.json"),
        loadJson<AttribRow[]>("/data/attribution_equity_us.json"),
        loadJson<AttribRow[]>("/data/attribution_equity_intl.json"),
        loadJson<RegimesPayload>("/data/regimes.json"),
      ]);

      if (!alive) return;

      setMeta(m);
      setExpUs(eUs);
      setExpIntl(eIntl);
      setAttUs(aUs);
      setAttIntl(aIntl);
      setRegAll(rPayload.data ?? []);
      setRegSummary(rPayload.summary ?? null);
    })().catch((err) => {
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

  const exposureWindowed = useMemo(
    () => applyDateRange(applyRegime(applyWindow(aligned.exposures))),
    [aligned.exposures, windowSel, regimeFilter, dateStart, dateEnd, regimeByDate]
  );

  const attribWindowed = useMemo(
    () => applyDateRange(applyRegime(applyWindow(aligned.attribution))),
    [aligned.attribution, windowSel, regimeFilter, dateStart, dateEnd, regimeByDate]
  );

  const exposureFiltered = exposureWindowed;
  const attribFiltered = attribWindowed;

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

  const dateBounds = useMemo(() => {
    if (!aligned.exposures.length) return { min: "", max: "" };
    return {
      min: aligned.exposures[0].date,
      max: aligned.exposures[aligned.exposures.length - 1].date,
    };
  }, [aligned.exposures]);

  function applyDateRange<T extends { date: string }>(rows: T[]): T[] {
    if (!dateStart && !dateEnd) return rows;
    return rows.filter((r) => {
      if (dateStart && r.date < dateStart) return false;
      if (dateEnd && r.date > dateEnd) return false;
      return true;
    });
  }

  const xExp = useMemo(() => exposureWindowed.map((r) => r.date), [exposureWindowed]);
  const xAtt = useMemo(() => attribWindowed.map((r) => r.date), [attribWindowed]);

  const stressSummary = regSummary?.stress ?? null;
  const calmSummary = regSummary?.calm ?? null;

  const keyInsights = useMemo(() => {
    const insights: string[] = [];
    if (!stressSummary || !calmSummary) return insights;
    const stressVol = stressSummary.mean_vol;
    const calmVol = calmSummary.mean_vol;
    if (stressVol && calmVol) {
      const diff = stressVol - calmVol;
      insights.push(
        diff > 0
          ? `Volatility is higher in stress regimes by ${(diff * 100).toFixed(2)}pp.`
          : `Volatility is lower in stress regimes by ${(Math.abs(diff) * 100).toFixed(2)}pp.`
      );
    }
    const stressExplained = stressSummary.mean_explained_share;
    const calmExplained = calmSummary.mean_explained_share;
    if (stressExplained && calmExplained) {
      const diff = stressExplained - calmExplained;
      insights.push(
        diff > 0
          ? `Explained share increases in stress by ${(diff * 100).toFixed(2)}pp.`
          : `Explained share decreases in stress by ${(Math.abs(diff) * 100).toFixed(2)}pp.`
      );
    }
    return insights;
  }, [stressSummary, calmSummary]);

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
          Model:&nbsp;
          <select value={modelSel} onChange={(e) => setModelSel(e.target.value as any)}>
            <option value="ff3">FF3</option>
            <option value="ff5" disabled>
              FF5 (coming soon)
            </option>
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

        <label>
          Start:&nbsp;
          <input
            type="date"
            value={dateStart}
            min={dateBounds.min}
            max={dateBounds.max}
            onChange={(e) => setDateStart(e.target.value)}
          />
        </label>

        <label>
          End:&nbsp;
          <input
            type="date"
            value={dateEnd}
            min={dateBounds.min}
            max={dateBounds.max}
            onChange={(e) => setDateEnd(e.target.value)}
          />
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

      <div style={{ border: "1px solid #e5e5e5", borderRadius: 12, padding: 14, marginBottom: 16 }}>
        <h2 style={{ fontSize: 18, margin: "0 0 8px 0" }}>Calm vs stress comparison</h2>
        {regSummary ? (
          <Plot
            data={[
              {
                x: ["Calm", "Stress"],
                y: [calmSummary?.mean_vol ?? 0, stressSummary?.mean_vol ?? 0],
                type: "bar",
                name: "Mean vol",
              },
              {
                x: ["Calm", "Stress"],
                y: [calmSummary?.mean_explained_share ?? 0, stressSummary?.mean_explained_share ?? 0],
                type: "bar",
                name: "Mean explained share",
              },
            ]}
            layout={{
              autosize: true,
              barmode: "group",
              height: 320,
              margin: { l: 50, r: 20, t: 10, b: 40 },
              yaxis: { title: "Value" },
              legend: { orientation: "h" },
            }}
            style={{ width: "100%" }}
            config={{ displayModeBar: false }}
          />
        ) : (
          <div>Loading…</div>
        )}
      </div>

      <div style={{ border: "1px solid #e5e5e5", borderRadius: 12, padding: 14, marginBottom: 16 }}>
        <h2 style={{ fontSize: 18, margin: "0 0 8px 0" }}>Key insights</h2>
        {keyInsights.length ? (
          <ul style={{ margin: 0, paddingLeft: 18, opacity: 0.9 }}>
            {keyInsights.map((insight) => (
              <li key={insight}>{insight}</li>
            ))}
          </ul>
        ) : (
          <div>Waiting for regime summary data…</div>
        )}
      </div>

      <div style={{ border: "1px solid #e5e5e5", borderRadius: 12, padding: 14 }}>
        <h2 style={{ fontSize: 18, margin: "0 0 8px 0" }}>Method snapshot</h2>
        {meta ? (
          <ul style={{ margin: 0, paddingLeft: 18, opacity: 0.9 }}>
            <li>Frequency: {meta.frequency}</li>
            <li>Model: {modelSel.toUpperCase()}</li>
            <li>Rolling window: {meta.rolling_window_weeks} weeks (min obs {meta.min_nobs})</li>
            <li>
              Regime rule: vol {meta.regime.vol_window_weeks}w, percentile {meta.regime.percentile}, lookback {meta.regime.lookback_weeks}w
            </li>
          </ul>
        ) : (
          <div>Loading…</div>
        )}
        <div style={{ marginTop: 10, opacity: 0.75, fontSize: 13 }}>
          <div style={{ fontWeight: 600, marginBottom: 4 }}>Limitations</div>
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            <li>Factors are limited to US / Developed ex-US datasets.</li>
            <li>Weekly aggregation; no daily modeling yet.</li>
            <li>No forecasting or trading signals.</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
