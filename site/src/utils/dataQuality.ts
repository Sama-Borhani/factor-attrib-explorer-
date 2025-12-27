export type QualityStatus = "good" | "warn" | "bad";

export function statusFromMissingPct(pct: number): QualityStatus {
  if (pct < 5) return "good";
  if (pct <= 15) return "warn";
  return "bad";
}

export function statusColor(status: QualityStatus): string {
  if (status === "good") return "#2e7d32";
  if (status === "warn") return "#f9a825";
  return "#c62828";
}
