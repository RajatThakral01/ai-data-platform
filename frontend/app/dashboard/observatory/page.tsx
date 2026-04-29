"use client";

import React, { useEffect, useState } from 'react';
import { useStore } from '@/lib/store';
import { getObservatoryStats, getObservatoryLogs } from '@/lib/api';
import { StatsResponse, LogEntry } from '@/lib/types';
import { Activity, Loader2, AlertTriangle, Zap, DollarSign, Clock, CheckCircle2, RefreshCw } from 'lucide-react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell } from 'recharts';

const CHART_COLORS = ['#00d4ff', '#7b2fff', '#ff6b35', '#00ff88', '#d4b100'];

export default function ObservatoryPage() {
  const { setCurrentModule } = useStore();
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { setCurrentModule('observatory'); }, [setCurrentModule]);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [s, l] = await Promise.all([getObservatoryStats(), getObservatoryLogs(50)]);
      setStats(s);
      setLogs(l);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load observatory data.');
    } finally { setLoading(false); }
  };

  useEffect(() => { fetchData(); }, []);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-[70vh] space-y-6">
        <Loader2 className="w-16 h-16 animate-spin text-[var(--accent-orange)] drop-shadow-[0_0_15px_rgba(255,107,53,0.8)]" />
        <h2 className="text-2xl font-bold text-[var(--text-primary)]">Loading Observatory...</h2>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-[70vh] space-y-4">
        <AlertTriangle className="w-16 h-16 text-red-500" />
        <h2 className="text-2xl font-bold text-red-400">Observatory Error</h2>
        <p className="text-[var(--text-muted)] p-4 bg-red-500/10 border border-red-500/20 rounded-lg font-mono text-sm">{error}</p>
        <button onClick={fetchData} className="mt-6 px-6 py-2 border border-[var(--border-subtle)] hover:border-[var(--accent-cyan)] hover:text-[var(--accent-cyan)] transition-colors rounded-lg text-sm">Retry</button>
      </div>
    );
  }

  const moduleData = (Array.isArray(stats?.calls_by_module) 
    ? stats.calls_by_module 
    : []
  ).map((item, i) => ({ 
    name: item.module, 
    calls: item.count, 
    fill: CHART_COLORS[i % CHART_COLORS.length] 
  }));

  const modelData = (Array.isArray(stats?.calls_by_model) 
    ? stats.calls_by_model 
    : []
  ).map((item, i) => ({ 
    name: item.model, 
    calls: item.count, 
    fill: CHART_COLORS[i % CHART_COLORS.length] 
  }));

  return (
    <div className="space-y-8 animate-in fade-in duration-500 pb-12">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Activity className="w-6 h-6 text-[var(--accent-orange)]" />
            <h1 className="text-3xl font-bold tracking-tight text-[var(--text-primary)]">Admin Observatory</h1>
          </div>
          <p className="text-[var(--text-muted)]">LLM usage monitoring and cost tracking</p>
        </div>
        <button onClick={fetchData} className="p-2 border border-[var(--border-subtle)] rounded-lg hover:border-[var(--accent-cyan)] transition-colors">
          <RefreshCw className="w-5 h-5 text-[var(--text-muted)]" />
        </button>
      </div>

      {stats && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="data-card p-5">
              <div className="flex items-center gap-2 text-xs text-[var(--text-muted)] uppercase mb-2"><Zap className="w-3 h-3" /> Total Calls</div>
              <p className="text-2xl font-bold font-mono text-[var(--accent-cyan)]">{stats.total_calls}</p>
            </div>
            <div className="data-card p-5">
              <div className="flex items-center gap-2 text-xs text-[var(--text-muted)] uppercase mb-2"><CheckCircle2 className="w-3 h-3" /> Success Rate</div>
              <p className="text-2xl font-bold font-mono text-[var(--accent-green)]">{stats?.success_rate != null ? Number(stats.success_rate).toFixed(1) : '—'}%</p>
            </div>
            <div className="data-card p-5">
              <div className="flex items-center gap-2 text-xs text-[var(--text-muted)] uppercase mb-2"><Clock className="w-3 h-3" /> Avg Latency</div>
              <p className="text-2xl font-bold font-mono text-[var(--accent-purple)]">{stats?.avg_latency_ms != null ? Number(stats.avg_latency_ms).toFixed(0) : '—'}ms</p>
            </div>
            <div className="data-card p-5">
              <div className="flex items-center gap-2 text-xs text-[var(--text-muted)] uppercase mb-2"><Activity className="w-3 h-3" /> Fallback Rate</div>
              <p className="text-2xl font-bold font-mono text-[var(--accent-orange)]">{stats?.fallback_rate != null ? Number(stats.fallback_rate).toFixed(1) : '—'}%</p>
            </div>
            <div className="data-card p-5">
              <div className="flex items-center gap-2 text-xs text-[var(--text-muted)] uppercase mb-2"><DollarSign className="w-3 h-3" /> Total Cost</div>
              <p className="text-2xl font-bold font-mono text-[var(--text-primary)]">${stats?.total_cost != null ? Number(stats.total_cost).toFixed(4) : '—'}</p>
            </div>
          </div>

          {moduleData.length > 0 && (
            <div className="data-card flex flex-col overflow-hidden">
              <div className="p-4 border-b border-[var(--border-subtle)] bg-[var(--bg-card)]/80">
                <h3 className="font-bold text-[var(--text-primary)]">Calls by Module</h3>
              </div>
              <div className="p-4 h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={moduleData} margin={{ top: 10, right: 10, left: 10, bottom: 30 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#21262d" vertical={false} />
                    <XAxis dataKey="name" stroke="#8b949e" fontSize={10} angle={-30} textAnchor="end" tickMargin={10} />
                    <YAxis stroke="#8b949e" fontSize={11} />
                    <Tooltip contentStyle={{ background: '#1a1a2e', border: '1px solid #30363d', borderRadius: '8px', fontSize: '12px' }} />
                    <Bar dataKey="calls" name="API Calls" radius={[4, 4, 0, 0]}>
                      {moduleData.map((e, i) => <Cell key={i} fill={e.fill} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </>
      )}

      {(logs ?? []).length > 0 && (
        <div className="data-card overflow-hidden">
          <div className="p-4 border-b border-[var(--border-subtle)] bg-[var(--bg-card)]/80">
            <h2 className="text-lg font-bold text-[var(--text-primary)]">Recent Logs</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-[var(--border-subtle)] bg-[var(--bg-card)]">
                  <th className="text-left p-3 text-[var(--text-muted)] font-mono uppercase">Time</th>
                  <th className="text-left p-3 text-[var(--text-muted)] font-mono uppercase">Module</th>
                  <th className="text-left p-3 text-[var(--text-muted)] font-mono uppercase">Model</th>
                  <th className="text-right p-3 text-[var(--text-muted)] font-mono uppercase">Latency</th>
                  <th className="text-center p-3 text-[var(--text-muted)] font-mono uppercase">Status</th>
                  <th className="text-right p-3 text-[var(--text-muted)] font-mono uppercase">Cost</th>
                </tr>
              </thead>
              <tbody>
                {(logs ?? []).slice(0, 30).map((log, idx) => (
                  <tr key={idx} className={`border-b border-[var(--border-subtle)] ${idx % 2 === 0 ? 'bg-[var(--bg-primary)]/30' : ''} hover:bg-[var(--accent-cyan)]/5 transition-colors`}>
                    <td className="p-3 text-[var(--text-muted)] font-mono">{new Date(log.timestamp).toLocaleTimeString()}</td>
                    <td className="p-3 text-[var(--text-primary)]">{log.module_name}</td>
                    <td className="p-3 text-[var(--accent-purple)] font-mono">{log.model_used}</td>
                    <td className="text-right p-3 font-mono text-[var(--text-muted)]">{log?.latency_ms != null ? Number(log.latency_ms).toFixed(0) : '—'}ms</td>
                    <td className="text-center p-3">
                      {log.success ? <span className="text-[var(--accent-green)]">✓</span> : <span className="text-red-400">✗</span>}
                      {log.fallback_used && <span className="ml-1 text-[var(--accent-orange)]">⚡</span>}
                    </td>
                    <td className="text-right p-3 font-mono text-[var(--text-muted)]">—</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
