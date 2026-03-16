"use client";

import React, { useState } from 'react';
import { useStore } from '@/lib/store';
import { generateReport } from '@/lib/api';
import { FileText, Loader2, AlertTriangle, Download, Sparkles } from 'lucide-react';

export default function ReportPage() {
  const { sessionId, filename, setCurrentModule } = useStore();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [generated, setGenerated] = useState(false);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);

  React.useEffect(() => { setCurrentModule('report'); }, [setCurrentModule]);

  const handleGenerate = async () => {
    if (!sessionId) return;
    setLoading(true);
    setError(null);
    try {
      const blob = await generateReport(sessionId);
      const url = window.URL.createObjectURL(new Blob([blob], { type: 'application/pdf' }));
      setPdfUrl(url);
      setGenerated(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to generate report.');
    } finally { setLoading(false); }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-[70vh] space-y-6">
        <div className="relative">
          <div className="absolute inset-0 bg-[var(--accent-orange)] rounded-full blur-[50px] opacity-20 animate-pulse" />
          <Loader2 className="w-16 h-16 animate-spin text-[var(--accent-orange)] drop-shadow-[0_0_15px_rgba(255,107,53,0.8)] relative z-10" />
        </div>
        <div className="text-center space-y-2">
          <h2 className="text-2xl font-bold text-[var(--text-primary)]">Generating Report...</h2>
          <p className="text-[var(--text-muted)] font-mono text-sm max-w-sm">Compiling analysis results, charts, and AI insights into a PDF document.</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-[70vh] space-y-4">
        <AlertTriangle className="w-16 h-16 text-red-500" />
        <h2 className="text-2xl font-bold text-red-400">Report Generation Failed</h2>
        <p className="text-[var(--text-muted)] p-4 bg-red-500/10 border border-red-500/20 rounded-lg font-mono text-sm">{error}</p>
        <button onClick={() => { setError(null); setGenerated(false); }} className="mt-6 px-6 py-2 border border-[var(--border-subtle)] hover:border-[var(--accent-cyan)] hover:text-[var(--accent-cyan)] transition-colors rounded-lg text-sm">Retry</button>
      </div>
    );
  }

  if (generated && pdfUrl) {
    return (
      <div className="space-y-8 animate-in fade-in duration-500 pb-12">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <FileText className="w-6 h-6 text-[var(--accent-orange)]" />
            <h1 className="text-3xl font-bold tracking-tight text-[var(--text-primary)]">Report Generator</h1>
          </div>
          <p className="text-[var(--text-muted)]">Report ready for <span className="text-[var(--text-primary)] font-mono">{filename}</span></p>
        </div>

        <div className="data-card p-10 text-center space-y-6">
          <div className="inline-block p-6 bg-[var(--accent-green)]/10 rounded-full">
            <FileText className="w-16 h-16 text-[var(--accent-green)]" />
          </div>
          <h2 className="text-2xl font-bold text-[var(--text-primary)]">Report Generated Successfully</h2>
          <p className="text-[var(--text-muted)] text-sm max-w-md mx-auto">Your comprehensive analysis report has been compiled with AI-generated insights, charts, and recommendations.</p>
          <div className="flex items-center justify-center gap-4">
            <a href={pdfUrl} download={`report_${filename || 'analysis'}.pdf`}
              className="flex items-center gap-2 px-8 py-3 bg-[var(--accent-green)]/10 border border-[var(--accent-green)]/30 text-[var(--accent-green)] rounded-lg font-semibold hover:bg-[var(--accent-green)]/20 transition-all text-sm">
              <Download className="w-5 h-5" /> Download PDF
            </a>
            <button onClick={() => { setGenerated(false); setPdfUrl(null); }}
              className="px-8 py-3 border border-[var(--border-subtle)] text-[var(--text-muted)] rounded-lg hover:border-[var(--accent-cyan)] hover:text-[var(--accent-cyan)] transition-all text-sm">
              Regenerate
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div>
        <div className="flex items-center gap-2 mb-2">
          <FileText className="w-6 h-6 text-[var(--accent-orange)]" />
          <h1 className="text-3xl font-bold tracking-tight text-[var(--text-primary)]">Report Generator</h1>
        </div>
        <p className="text-[var(--text-muted)]">Generate a comprehensive PDF report for <span className="text-[var(--text-primary)] font-mono">{filename}</span></p>
      </div>

      <div className="data-card p-10 text-center border-dashed border-2 border-[var(--border-subtle)] hover:border-[var(--accent-orange)] transition-colors group cursor-pointer" onClick={handleGenerate}>
        <div className="relative inline-block mb-6">
          <div className="absolute inset-0 bg-[var(--accent-orange)] rounded-full blur-[40px] opacity-0 group-hover:opacity-20 transition-opacity" />
          <Sparkles className="w-20 h-20 text-[var(--accent-orange)] opacity-50 group-hover:opacity-100 transition-opacity relative z-10" />
        </div>
        <h2 className="text-2xl font-bold text-[var(--text-primary)] mb-2">Generate Analysis Report</h2>
        <p className="text-[var(--text-muted)] text-sm max-w-md mx-auto mb-6">Compiles all analysis results, AI insights, and visualizations into a professional PDF document.</p>
        <button className="px-8 py-3 bg-[var(--accent-orange)]/10 border border-[var(--accent-orange)]/30 text-[var(--accent-orange)] rounded-lg font-semibold hover:bg-[var(--accent-orange)]/20 transition-all text-sm">
          📄 Generate PDF Report
        </button>
      </div>
    </div>
  );
}
