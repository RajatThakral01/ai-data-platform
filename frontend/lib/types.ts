export interface UploadResponse {
  session_id: string;
  filename: string;
  rows: number;
  columns: number;
  dtypes: Record<string, string>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  sample: Record<string, any>[];
  column_names: string[];
}

export interface EDAResponse {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  stats: Record<string, any>;
  missing: Record<string, number>;
  outliers?: Record<string, number>;
  correlations: Record<string, Record<string, number>>;
  narrative: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  charts?: any[];
}

export interface CleanBeforeAfter {
  rows: number;
  missing_count: number;
}

export interface CleanAction {
  column: string;
  action: string;
  reason: string;
}

export interface CleanResponse {
  changes_log: CleanAction[];
  before: CleanBeforeAfter;
  after: CleanBeforeAfter;
  download_url: string;
}

export interface MLModelResult {
  name: string;
  accuracy?: number;
  r2?: number;
  rmse?: number;
  precision?: number;
  recall?: number;
  f1?: number;
  training_time_ms?: number;
}

export interface MLResponse {
  task_type: "classification" | "regression" | "unknown";
  models: MLModelResult[];
  best_model: string;
  ai_summary: string;
  leakage_warnings: string[];
}

export interface BusinessContext {
  domain: string;
  business_entity: string;
  target_metric: string;
  business_questions: string[];
}

export interface KPI {
  label: string;
  value: number;
  formatted_value: string;
  delta?: string | null;
}

export interface ChartSpec {
  chart_type: string;
  x_col: string;
  y_col?: string;
  title: string;
  business_question: string;
  insight_hint: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data: any[];
}

export interface InsightsResponse {
  business_context: BusinessContext;
  kpis: KPI[];
  charts: ChartSpec[];
  ai_insights: string[];
  executive_summary?: string;
}

export interface QueryResponse {
  question: string;
  answer: string;
  code_used: string;
  context_chunks: string[];
  execution_time_ms: number;
  query_type?: string;
  summary?: string;
  follow_ups?: string[];
}

export interface LogEntry {
  timestamp: string;
  module: string;
  model: string;
  latency_dt: number;
  success: boolean;
  is_fallback: boolean;
  prompt_tokens: number;
  completion_tokens: number;
  total_cost_usd: number;
  module_name?: string;
  model_used?: string;
  latency_ms?: number;
  cost?: number;
  fallback_used?: boolean;
}

export interface StatsResponse {
  total_calls: number;
  total_tokens: number;
  total_cost: number;
  avg_latency_ms: number;
  calls_by_model: { model: string; count: number }[];
  calls_by_module: { module: string; count: number }[];
  fallback_rate: number;
  success_rate: number;
}
