"use client";

import React from "react";
import { QualityReport } from "@/types/models";
import { statusColor, statusFromMissingPct } from "@/utils/dataQuality";

type Props = {
  report: QualityReport | null;
  lastRefresh?: string;
};

export default function DataQuality({ report, lastRefresh }: Props) {
  if (!report) {
    return (
      <div style={{ border: "1px solid #e5e5e5", borderRadius: 12, padding: 14 }}>
        <h2 style={{ fontSize: 18, margin: "0 0 8px 0" }}>Data quality</h2>
        <div>Loading…</div>
      </div>
    );
  }

  const tickers = Object.keys(report.missing_pct_weekly_returns || {});
  const sampleSize = report.aligned_sample_sizes?.equity_us ?? report.aligned_sample_sizes?.model_frame;

  return (
    <details open style={{ border: "1px solid #e5e5e5", borderRadius: 12, padding: 14 }}>
      <summary style={{ fontSize: 18, fontWeight: 600, cursor: "pointer", marginBottom: 8 }}>Data quality</summary>
      <div style={{ display: "flex", gap: 16, flexWrap: "wrap", marginBottom: 12 }}>
        <div>
          <div style={{ fontSize: 12, opacity: 0.7 }}>Last refresh</div>
          <div>{lastRefresh ?? "Unknown"}</div>
        </div>
        <div>
          <div style={{ fontSize: 12, opacity: 0.7 }}>Sample size</div>
          <div>{sampleSize ?? "n/a"} observations</div>
        </div>
        <div>
          <div style={{ fontSize: 12, opacity: 0.7 }}>Coverage range</div>
          <div>{tickers.length ? `${report.coverage[tickers[0]]?.start} → ${report.coverage[tickers[0]]?.end}` : "n/a"}</div>
        </div>
      </div>

      <div style={{ display: "grid", gap: 8 }}>
        {tickers.map((ticker) => {
          const pct = report.missing_pct_weekly_returns[ticker];
          const status = statusFromMissingPct(pct);
          return (
            <div key={ticker} style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div style={{ width: 8, height: 8, borderRadius: "50%", background: statusColor(status) }} />
              <div style={{ width: 60 }}>{ticker}</div>
              <div style={{ flex: 1, height: 8, background: "#f2f2f2", borderRadius: 6, overflow: "hidden" }}>
                <div style={{ width: `${Math.min(pct, 100)}%`, height: "100%", background: statusColor(status) }} />
              </div>
              <div style={{ width: 64, textAlign: "right" }}>{pct.toFixed(2)}%</div>
            </div>
          );
        })}
      </div>
    </details>
  );
}
