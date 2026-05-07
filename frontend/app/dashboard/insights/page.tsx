"use client";

import React, { useEffect, useState } from 'react';
import { useStore } from '@/lib/store';
import { runInsights } from '@/lib/api';
import { InsightsResponse } from '@/lib/types';
import { Lightbulb, TrendingUp, AlertCircle, Loader2, Sparkles, AlertTriangle } from 'lucide-react';
import ReactECharts from 'echarts-for-react';

const CHART_COLORS = ['#00d4ff', '#7b2fff', '#4FCC8E', '#F7644F', '#ff6b35', '#ffff00'];

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-[#1a1a2e] border border-[#30363d] p-3 rounded-lg shadow-xl text-sm">
        <p className="text-[#8b949e] font-mono mb-1">{label}</p>
        <p className="text-[var(--text-primary)] font-bold">
          {payload[0].name}: <span className="text-[#00d4ff]">{payload[0].value?.toLocaleString() ?? 'N/A'}</span>
        </p>
      </div>
    );
  }
  return null;
};

export default function InsightsPage() {
  const { sessionId, filename, setCurrentModule, insightsResults, setInsightsResults } = useStore();
  const [data, setData] = useState<InsightsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setCurrentModule('insights');
  }, [setCurrentModule]);

  const fetchData = async () => {
    if (!sessionId) return;

    setLoading(true);
    setError(null);

    try {
      const result = await runInsights(sessionId);
      setInsightsResults(result);
      setData(result);
    } catch (err: unknown) {
      console.error("Failed to load insights:", err);
      const errorMsg = err && typeof err === 'object' && 'response' in err 
      ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail 
      : (err instanceof Error ? err.message : 'Error generating insights.');
      setError(errorMsg || "Failed to generate AI data insights");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (insightsResults) {
      setData(insightsResults);
      setLoading(false);
      return;
    }
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-[70vh] space-y-6">
        <div className="relative">
          <div className="absolute inset-0 bg-[var(--accent-purple)] rounded-full blur-[50px] opacity-20 animate-pulse" />
          <Loader2 className="w-16 h-16 animate-spin text-[var(--accent-purple)] drop-shadow-[0_0_15px_rgba(123,47,255,0.8)] relative z-10" />
        </div>
        <div className="text-center space-y-2">
          <h2 className="text-2xl font-bold text-[var(--text-primary)]">Agent Working...</h2>
          <p className="text-[var(--text-muted)] font-mono text-sm max-w-sm">
            Detecting business domain, scanning correlation matrices, and compiling AI narratives.
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-[70vh] space-y-4">
        <AlertTriangle className="w-16 h-16 text-red-500 drop-shadow-[0_0_15px_rgba(239,68,68,0.5)]" />
        <h2 className="text-2xl font-bold text-[var(--text-primary)] text-red-400">Insight Generation Failed</h2>
        <p className="text-[var(--text-muted)] p-4 bg-red-500/10 border border-red-500/20 rounded-lg font-mono text-sm">
          {error}
        </p>
        <button 
          onClick={() => { setError(null); setData(null); setInsightsResults(null); fetchData(); }}
          className="mt-6 px-6 py-2 border border-[var(--border-subtle)] hover:border-[var(--accent-cyan)] hover:text-[var(--accent-cyan)] transition-colors rounded-lg text-sm"
        >
          Retry Analysis
        </button>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="space-y-8 animate-in fade-in duration-500 pb-12">
      
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Lightbulb className="w-6 h-6 text-[var(--accent-purple)]" />
            <h1 className="text-3xl font-bold tracking-tight text-[var(--text-primary)]">Context-Aware BI</h1>
          </div>
          <p className="text-[var(--text-muted)]">
            AI-generated dashboard tailored for <span className="text-[var(--text-primary)] font-mono">{filename}</span>
          </p>
        </div>
        <button
          onClick={() => { setInsightsResults(null); setData(null); fetchData(); }}
          className="px-4 py-2 border border-[var(--border-subtle)] text-[var(--text-muted)] rounded-lg hover:border-[var(--accent-cyan)] hover:text-[var(--accent-cyan)] transition-colors text-sm"
        >
          Re-run Analysis
        </button>
      </div>

      {/* Business Context Banner */}
      <div className="data-card p-6 border-l-4 border-l-[var(--accent-purple)] relative overflow-hidden group">
        <div className="absolute -right-10 -top-10 w-40 h-40 bg-[var(--accent-purple)] rounded-full blur-[80px] opacity-10 group-hover:opacity-20 transition-opacity pointer-events-none" />
        
        <div className="flex items-start gap-4">
          <div className="p-3 bg-[var(--accent-purple)]/10 rounded-lg shrink-0">
            <Sparkles className="w-6 h-6 text-[var(--accent-purple)]" />
          </div>
          <div className="flex-1">
            <h2 className="text-lg font-bold text-[var(--text-primary)] mb-1 flex items-center gap-2">
              Detected Domain: <span className="text-[var(--accent-purple)]">{data.business_context.domain}</span>
            </h2>
            <p className="text-sm text-[var(--text-muted)] mb-4 leading-relaxed">
              Based on the data dictionary, this dataset represents <span className="text-[var(--text-primary)] font-medium">{data.business_context.business_entity}</span>. 
              The primary target metric optimized is <span className="text-[var(--accent-cyan)] font-mono bg-[var(--accent-cyan)]/10 px-1.5 py-0.5 rounded">{data.business_context.target_metric}</span>.
            </p>
            
            <div className="space-y-2">
              <h3 className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider">Key Business Questions Assessed</h3>
              <ul className="text-sm text-[var(--text-primary)] space-y-1 font-medium">
                {data.business_context.business_questions.map((q, idx) => (
                  <li key={idx} className="flex gap-2">
                    <span className="text-[var(--accent-purple)]">→</span> {q}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>

      {data.executive_summary && (
        <div className="data-card p-5 mb-4 border-l-4 border-l-[var(--accent-cyan)]">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-1.5 h-5 rounded-full bg-[var(--accent-cyan)]" />
            <h3 className="text-xs font-semibold tracking-widest uppercase text-[var(--accent-cyan)]">
              Executive Summary
            </h3>
          </div>
          <p className="text-sm leading-relaxed text-[var(--text-primary)]">
            {data.executive_summary}
          </p>
        </div>
      )}

      {/* KPI Cards Grid */}
      <div>
        <h2 className="text-xl font-bold text-[var(--text-primary)] mb-4">Core Performance Indicators</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {data.kpis.map((kpi, idx) => (
            <div key={idx} className="data-card p-5 group hover:-translate-y-1 hover:border-[var(--accent-cyan)] transition-all duration-300">
              <h3 className="text-sm font-medium text-[var(--text-muted)] mb-2 truncate" title={kpi.label}>{kpi.label}</h3>
              <div className="text-3xl font-bold font-mono text-[var(--text-primary)] mb-1 shrink-0">{kpi.formatted_value}</div>
            </div>
          ))}
        </div>
      </div>

      {/* AI Narrative Section */}
      {data.ai_insights && data.ai_insights.length > 0 && (
        <div className="data-card p-6 border border-[var(--border-subtle)]">
          <h2 className="text-xl font-bold text-[var(--text-primary)] mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-[var(--accent-cyan)]" /> Executive Summary
          </h2>
          <div className="space-y-3">
            {data.ai_insights.map((insight, idx) => (
              <div key={idx} className="flex gap-4 p-3 rounded-lg bg-[var(--bg-card-hover)]/50 border border-[var(--border-subtle)] text-sm text-[var(--text-primary)] leading-relaxed">
                <span className="text-[var(--accent-cyan)] font-mono font-bold shrink-0 mt-0.5">0{idx + 1}</span>
                <p>{insight}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Dynamic Charts Grid */}
      <div>
        <h2 className="text-xl font-bold text-[var(--text-primary)] mb-4">Domain Analysis</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {data.charts.map((chart, idx) => (
            <div key={idx} className="data-card flex flex-col overflow-hidden group">
              <div className="p-4 border-b border-[var(--border-subtle)] bg-[var(--bg-card-hover)]/40">
                <h3 className="font-bold text-[var(--text-primary)] text-sm mb-1 truncate" title={chart.title}>{chart.title}</h3>
                <p className="text-xs text-[var(--text-muted)] font-mono truncate">{chart.business_question}</p>
              </div>
              
              <div className="p-4 h-80 relative flex items-center justify-center bg-white/5">
                {chart.data && chart.data.length > 0 ? (
                  (() => {
                    const labels = chart.data.map((d: any) => d.x);
                    const values = chart.data.map((d: any) => d.y);
                    const COLORS = ["#00d4ff", "#7b2fff", "#ff6b35", "#00ff88", "#d4b100"];

                    let option: any = {};

                    if (chart.chart_type === 'line') {
                      option = {
                        backgroundColor: 'transparent',
                        tooltip: { trigger: 'axis' },
                        grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
                        xAxis: { type: 'category', data: labels, axisLabel: { color: '#64748b', fontSize: 11 } },
                        yAxis: { type: 'value', axisLabel: { color: '#64748b', fontSize: 11 } },
                        series: [{
                          data: values, type: 'line', smooth: true,
                          lineStyle: { color: '#00d4ff', width: 3 },
                          itemStyle: { color: '#00d4ff' },
                          areaStyle: { color: 'rgba(0, 212, 255, 0.1)' }
                        }]
                      };
                    } else if (chart.chart_type === 'pie' || chart.chart_type === 'donut') {
                      option = {
                        backgroundColor: 'transparent',
                        tooltip: { trigger: 'item' },
                        legend: { bottom: 0, textStyle: { color: '#64748b', fontSize: 11 } },
                        series: [{
                          type: 'pie',
                          radius: chart.chart_type === 'donut' ? ['40%', '70%'] : '65%',
                          data: chart.data.map((d: any, i: number) => ({
                            value: d.y, name: d.x,
                            itemStyle: { color: COLORS[i % COLORS.length] }
                          })),
                          label: { show: false }
                        }]
                      };
                    } else if (chart.chart_type === 'scatter') {
                      option = {
                        backgroundColor: 'transparent',
                        tooltip: { trigger: 'item' },
                        grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
                        xAxis: { type: 'category', data: labels, axisLabel: { color: '#64748b', fontSize: 11 } },
                        yAxis: { type: 'value', axisLabel: { color: '#64748b', fontSize: 11 } },
                        series: [{
                          data: values, type: 'scatter',
                          itemStyle: { color: '#7b2fff' }, symbolSize: 10
                        }]
                      };
                    } else {
                      option = {
                        backgroundColor: 'transparent',
                        tooltip: { trigger: 'axis' },
                        grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
                        xAxis: {
                          type: 'category', data: labels,
                          axisLabel: { color: '#64748b', fontSize: 11, rotate: labels.length > 5 ? 45 : 0 }
                        },
                        yAxis: { type: 'value', axisLabel: { color: '#64748b', fontSize: 11 } },
                        series: [{
                          data: values, type: 'bar',
                          itemStyle: { color: '#7b2fff', borderRadius: [4, 4, 0, 0] }
                        }]
                      };
                    }

                    return (
                      <ReactECharts
                        option={option}
                        style={{ height: '100%', width: '100%' }}
                        opts={{ renderer: 'canvas' }}
                      />
                    );
                  })()
                ) : (
                  <div className="text-center">
                    <AlertCircle className="w-8 h-8 text-[var(--text-muted)] mx-auto mb-2 opacity-50" />
                    <p className="text-sm text-[var(--text-muted)] font-mono">No renderable data found for this specification.</p>
                  </div>
                )}
              </div>
              
              <div className="p-3 bg-[var(--accent-purple)]/5 border-t border-[var(--accent-purple)]/20 mt-auto">
                <div className="flex gap-2 items-start text-xs">
                  <Lightbulb className="w-4 h-4 text-[var(--accent-purple)] shrink-0 mt-0.5" />
                  <p className="text-[var(--text-primary)] italic opacity-90 leading-tight">
                    {chart.insight_hint}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}
