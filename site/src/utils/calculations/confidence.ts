export type ConfidenceBand = {
  date: string;
  value: number;
  lower: number;
  upper: number;
};

export function computeConfidenceBands<T extends Record<string, any>>(
  rows: T[],
  valueKey: string,
  stderrKey: string,
  zScore = 1.96
): ConfidenceBand[] {
  return rows
    .map((row) => {
      const value = Number(row[valueKey]);
      const stderr = Number(row[stderrKey]);
      if (!Number.isFinite(value) || !Number.isFinite(stderr)) return null;
      return {
        date: String(row.date),
        value,
        lower: value - zScore * stderr,
        upper: value + zScore * stderr,
      };
    })
    .filter((row): row is ConfidenceBand => row !== null);
}
