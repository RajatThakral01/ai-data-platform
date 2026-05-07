"use client";

import { useEffect, useState, useCallback } from "react";
import { useStore } from "@/lib/store";
import { generateBIDashboard, getCachedBIDashboard } from "@/lib/api";
import {
  BarChart3,
  Sparkles,
  Download,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Loader2,
  Database,
  Globe,
} from "lucide-react";

// ── Types ─────────────────────────────────────────────────────────────────────

interface DashboardResult {
  html_content: string;
  domain: string;
  row_count: number;
  columns_analyzed: number;
  source?: string;
  charts_count?: number;
  kpis_count?: number;
}

// ── Domain Badge Colors ───────────────────────────────────────────────────────

const DOMAIN_COLORS: Record<string, string> = {
  telecom:   "bg-cyan-500/20 text-cyan-400 border border-cyan-500/30",
  retail:    "bg-purple-500/20 text-purple-400 border border-purple-500/30",
  finance:   "bg-green-500/20 text-green-400 border border-green-500/30",
  hr:        "bg-orange-500/20 text-orange-400 border border-orange-500/30",
  marketing: "bg-pink-500/20 text-pink-400 border border-pink-500/30",
  general:   "bg-slate-500/20 text-slate-400 border border-slate-500/30",
};

// ── Main Component ────────────────────────────────────────────────────────────

export default function BIDashboardPage() {
  const { sessionId, filename, rowCount, columns, setCurrentModule } = useStore();

  const [result, setResult]         = useState<DashboardResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError]         = useState<string | null>(null);
  const [iframeKey, setIframeKey] = useState(0);
  const [currentStep, setCurrentStep] = useState(0);
  const [stepsComplete, setStepsComplete] = useState<boolean[]>([false, false, false, false]);
  const [generatedAt, setGeneratedAt]  = useState<string | null>(null);

  const GENERATION_STEPS = [
    { label: "Analyzing dataset",      detail: "Reading domain and business context"     },
    { label: "Building chart plan",    detail: "Selecting business-relevant charts"       },
    { label: "Writing dashboard code", detail: "Generating HTML, CSS and Chart.js"       },
    { label: "Finalizing dashboard",   detail: "Assembling and validating output"        },
  ];

  useEffect(() => {
    setCurrentModule("bi");
  }, [setCurrentModule]);

  // Try to load cached dashboard on mount
  useEffect(() => {
    if (!sessionId) return;
    getCachedBIDashboard(sessionId)
      .then((data) => setResult(data))
      .catch(() => {}); // silently ignore — no cache yet
  }, [sessionId]);

  const handleGenerate = useCallback(async () => {
    if (!sessionId) return;
    setIsLoading(true);
    setError(null);
    setCurrentStep(0);
    setStepsComplete([false, false, false, false]);

    const progressInterval = setInterval(() => {
      setCurrentStep(prev => {
        const next = prev + 1;
        setStepsComplete(steps => {
          const updated = [...steps];
          updated[prev] = true;
          return updated;
        });
        if (next >= GENERATION_STEPS.length - 1) {
          clearInterval(progressInterval);
        }
        return Math.min(next, GENERATION_STEPS.length - 1);
      });
    }, 8000);

    let data: DashboardResult;
    try {
      data = await generateBIDashboard(sessionId);
    } catch (err: any) {
      clearInterval(progressInterval);
      setError(
        err?.response?.data?.detail ||
        "Failed to generate dashboard. Please try again."
      );
      setIsLoading(false);
      return;
    } finally {
      clearInterval(progressInterval);
    }
    setStepsComplete([true, true, true, true]);
    setCurrentStep(GENERATION_STEPS.length - 1);
    setResult(data);
    setGeneratedAt(new Date().toLocaleTimeString());
    setIsLoading(false);
    setIframeKey(k => k + 1);
  }, [sessionId]);

  const handleDownload = useCallback(() => {
    if (!result) return;
    const blob = new Blob([result.html_content], { type: "text/html" });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href     = url;
    a.download = `bi-dashboard-${filename?.replace(/\.[^.]+$/, "") ?? "report"}.html`;
    a.click();
    URL.revokeObjectURL(url);
  }, [result, filename]);

  const domainClass = DOMAIN_COLORS[result?.domain ?? "general"] ?? DOMAIN_COLORS.general;

  // ── No Session ──────────────────────────────────────────────────────────────

  if (!sessionId) {
    return (
      <div className="flex flex-col items-center justify-center h-full min-h-[60vh] gap-4 text-center px-4">
        <div className="p-4 rounded-2xl bg-[var(--bg-card)] border border-[var(--border)]">
          <Database className="w-10 h-10 text-[var(--text-muted)]" />
        </div>
        <h2 className="text-xl font-semibold text-[var(--text-primary)]">No dataset loaded</h2>
        <p className="text-[var(--text-muted)] max-w-sm">
          Upload a CSV or Excel file first, then come back here to generate your BI dashboard.
        </p>
      </div>
    );
  }

  // ── Main UI ─────────────────────────────────────────────────────────────────

  return (
    <div className="flex flex-col gap-6 p-6 h-full">

      {/* ── Header ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-cyan-500/10 border border-cyan-500/20">
            <BarChart3 className="w-5 h-5 text-[var(--accent-cyan)]" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-[var(--text-primary)]">
              AI BI Dashboard
            </h1>
            <p className="text-sm text-[var(--text-muted)]">
              Auto-generated with NVIDIA NIM — Kimi K2.6 / GLM-5.1 / Llama 4
            </p>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2">
          {result && (
            <>
              <button
                onClick={handleDownload}
                className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium
                           bg-[var(--bg-card)] border border-[var(--border)]
                           text-[var(--text-primary)] hover:border-cyan-500/50
                           transition-all duration-200"
              >
                <Download className="w-4 h-4" />
                Download HTML
              </button>
              <button
                onClick={handleGenerate}
                disabled={isLoading}
                className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium
                           bg-[var(--bg-card)] border border-[var(--border)]
                           text-[var(--text-muted)] hover:text-[var(--text-primary)]
                           hover:border-[var(--border)] transition-all duration-200
                           disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
                Regenerate
              </button>
            </>
          )}

          {!result && (
            <button
              onClick={handleGenerate}
              disabled={isLoading}
              className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold
                         bg-[var(--accent-cyan)] text-[#080b14]
                         hover:brightness-110 active:scale-95
                         transition-all duration-200
                         disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Sparkles className="w-4 h-4" />
              )}
              {isLoading ? "Generating…" : "Generate Dashboard"}
            </button>
          )}
        </div>
      </div>

      {/* ── Dataset Info Strip ── */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2
                      px-4 py-3 rounded-xl
                      bg-[var(--bg-card)] border border-[var(--border)]">

        {/* Filename */}
        <div className="flex items-center gap-2 text-sm
                        text-[var(--text-muted)]">
          <Database className="w-3.5 h-3.5 shrink-0" />
          <span className="text-[var(--text-primary)] font-medium">
            {filename}
          </span>
        </div>

        <span className="text-[var(--border)] hidden sm:block">·</span>

        {/* Rows */}
        <span className="text-sm text-[var(--text-muted)]">
          <span className="text-[var(--text-primary)] font-medium">
            {rowCount.toLocaleString()}
          </span> rows
        </span>

        <span className="text-[var(--border)] hidden sm:block">·</span>

        {/* Columns */}
        <span className="text-sm text-[var(--text-muted)]">
          <span className="text-[var(--text-primary)] font-medium">
            {columns.length}
          </span> columns
        </span>

        {/* Domain badge */}
        {result && (
          <>
            <span className="text-[var(--border)] hidden sm:block">·</span>
            <span className={`flex items-center gap-1.5 text-xs
                              px-2.5 py-1 rounded-full font-medium
                              ${domainClass}`}>
              <Globe className="w-3 h-3" />
              {result.domain.charAt(0).toUpperCase() +
               result.domain.slice(1)}
            </span>
          </>
        )}

        {/* Source badge */}
        {result?.source && (
          <>
            <span className="text-[var(--border)] hidden sm:block">·</span>
            <span className={`text-xs px-2.5 py-1 rounded-full font-medium
              ${result.source === "insights"
                ? "bg-purple-500/20 text-purple-400 border border-purple-500/30"
                : result.source === "refined"
                  ? "bg-orange-500/20 text-orange-400 border border-orange-500/30"
                  : "bg-slate-500/20 text-slate-400 border border-slate-500/30"
              }`}>
              {result.source === "insights"
                ? "✦ From Insights"
                : result.source === "refined"
                  ? "✎ Refined"
                  : "⚡ Auto-planned"}
            </span>
          </>
        )}

        {/* Charts + KPIs count */}
        {result?.charts_count && (
          <>
            <span className="text-[var(--border)] hidden sm:block">·</span>
            <span className="text-xs text-[var(--text-muted)]">
              <span className="text-[var(--text-primary)] font-medium">
                {result.charts_count}
              </span> charts · <span className="text-[var(--text-primary)] font-medium">
                {result.kpis_count ?? 0}
              </span> KPIs
            </span>
          </>
        )}

        {/* Status + timestamp */}
        <div className="ml-auto flex items-center gap-3">
          {generatedAt && (
            <span className="text-xs text-[var(--text-muted)]">
              Generated {generatedAt}
            </span>
          )}
          {result && (
            <span className="flex items-center gap-1.5
                             text-xs text-green-400">
              <CheckCircle2 className="w-3.5 h-3.5" />
              Dashboard ready
            </span>
          )}
        </div>
      </div>

      {/* ── Error Banner ── */}
      {error && (
        <div className="flex items-start gap-3 px-4 py-3 rounded-xl
                        bg-red-500/10 border border-red-500/20 text-sm text-red-400">
          <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* ── Loading State ── */}
      {isLoading && (
        <div className="flex flex-col gap-6 py-12 px-6
                        bg-[var(--bg-card)] rounded-2xl
                        border border-[var(--border)]">

          {/* Header */}
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full border-2
                            border-[var(--border)]
                            border-t-[var(--accent-cyan)]
                            animate-spin shrink-0" />
            <div>
              <p className="text-[var(--text-primary)] font-semibold">
                Generating your BI dashboard...
              </p>
              <p className="text-xs text-[var(--text-muted)] mt-0.5">
                Using multi-step AI generation for best quality
              </p>
            </div>
          </div>

          {/* Steps */}
          <div className="flex flex-col gap-3 pl-2">
            {GENERATION_STEPS.map((step, index) => {
              const isDone   = stepsComplete[index];
              const isActive = currentStep === index && !isDone;
              const isPending = currentStep < index;
              return (
                <div key={index}
                     className="flex items-start gap-3">
                  {/* Step indicator */}
                  <div className={`
                    w-5 h-5 rounded-full shrink-0 mt-0.5
                    flex items-center justify-center text-xs
                    transition-all duration-500
                    ${isDone
                      ? "bg-[var(--accent-green)] text-[#080b14]"
                      : isActive
                        ? "border-2 border-[var(--accent-cyan)] animate-pulse"
                        : "border border-[var(--border)]"
                    }
                  `}>
                    {isDone && "✓"}
                  </div>
                  {/* Step text */}
                  <div className="flex-1">
                    <p className={`text-sm font-medium transition-colors duration-300
                      ${isDone
                        ? "text-[var(--accent-green)]"
                        : isActive
                          ? "text-[var(--text-primary)]"
                          : "text-[var(--text-muted)]"
                      }`}>
                      {step.label}
                    </p>
                    {isActive && (
                      <p className="text-xs text-[var(--text-muted)] mt-0.5">
                        {step.detail}
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Model badge */}
          <div className="flex items-center gap-2 pl-2">
            <div className="w-1.5 h-1.5 rounded-full
                            bg-[var(--accent-cyan)] animate-pulse" />
            <span className="text-xs text-[var(--text-muted)]">
              Powered by NVIDIA NIM — MiniMax M2.7 / Llama 4 Maverick
            </span>
          </div>
        </div>
      )}

      {/* ── Empty State (no result yet, not loading) ── */}
      {!isLoading && !result && !error && (
        <div className="flex flex-col items-center justify-center gap-6 py-20
                        bg-[var(--bg-card)] rounded-2xl border border-dashed border-[var(--border)]">
          <div className="p-5 rounded-2xl bg-cyan-500/5 border border-cyan-500/10">
            <Sparkles className="w-10 h-10 text-[var(--accent-cyan)]" />
          </div>
          <div className="text-center max-w-sm">
            <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-2">
              Ready to generate your BI dashboard
            </h3>
            <p className="text-sm text-[var(--text-muted)] leading-relaxed">
              Click <strong className="text-[var(--text-primary)]">Generate Dashboard</strong> and
              DeepSeek V4 Flash will create a fully custom HTML dashboard with real charts
              built specifically for <strong className="text-[var(--text-primary)]">{filename}</strong>.
            </p>
          </div>
          <div className="flex flex-wrap justify-center gap-2 text-xs text-[var(--text-muted)]">
            {["KPI Cards", "Bar Charts", "Pie Charts", "Distribution Charts", "Data Table", "Downloadable HTML"].map(
              (f) => (
                <span key={f} className="px-2.5 py-1 rounded-full bg-[var(--bg-card)] border border-[var(--border)]">
                  {f}
                </span>
              )
            )}
          </div>
          <button
            onClick={handleGenerate}
            className="flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold
                       bg-[var(--accent-cyan)] text-[#080b14]
                       hover:brightness-110 active:scale-95 transition-all duration-200"
          >
            <Sparkles className="w-4 h-4" />
            Generate Dashboard
          </button>
        </div>
      )}

      {/* ── Dashboard iframe ── */}
      {!isLoading && result && (
        <div className="flex-1 rounded-2xl overflow-hidden border border-[var(--border)]
                        shadow-[0_0_40px_rgba(0,229,255,0.05)]"
             style={{ minHeight: "700px" }}>
          <iframe
            key={iframeKey}
            srcDoc={result.html_content}
            sandbox="allow-scripts"
            className="w-full h-full"
            style={{ minHeight: "700px", border: "none", background: "#080b14" }}
            title="AI-Generated BI Dashboard"
          />
        </div>
      )}

      

    </div>
  );
}
