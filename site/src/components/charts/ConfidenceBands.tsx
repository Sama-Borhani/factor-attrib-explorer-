"use client";

import React from "react";
import dynamic from "next/dynamic";
import { ConfidenceBand } from "@/utils/calculations/confidence";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

type BandSeries = {
  name: string;
  bands: ConfidenceBand[];
};

type Props = {
  title: string;
  series: BandSeries[];
  showBands: boolean;
};

export default function ConfidenceBands({ title, series, showBands }: Props) {
  const traces = series.flatMap((s) => {
    const x = s.bands.map((b) => b.date);
    const y = s.bands.map((b) => b.value);
    const lower = s.bands.map((b) => b.lower);
    const upper = s.bands.map((b) => b.upper);

    const lineTrace = { x, y, type: "scatter", mode: "lines", name: s.name };

    if (!showBands) return [lineTrace];

    return [
      { x, y: lower, type: "scatter", mode: "lines", line: { width: 0 }, showlegend: false },
      {
        x,
        y: upper,
        type: "scatter",
        mode: "lines",
        fill: "tonexty",
        fillcolor: "rgba(100, 149, 237, 0.15)",
        line: { width: 0 },
        name: `${s.name} 95% CI`,
      },
      lineTrace,
    ];
  });

  return (
    <Plot
      data={traces}
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
  );
}
