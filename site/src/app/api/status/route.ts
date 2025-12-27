import { NextResponse } from "next/server";
import fs from "node:fs";
import path from "node:path";

import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

export async function GET() {
  const p = path.join(process.cwd(), "public", "data", "manifest.json");
  const raw = fs.readFileSync(p, "utf8");
  return NextResponse.json(JSON.parse(raw));
}

function load(p: string) {
  return JSON.parse(fs.readFileSync(p, "utf8"));
}

function alignByIntersection(exposures: any[], attribution: any[], regimes: any[]) {
  const Sexp = new Set(exposures.map((d) => d.date));
  const Satt = new Set(attribution.map((d) => d.date));
  const Sreg = new Set(regimes.map((d) => d.date));
  const common = [...Sexp].filter((d) => Satt.has(d) && Sreg.has(d)).sort();
  const C = new Set(common);

  return {
    exposures: exposures.filter((x) => C.has(x.date)),
    attribution: attribution.filter((x) => C.has(x.date)),
    regimes: regimes.filter((x) => C.has(x.date)),
    start: common[0] ?? null,
    end: common[common.length - 1] ?? null,
  };
}

export async function GET() {
  // Next runs from /site as app root in dev. Use process.cwd()
  const dataDir = path.join(process.cwd(), "public", "data");

  const eUs = load(path.join(dataDir, "exposures_equity_us.json"));
  const aUs = load(path.join(dataDir, "attribution_equity_us.json"));
  const r = load(path.join(dataDir, "regimes.json"));

  const aligned = alignByIntersection(eUs, aUs, r);

  return NextResponse.json({
    raw: { exp: eUs.length, att: aUs.length, reg: r.length },
    aligned: {
      exp: aligned.exposures.length,
      att: aligned.attribution.length,
      reg: aligned.regimes.length,
      start: aligned.start,
      end: aligned.end,
    },
  });
}

