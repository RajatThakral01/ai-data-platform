"use client";

import React, { useEffect, useState } from 'react';
import { useStore } from '@/lib/store';
import { runML } from '@/lib/api';
import { MLResponse } from '@/lib/types';
import { BrainCircuit, Loader2, AlertTriangle, Trophy, Zap, ShieldAlert } from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis
} from 'recharts';

const CHART_COLORS = ['#00d4ff', '#7b2fff', '#ff6b35', '#00ff88', '#d4b100'];

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-[#1a1a2e] border border-[#30363d] p-3 rounded-lg shadow-xl text-sm">
        <p className="text-[#8b949e] font-mono mb-1">{label}</p>
        <p className="text-[var(--text-primary)] font-bold">
          {payload[0].name}: <span className="text-[#00d4ff]">{typeof payload[0].value === 'number' ? payload[0].value.toFixed(4) : payload[0].value}</span>
        </p>
      </div>
    );
  }
  return null;
};

export default function MLPage() {
  const { sessionId, filename, columns, setCurrentModule, mlResults, setMlResults } = useStore();
  const [data, setData] = useState<MLResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [targetColumn, setTargetColumn] = useState('');

  useEffect(() => { setCurrentModule('ml'); }, [setCurrentModule]);

  useEffect(() => {
    if (mlResults) {
      setData(mlResults as MLResponse);
      setLoading(false);
    }
  }, []);

  const handleRun = async () => {
    if (!sessionId || !targetColumn) return;
    setLoading(true);
    setError(null);
    try {
      const result = await runML(sessionId, targetColumn);
      setMlResults(result);
      setData(result);
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : 'Error running ML pipeline.';
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-[70vh] space-y-6">
        <div className="relative">
          <div className="absolute inset-0 bg-[var(--accent-purple)] rounded-full blur-[50px] opacity-20 animate-pulse" />
          <Loader2 className="w-16 h-16 animate-spin text-[var(--accent-purple)] drop-shadow-[0_0_15px_rgba(123,47,255,0.8)] relative z-10" />
        </div>
        <div className="text-center space-y-2">
          <h2 className="text-2xl font-bold text-[var(--text-primary)]">Training Models...</h2>
          <p className="text-[var(--text-muted)] font-mono text-sm max-w-sm">Running multiple ML algorithms, tuning hyperparameters, and comparing performance metrics.</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-[70vh] space-y-4">
        <AlertTriangle className="w-16 h-16 text-red-500 drop-shadow-[0_0_15px_rgba(239,68,68,0.5)]" />
        <h2 className="text-2xl font-bold text-red-400">ML Pipeline Failed</h2>
        <p className="text-[var(--text-muted)] p-4 bg-red-500/10 border border-red-500/20 rounded-lg font-mono text-sm">{error}</p>
        <button onClick={() => { setError(null); setData(null); setMlResults(null); }} className="mt-6 px-6 py-2 border border-[var(--border-subtle)] hover:border-[var(--accent-cyan)] hover:text-[var(--accent-cyan)] transition-colors rounded-lg text-sm">Retry</button>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="space-y-8 animate-in fade-in duration-500">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <BrainCircuit className="w-6 h-6 text-[var(--accent-purple)]" />
            <h1 className="text-3xl font-bold tracking-tight text-[var(--text-primary)]">ML Recommender</h1>
          </div>
          <p className="text-[var(--text-muted)]">
            Select a target column from <span className="text-[var(--text-primary)] font-mono">{filename}</span> to train models
          </p>
        </div>

        <div className="data-card p-8 max-w-xl">
          <label className="block text-sm font-medium text-[var(--text-muted)] mb-3">Target Column</label>
          <select
            value={targetColumn}
            onChange={(e) => setTargetColumn(e.target.value)}
            className="w-full bg-[var(--bg-primary)] border border-[var(--border-subtle)] text-[var(--text-primary)] rounded-lg px-4 py-3 text-sm font-mono focus:outline-none focus:border-[var(--accent-purple)] transition-colors appearance-none"
          >
            <option value="">Select column to predict...</option>
            {columns.map((col) => (
              <option key={col} value={col}>{col}</option>
            ))}
          </select>
          <button
            onClick={handleRun}
            disabled={!targetColumn}
            className="mt-6 w-full px-6 py-3 bg-[var(--accent-purple)]/10 border border-[var(--accent-purple)]/30 text-[var(--accent-purple)] rounded-lg font-semibold hover:bg-[var(--accent-purple)]/20 transition-all text-sm disabled:opacity-30 disabled:cursor-not-allowed"
          >
            🧠 Train & Compare Models
          </button>
        </div>
      </div>
    );
  }

  // Results
  const primaryMetric = data.task_type === 'classification' ? 'accuracy' : 'r2';
  const primaryLabel = data.task_type === 'classification' ? 'Accuracy' : 'R² Score';
  const modelChartData = data.models.map((m, idx) => ({
    name: m.name,
    score: m[primaryMetric as keyof typeof m] as number ?? 0,
    fill: CHART_COLORS[idx % CHART_COLORS.length],
  }));

  // Radar data for best model
  const bestModel = data.models.find((m) => m.name === data.best_model);
  const radarData = bestModel ? [
    { metric: 'Accuracy', value: bestModel.accuracy ?? 0 },
    { metric: 'Precision', value: bestModel.precision ?? 0 },
    { metric: 'Recall', value: bestModel.recall ?? 0 },
    { metric: 'F1', value: bestModel.f1 ?? 0 },
  ].filter(d => d.value > 0) : [];

  return (
    <div className="space-y-8 animate-in fade-in duration-500 pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <BrainCircuit className="w-6 h-6 text-[var(--accent-purple)]" />
            <h1 className="text-3xl font-bold tracking-tight text-[var(--text-primary)]">ML Recommender</h1>
          </div>
          <p className="text-[var(--text-muted)]">
            Task: <span className="text-[var(--accent-purple)] font-mono uppercase">{data.task_type}</span>
          </p>
        </div>
        <button
          onClick={() => { setMlResults(null); setData(null); setTargetColumn(''); }}
          className="px-4 py-2 border border-[var(--border-subtle)] text-[var(--text-muted)] rounded-lg hover:border-[var(--accent-cyan)] hover:text-[var(--accent-cyan)] transition-colors text-sm"
        >
          Re-run Analysis
        </button>
      </div>

      {/* Leakage Warnings */}
      {data.leakage_warnings.length > 0 && (
        <div className="data-card p-4 border-l-4 border-l-[var(--accent-orange)]">
          <div className="flex items-center gap-2 mb-2">
            <ShieldAlert className="w-5 h-5 text-[var(--accent-orange)]" />
            <h3 className="text-sm font-bold text-[var(--accent-orange)]">Data Leakage Warnings</h3>
          </div>
          <ul className="space-y-1 text-sm text-[var(--text-muted)]">
            {data.leakage_warnings.map((w, i) => (
              <li key={i} className="font-mono text-xs">⚠ {w}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Best Model Card */}
      <div className="data-card p-6 border border-[var(--accent-green)]/30 relative overflow-hidden">
        <div className="absolute -right-10 -top-10 w-40 h-40 bg-[var(--accent-green)] rounded-full blur-[80px] opacity-10 pointer-events-none" />
        <div className="flex items-center gap-3 mb-4">
          <Trophy className="w-7 h-7 text-[var(--accent-green)]" />
          <div>
            <h2 className="text-lg font-bold text-[var(--text-primary)]">Best Model: <span className="text-[var(--accent-green)]">{data.best_model}</span></h2>
            <p className="text-xs text-[var(--text-muted)]">{primaryLabel}: <span className="font-mono text-[var(--accent-cyan)]">{bestModel ? (bestModel[primaryMetric as keyof typeof bestModel] as number ?? 0).toFixed(4) : 'N/A'}</span></p>
          </div>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Model Comparison Bar */}
        <div className="data-card flex flex-col overflow-hidden">
          <div className="p-4 border-b border-[var(--border-subtle)] bg-[var(--bg-card)]/80">
            <h3 className="font-bold text-[var(--text-primary)]">Model Comparison</h3>
            <p className="text-xs text-[var(--text-muted)] font-mono">{primaryLabel}</p>
          </div>
          <div className="p-4 h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={modelChartData} margin={{ top: 10, right: 10, left: 10, bottom: 40 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#21262d" vertical={false} />
                <XAxis dataKey="name" stroke="#8b949e" fontSize={10} angle={-30} textAnchor="end" tickMargin={10} />
                <YAxis stroke="#8b949e" fontSize={11} domain={[0, 1]} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="score" name={primaryLabel} radius={[4, 4, 0, 0]}>
                  {modelChartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Radar Chart for best model metrics */}
        {radarData.length >= 3 && (
          <div className="data-card flex flex-col overflow-hidden">
            <div className="p-4 border-b border-[var(--border-subtle)] bg-[var(--bg-card)]/80">
              <h3 className="font-bold text-[var(--text-primary)]">Best Model Metrics</h3>
              <p className="text-xs text-[var(--text-muted)] font-mono">{data.best_model}</p>
            </div>
            <div className="p-4 h-80">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={radarData} cx="50%" cy="50%" outerRadius="70%">
                  <PolarGrid stroke="#21262d" />
                  <PolarAngleAxis dataKey="metric" stroke="#8b949e" fontSize={11} />
                  <PolarRadiusAxis stroke="#21262d" domain={[0, 1]} fontSize={9} />
                  <Radar name="Score" dataKey="value" stroke="#00d4ff" fill="#00d4ff" fillOpacity={0.2} strokeWidth={2} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
      </div>

      {/* AI Summary */}
      {data.ai_summary && (
        <div className="data-card p-6 border-l-4 border-l-[var(--accent-cyan)]">
          <div className="flex items-start gap-4">
            <Zap className="w-5 h-5 text-[var(--accent-cyan)] shrink-0 mt-1" />
            <div>
              <h3 className="font-bold text-[var(--text-primary)] mb-2">AI Analysis</h3>
              <p className="text-sm text-[var(--text-muted)] leading-relaxed whitespace-pre-wrap">{data.ai_summary}</p>
            </div>
          </div>
        </div>
      )}

      {/* Model Details Table */}
      <div className="data-card overflow-hidden">
        <div className="p-4 border-b border-[var(--border-subtle)] bg-[var(--bg-card)]/80">
          <h2 className="text-lg font-bold text-[var(--text-primary)]">Detailed Results</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--border-subtle)] bg-[var(--bg-card)]">
                <th className="text-left p-3 text-[var(--text-muted)] font-mono text-xs uppercase">Model</th>
                {data.task_type === 'classification' ? (
                  <>
                    <th className="text-right p-3 text-[var(--text-muted)] font-mono text-xs uppercase">Accuracy</th>
                    <th className="text-right p-3 text-[var(--text-muted)] font-mono text-xs uppercase">Precision</th>
                    <th className="text-right p-3 text-[var(--text-muted)] font-mono text-xs uppercase">Recall</th>
                    <th className="text-right p-3 text-[var(--text-muted)] font-mono text-xs uppercase">F1</th>
                  </>
                ) : (
                  <>
                    <th className="text-right p-3 text-[var(--text-muted)] font-mono text-xs uppercase">R²</th>
                    <th className="text-right p-3 text-[var(--text-muted)] font-mono text-xs uppercase">RMSE</th>
                  </>
                )}
              </tr>
            </thead>
            <tbody>
              {data.models.map((model, idx) => (
                <tr key={idx} className={`border-b border-[var(--border-subtle)] ${model.name === data.best_model ? 'bg-[var(--accent-green)]/5' : idx % 2 === 0 ? 'bg-[var(--bg-primary)]/30' : ''} hover:bg-[var(--accent-cyan)]/5 transition-colors`}>
                  <td className="p-3 text-[var(--text-primary)] font-medium text-xs">
                    {model.name === data.best_model && <Trophy className="w-3 h-3 text-[var(--accent-green)] inline mr-1.5" />}
                    {model.name}
                  </td>
                  {data.task_type === 'classification' ? (
                    <>
                      <td className="text-right p-3 font-mono text-xs text-[var(--text-muted)]">{(model.accuracy ?? 0).toFixed(4)}</td>
                      <td className="text-right p-3 font-mono text-xs text-[var(--text-muted)]">{(model.precision ?? 0).toFixed(4)}</td>
                      <td className="text-right p-3 font-mono text-xs text-[var(--text-muted)]">{(model.recall ?? 0).toFixed(4)}</td>
                      <td className="text-right p-3 font-mono text-xs text-[var(--text-muted)]">{(model.f1 ?? 0).toFixed(4)}</td>
                    </>
                  ) : (
                    <>
                      <td className="text-right p-3 font-mono text-xs text-[var(--text-muted)]">{(model.r2 ?? 0).toFixed(4)}</td>
                      <td className="text-right p-3 font-mono text-xs text-[var(--text-muted)]">{(model.rmse ?? 0).toFixed(4)}</td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
