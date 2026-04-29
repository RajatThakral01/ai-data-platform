"use client";

import React, { useEffect, useState } from 'react';
import { useStore } from '@/lib/store';
import { runEDA } from '@/lib/api';
import { EDAResponse } from '@/lib/types';
import { BarChart2, Loader2, AlertTriangle, TrendingUp, AlertCircle, Hash } from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
} from 'recharts';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-[#1a1a2e] border border-[#30363d] p-3 rounded-lg shadow-xl text-sm">
        <p className="text-[#8b949e] font-mono mb-1">{label}</p>
        <p className="text-[var(--text-primary)] font-bold">
          {payload[0].name}: <span className="text-[#00d4ff]">{typeof payload[0].value === 'number' ? payload[0].value.toLocaleString() : payload[0].value}</span>
        </p>
      </div>
    );
  }
  return null;
};

export default function EDAPage() {
  const { sessionId, filename, setCurrentModule, edaResults, setEdaResults } = useStore();
  const [data, setData] = useState<EDAResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { setCurrentModule('eda'); }, [setCurrentModule]);

  const fetchData = async () => {
    if (!sessionId) return;
    setLoading(true);
    setError(null);
    try {
      const result = await runEDA(sessionId);
      setEdaResults(result);
      setData(result);
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : 'Error running EDA.';
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (edaResults) {
      setData(edaResults);
      setLoading(false);
      return;
    }
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-[70vh] space-y-6">
        <div className="relative">
          <div className="absolute inset-0 bg-[var(--accent-cyan)] rounded-full blur-[50px] opacity-20 animate-pulse" />
          <Loader2 className="w-16 h-16 animate-spin text-[var(--accent-cyan)] drop-shadow-[0_0_15px_rgba(0,212,255,0.8)] relative z-10" />
        </div>
        <div className="text-center space-y-2">
          <h2 className="text-2xl font-bold text-[var(--text-primary)]">Analyzing Dataset...</h2>
          <p className="text-[var(--text-muted)] font-mono text-sm max-w-sm">Computing descriptive statistics, correlations, and generating AI narrative.</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-[70vh] space-y-4">
        <AlertTriangle className="w-16 h-16 text-red-500 drop-shadow-[0_0_15px_rgba(239,68,68,0.5)]" />
        <h2 className="text-2xl font-bold text-red-400">EDA Failed</h2>
        <p className="text-[var(--text-muted)] p-4 bg-red-500/10 border border-red-500/20 rounded-lg font-mono text-sm">{error}</p>
        <button onClick={() => { setError(null); setData(null); setEdaResults(null); fetchData(); }} className="mt-6 px-6 py-2 border border-[var(--border-subtle)] hover:border-[var(--accent-cyan)] hover:text-[var(--accent-cyan)] transition-colors rounded-lg text-sm">Retry</button>
      </div>
    );
  }

  if (!data) return null;

  const statsEntries = data.stats ? Object.entries(data.stats) : [];
  const missingEntries = data.missing ? Object.entries(data.missing).filter(([, v]) => v > 0).sort((a, b) => (b[1] as number) - (a[1] as number)) : [];
  const missingChartData = missingEntries.slice(0, 15).map(([col, val]) => ({ x: col, y: val }));

  // Build correlation heatmap data
  const corrEntries = data.correlations ? Object.entries(data.correlations) : [];
  const corrPairs: { x: string; y: string; v: number }[] = [];
  if (corrEntries.length > 0) {
    corrEntries.forEach(([col1, inner]) => {
      Object.entries(inner as Record<string, number>).forEach(([col2, val]) => {
        if (col1 !== col2) corrPairs.push({ x: col1, y: col2, v: Math.round(val * 100) / 100 });
      });
    });
  }
  // Get top 5 strongest correlations (absolute value, unique pairs)
  const seen = new Set<string>();
  const topCorrelations = corrPairs
    .sort((a, b) => Math.abs(b.v) - Math.abs(a.v))
    .filter(p => {
      const key = [p.x, p.y].sort().join('|');
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .slice(0, 8);

  return (
    <div className="space-y-8 animate-in fade-in duration-500 pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <BarChart2 className="w-6 h-6 text-[var(--accent-cyan)]" />
            <h1 className="text-3xl font-bold tracking-tight text-[var(--text-primary)]">Smart EDA</h1>
          </div>
          <p className="text-[var(--text-muted)]">
            Automated exploratory data analysis for <span className="text-[var(--text-primary)] font-mono">{filename}</span>
          </p>
        </div>
        <button
          onClick={() => { setEdaResults(null); setData(null); fetchData(); }}
          className="px-4 py-2 border border-[var(--border-subtle)] text-[var(--text-muted)] rounded-lg hover:border-[var(--accent-cyan)] hover:text-[var(--accent-cyan)] transition-colors text-sm"
        >
          Re-run Analysis
        </button>
      </div>

      {/* AI Narrative */}
      {data.narrative && (
        <div className="data-card p-6 border-l-4 border-l-[var(--accent-cyan)] relative overflow-hidden">
          <div className="absolute -right-10 -top-10 w-40 h-40 bg-[var(--accent-cyan)] rounded-full blur-[80px] opacity-10 pointer-events-none" />
          <div className="flex items-start gap-4">
            <div className="p-3 bg-[var(--accent-cyan)]/10 rounded-lg shrink-0">
              <TrendingUp className="w-6 h-6 text-[var(--accent-cyan)]" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-[var(--text-primary)] mb-2">AI Dataset Summary</h2>
              <p className="text-sm text-[var(--text-muted)] leading-relaxed whitespace-pre-wrap">{data.narrative}</p>
            </div>
          </div>
        </div>
      )}

      {/* Stats Table */}
      {statsEntries.length > 0 && (
        <div className="data-card overflow-hidden">
          <div className="p-4 border-b border-[var(--border-subtle)] bg-[var(--bg-card)]/80 flex items-center gap-2">
            <Hash className="w-5 h-5 text-[var(--accent-purple)]" />
            <h2 className="text-lg font-bold text-[var(--text-primary)]">Descriptive Statistics</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border-subtle)] bg-[var(--bg-card)]">
                  <th className="text-left p-3 text-[var(--text-muted)] font-mono text-xs uppercase tracking-wider">Column</th>
                  {statsEntries[0] && typeof statsEntries[0][1] === 'object' &&
                    Object.keys(statsEntries[0][1] as Record<string, unknown>).map(key => (
                      <th key={key} className="text-right p-3 text-[var(--text-muted)] font-mono text-xs uppercase tracking-wider">{key}</th>
                    ))
                  }
                </tr>
              </thead>
              <tbody>
                {statsEntries.map(([col, vals], idx) => (
                  <tr key={col} className={`border-b border-[var(--border-subtle)] ${idx % 2 === 0 ? 'bg-[var(--bg-primary)]/30' : ''} hover:bg-[var(--accent-cyan)]/5 transition-colors`}>
                    <td className="p-3 text-[var(--text-primary)] font-medium font-mono text-xs">{col}</td>
                    {typeof vals === 'object' && vals !== null &&
                      Object.values(vals as Record<string, unknown>).map((v, i) => (
                        <td key={i} className="text-right p-3 text-[var(--text-muted)] font-mono text-xs">
                          {typeof v === 'number' ? v.toLocaleString(undefined, { maximumFractionDigits: 2 }) : String(v ?? '-')}
                        </td>
                      ))
                    }
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Missing Values + Top Correlations row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Missing Values */}
        {missingChartData.length > 0 && (
          <div className="data-card flex flex-col overflow-hidden">
            <div className="p-4 border-b border-[var(--border-subtle)] bg-[var(--bg-card)]/80 flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-[var(--accent-orange)]" />
              <h3 className="font-bold text-[var(--text-primary)]">Missing Values</h3>
            </div>
            <div className="p-4 h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={missingChartData} layout="vertical" margin={{ left: 100, right: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#21262d" horizontal={false} />
                  <XAxis type="number" stroke="#8b949e" fontSize={11} />
                  <YAxis dataKey="x" type="category" stroke="#8b949e" fontSize={10} width={90} />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="y" name="Missing Count" fill="#ff6b35" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* Top Correlations */}
        {topCorrelations.length > 0 && (
          <div className="data-card flex flex-col overflow-hidden">
            <div className="p-4 border-b border-[var(--border-subtle)] bg-[var(--bg-card)]/80 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-[var(--accent-purple)]" />
              <h3 className="font-bold text-[var(--text-primary)]">Strongest Correlations</h3>
            </div>
            <div className="p-4 space-y-2">
              {topCorrelations.map((pair, idx) => {
                const absVal = Math.abs(pair.v);
                const barColor = pair.v >= 0 ? '#00ff88' : '#ff6b35';
                return (
                  <div key={idx} className="flex items-center gap-3 group">
                    <div className="text-xs text-[var(--text-muted)] font-mono w-32 truncate text-right" title={pair.x}>{pair.x}</div>
                    <div className="text-xs text-[var(--text-muted)]">↔</div>
                    <div className="text-xs text-[var(--text-muted)] font-mono w-32 truncate" title={pair.y}>{pair.y}</div>
                    <div className="flex-1 bg-[var(--bg-primary)] rounded-full h-3 relative overflow-hidden">
                      <div className="h-full rounded-full transition-all duration-500" style={{ width: `${absVal * 100}%`, backgroundColor: barColor, boxShadow: `0 0 8px ${barColor}40` }} />
                    </div>
                    <span className="text-xs font-mono font-bold w-12 text-right" style={{ color: barColor }}>{pair.v.toFixed(2)}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
