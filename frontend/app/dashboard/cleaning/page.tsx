"use client";

import React, { useEffect, useState } from 'react';
import { useStore } from '@/lib/store';
import { runCleaning } from '@/lib/api';
import { CleanResponse } from '@/lib/types';
import { Wand2, Loader2, AlertTriangle, CheckCircle2, ArrowRight, Download, Sparkles } from 'lucide-react';

export default function CleaningPage() {
  const { sessionId, filename, setCurrentModule, cleaningResults, setCleaningResults } = useStore();
  const [data, setData] = useState<CleanResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { setCurrentModule('cleaning'); }, [setCurrentModule]);

  useEffect(() => {
    if (cleaningResults) {
      setData(cleaningResults);
      setLoading(false);
    }
  }, []);

  const handleClean = async () => {
    if (!sessionId) return;
    setLoading(true);
    setError(null);
    try {
      const result = await runCleaning(sessionId, true);
      setCleaningResults(result);
      setData(result);
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : 'Error running data cleaning.';
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-[70vh] space-y-6">
        <div className="relative">
          <div className="absolute inset-0 bg-[var(--accent-green)] rounded-full blur-[50px] opacity-20 animate-pulse" />
          <Loader2 className="w-16 h-16 animate-spin text-[var(--accent-green)] drop-shadow-[0_0_15px_rgba(0,255,136,0.8)] relative z-10" />
        </div>
        <div className="text-center space-y-2">
          <h2 className="text-2xl font-bold text-[var(--text-primary)]">Auto-Cleaning Data...</h2>
          <p className="text-[var(--text-muted)] font-mono text-sm max-w-sm">Detecting missing values, duplicates, and outliers. Applying intelligent transformations.</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-[70vh] space-y-4">
        <AlertTriangle className="w-16 h-16 text-red-500 drop-shadow-[0_0_15px_rgba(239,68,68,0.5)]" />
        <h2 className="text-2xl font-bold text-red-400">Cleaning Failed</h2>
        <p className="text-[var(--text-muted)] p-4 bg-red-500/10 border border-red-500/20 rounded-lg font-mono text-sm">{error}</p>
        <button onClick={() => { setError(null); setData(null); setCleaningResults(null); }} className="mt-6 px-6 py-2 border border-[var(--border-subtle)] hover:border-[var(--accent-cyan)] hover:text-[var(--accent-cyan)] transition-colors rounded-lg text-sm">Retry</button>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="space-y-8 animate-in fade-in duration-500">
        {/* Header */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Wand2 className="w-6 h-6 text-[var(--accent-green)]" />
            <h1 className="text-3xl font-bold tracking-tight text-[var(--text-primary)]">Data Cleaning</h1>
          </div>
          <p className="text-[var(--text-muted)]">
            Intelligent auto-cleaning for <span className="text-[var(--text-primary)] font-mono">{filename}</span>
          </p>
        </div>

        {/* CTA */}
        <div className="data-card p-10 text-center border-dashed border-2 border-[var(--border-subtle)] hover:border-[var(--accent-green)] transition-colors group cursor-pointer" onClick={handleClean}>
          <div className="relative inline-block mb-6">
            <div className="absolute inset-0 bg-[var(--accent-green)] rounded-full blur-[40px] opacity-0 group-hover:opacity-20 transition-opacity" />
            <Sparkles className="w-20 h-20 text-[var(--accent-green)] opacity-50 group-hover:opacity-100 transition-opacity relative z-10" />
          </div>
          <h2 className="text-2xl font-bold text-[var(--text-primary)] mb-2">Run Auto-Clean Pipeline</h2>
          <p className="text-[var(--text-muted)] text-sm max-w-md mx-auto mb-6">
            AI will analyze your data, detect issues, and apply transformations automatically. 
            Changes are logged and the original data is preserved.
          </p>
          <button className="px-8 py-3 bg-[var(--accent-green)]/10 border border-[var(--accent-green)]/30 text-[var(--accent-green)] rounded-lg font-semibold hover:bg-[var(--accent-green)]/20 transition-all text-sm">
            ⚡ Start Cleaning
          </button>
        </div>
      </div>
    );
  }

  // Results
  const removedMissing = data.before.missing_count - data.after.missing_count;

  return (
    <div className="space-y-8 animate-in fade-in duration-500 pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Wand2 className="w-6 h-6 text-[var(--accent-green)]" />
            <h1 className="text-3xl font-bold tracking-tight text-[var(--text-primary)]">Data Cleaning</h1>
          </div>
          <p className="text-[var(--text-muted)]">
            Cleaning results for <span className="text-[var(--text-primary)] font-mono">{filename}</span>
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {data.download_url && (
            <a
              href={`http://localhost:8000${data.download_url}`}
              className="flex items-center gap-2 px-5 py-2.5 bg-[var(--accent-green)]/10 border border-[var(--accent-green)]/30 text-[var(--accent-green)] rounded-lg text-sm font-semibold hover:bg-[var(--accent-green)]/20 transition-all"
            >
              <Download className="w-4 h-4" /> Download Cleaned CSV
            </a>
          )}
          <button
            onClick={() => { setCleaningResults(null); setData(null); handleClean(); }}
            className="px-4 py-2 border border-[var(--border-subtle)] text-[var(--text-muted)] rounded-lg hover:border-[var(--accent-cyan)] hover:text-[var(--accent-cyan)] transition-colors text-sm"
          >
            Re-run Analysis
          </button>
        </div>
      </div>

      {/* Before → After */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-center">
        <div className="data-card p-6 text-center">
          <p className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider mb-2">Before</p>
          <p className="text-3xl font-bold font-mono text-[var(--text-primary)]">{data.before.rows.toLocaleString()}</p>
          <p className="text-sm text-[var(--text-muted)] mt-1">rows</p>
          <p className="text-sm text-[var(--accent-orange)] font-mono mt-2">{data.before.missing_count.toLocaleString()} missing</p>
        </div>
        <div className="flex justify-center">
          <div className="flex items-center gap-2 text-[var(--accent-green)]">
            <ArrowRight className="w-8 h-8" />
          </div>
        </div>
        <div className="data-card p-6 text-center border-[var(--accent-green)]/30">
          <p className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider mb-2">After</p>
          <p className="text-3xl font-bold font-mono text-[var(--accent-green)]">{data.after.rows.toLocaleString()}</p>
          <p className="text-sm text-[var(--text-muted)] mt-1">rows</p>
          <p className="text-sm text-[var(--accent-green)] font-mono mt-2">{data.after.missing_count.toLocaleString()} missing</p>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="data-card p-5">
          <p className="text-xs text-[var(--text-muted)] uppercase tracking-wider mb-1">Changes Applied</p>
          <p className="text-2xl font-bold font-mono text-[var(--accent-cyan)]">{data.changes_log.length}</p>
        </div>
        <div className="data-card p-5">
          <p className="text-xs text-[var(--text-muted)] uppercase tracking-wider mb-1">Missing Fixed</p>
          <p className="text-2xl font-bold font-mono text-[var(--accent-green)]">{removedMissing.toLocaleString()}</p>
        </div>
        <div className="data-card p-5">
          <p className="text-xs text-[var(--text-muted)] uppercase tracking-wider mb-1">Rows Cleaned</p>
          <p className="text-2xl font-bold font-mono text-[var(--accent-purple)]">{data.after.rows.toLocaleString()}</p>
        </div>
        <div className="data-card p-5">
          <p className="text-xs text-[var(--text-muted)] uppercase tracking-wider mb-1">Data Quality</p>
          <p className="text-2xl font-bold font-mono text-[var(--accent-green)]">
            {data.after.rows > 0 ? Math.round((1 - data.after.missing_count / (data.after.rows * 10)) * 100) : 0}%
          </p>
        </div>
      </div>

      {/* Changes Log */}
      {data.changes_log.length > 0 && (
        <div className="data-card overflow-hidden">
          <div className="p-4 border-b border-[var(--border-subtle)] bg-[var(--bg-card)]/80 flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-[var(--accent-green)]" />
            <h2 className="text-lg font-bold text-[var(--text-primary)]">Transformation Log</h2>
          </div>
          <div className="divide-y divide-[var(--border-subtle)]">
            {data.changes_log.map((change, idx) => (
              <div key={idx} className="flex items-center gap-4 p-4 hover:bg-[var(--accent-cyan)]/5 transition-colors">
                <span className="text-[var(--accent-cyan)] font-mono font-bold text-sm shrink-0 w-8">
                  {String(idx + 1).padStart(2, '0')}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-[var(--text-primary)] font-medium truncate">{change.action}</p>
                  <p className="text-xs text-[var(--text-muted)] font-mono mt-0.5">{change.reason}</p>
                </div>
                <span className="text-xs text-[var(--accent-purple)] font-mono bg-[var(--accent-purple)]/10 px-2 py-1 rounded shrink-0 truncate max-w-[120px]" title={change.column}>
                  {change.column}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
