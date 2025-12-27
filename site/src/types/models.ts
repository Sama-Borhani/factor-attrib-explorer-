export type Meta = {
  tickers: string[];
  weights: Record<string, number>;
  frequency: string;
  rolling_window_weeks: number;
  min_nobs: number;
  factor_set: string;
  regime: { vol_window_weeks: number; percentile: number; lookback_weeks: number };
};

export type ExposureRow = {
  date: string;
  alpha: number;
  r2: number;
  nobs: number;
  beta_MKT_RF: number;
  beta_SMB: number;
  beta_HML: number;
  stderr_alpha?: number;
  stderr_beta_MKT_RF?: number;
  stderr_beta_SMB?: number;
  stderr_beta_HML?: number;
  rolling_window_weeks?: number;
  min_nobs?: number;
};

export type AttribRow = { date: string; [k: string]: any };

export type RegimeRow = {
  date: string;
  regime: "calm" | "stress";
  vol: number;
  vol_thresh: number;
};

export type RegimesPayload = {
  metadata: {
    vol_window_weeks?: number;
    lookback_weeks?: number;
    percentile?: number;
  };
  stress_fraction?: number;
  summary?: Record<string, Record<string, number>>;
  data: RegimeRow[];
};

export type Manifest = {
  build_timestamp?: string;
};

export type QualityReport = {
  missing_pct_weekly_returns: Record<string, number>;
  coverage: Record<
    string,
    {
      start: string | null;
      end: string | null;
      rows_non_missing: number;
    }
  >;
  aligned_sample_sizes: Record<string, number>;
};
