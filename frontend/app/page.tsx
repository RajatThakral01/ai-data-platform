"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useDropzone } from 'react-dropzone';
import { UploadCloud, FileText, Database, Sparkles, Loader2, AlertCircle, Activity } from 'lucide-react';
import { uploadFile } from '@/lib/api';
import { useStore } from '@/lib/store';
import { cn } from '@/lib/utils';

export default function LandingPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const { setSessionId, setFilename, setColumns, setRowCount } = useStore();

  const handleFileUpload = async (file: File) => {
    setError(null);
    setIsUploading(true);
    
    try {
      const data = await uploadFile(file);
      
      // Update global store with the response
      setSessionId(data.session_id);
      setFilename(data.filename);
      setColumns(data.column_names);
      setRowCount(data.rows);
      
      // Redirect to dashboard
      router.push('/dashboard');
    } catch (err: unknown) {
      console.error('Upload Error:', err);
      const errorMsg = err && typeof err === 'object' && 'response' in err 
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail 
        : (err instanceof Error ? err.message : 'Failed to upload file. Please try again.');
      setError(errorMsg || 'Failed to upload file. Please try again.');
      setIsUploading(false);
    }
  };

  const onDrop = (acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      handleFileUpload(acceptedFiles[0]);
    }
  };

  const { getRootProps, getInputProps, isDragActive, isDragReject, open } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls']
    },
    maxFiles: 1,
    maxSize: 200 * 1024 * 1024,
    noClick: true,
    noKeyboard: true,
    disabled: isUploading
  });

  const loadSampleData = async () => {
    // For now, prompt the user to upload manually as we don't have sample files served statically yet
    setError("Sample data not bundled yet. Please upload a CSV.");
  };

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] grid-bg relative flex flex-col items-center justify-center p-4">
      {/* Decorative Background Elements */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-[var(--accent-cyan)] opacity-5 rounded-full blur-[100px] pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-[var(--accent-purple)] opacity-5 rounded-full blur-[100px] pointer-events-none" />

      <div className="w-full max-w-4xl z-10 flex flex-col items-center">
        {/* Header Unit */}
        <div className="text-center mb-12 animate-in fade-in slide-in-from-bottom-4 duration-1000">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-[var(--border-subtle)] bg-[rgba(0,212,255,0.05)] mb-6 text-[var(--accent-cyan)] font-mono text-sm shadow-[0_0_15px_rgba(0,212,255,0.1)]">
            <Sparkles className="w-4 h-4" />
            <span>AI-Powered Data Analysis v2.0</span>
          </div>
          <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6 text-[var(--text-primary)]">
            Intelligence <br className="hidden md:block" />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-[var(--accent-cyan)] to-[var(--accent-purple)] drop-shadow-[0_0_15px_rgba(0,212,255,0.3)]">
              from your Data
            </span>
          </h1>
          <p className="text-lg text-[var(--text-muted)] max-w-2xl mx-auto">
            Upload your CSV or Excel file to instantly unlock comprehensive EDA, machine learning insights, and interactive business intelligence.
          </p>
        </div>

        {/* Upload Zone */}
        <div 
          {...getRootProps()} 
          className={cn(
            "w-full max-w-2xl p-12 rounded-xl border-2 border-dashed transition-all duration-300 flex flex-col items-center justify-center text-center cursor-pointer relative overflow-hidden group data-card shadow-2xl",
            isDragActive 
              ? "border-[var(--accent-cyan)] bg-[rgba(0,212,255,0.05)] scale-[1.02]" 
              : isDragReject 
                ? "border-red-500 bg-red-500/5" 
                : "border-[var(--border-subtle)] hover:border-[var(--accent-cyan)] hover:bg-[rgba(0,212,255,0.02)]"
          )}
        >
          <input {...getInputProps()} />
          
          {isUploading ? (
            <div className="flex flex-col items-center gap-4 text-[var(--accent-cyan)] animate-in fade-in duration-500">
              <Loader2 className="w-16 h-16 animate-spin drop-shadow-[0_0_15px_rgba(0,212,255,0.5)]" />
              <div className="space-y-1">
                <h3 className="text-xl font-bold">Initializing Analysis...</h3>
                <p className="text-sm opacity-80 font-mono">Indexing chunks and preparing session environment</p>
              </div>
            </div>
          ) : (
            <>
              <div className="p-4 rounded-full bg-[rgba(255,255,255,0.03)] mb-4 group-hover:bg-[rgba(0,212,255,0.1)] transition-colors duration-300">
                <UploadCloud className={cn(
                  "w-12 h-12 transition-colors duration-300",
                  isDragActive ? "text-[var(--accent-cyan)] scale-110" : "text-[var(--text-muted)] group-hover:text-[var(--accent-cyan)]"
                )} />
              </div>
              <h3 className="text-xl font-bold text-[var(--text-primary)] mb-2 group-hover:text-[var(--accent-cyan)] transition-colors">
                {isDragActive ? "Drop to engage processing" : "Drag & drop to analyze"}
              </h3>
              <p className="text-sm text-[var(--text-muted)] mb-6">
                Supports CSV, XLS, XLSX up to 200MB
              </p>
              
              <div className="flex items-center gap-3 w-full max-w-xs mx-auto mb-2">
                <div className="h-px bg-gradient-to-r from-transparent via-[var(--border-subtle)] to-transparent flex-1" />
                <span className="text-xs font-mono text-[var(--text-muted)] uppercase tracking-wider">or</span>
                <div className="h-px bg-gradient-to-r from-transparent via-[var(--border-subtle)] to-transparent flex-1" />
              </div>
              
              <button 
                type="button" 
                className="mt-4 px-6 py-2 rounded border border-[var(--border-subtle)] bg-transparent text-[var(--text-primary)] font-medium text-sm hover:border-[var(--accent-cyan)] hover:text-[var(--accent-cyan)] transition-all z-10"
                onClick={(e) => { e.stopPropagation(); open(); }}
              >
                Browse Local Files
              </button>
            </>
          )}

          {/* Hover Glow Effect */}
          <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-[rgba(0,212,255,0.05)] opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />
        </div>

        {error && (
          <div className="mt-6 w-full max-w-2xl px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/50 flex items-start gap-3 text-red-400 animate-in slide-in-from-bottom-2">
            <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
            <p className="text-sm">{error}</p>
          </div>
        )}

        {/* Feature Cards / Sample Data */}
        <div className="mt-16 w-full max-w-5xl grid grid-cols-1 md:grid-cols-3 gap-6 animate-in fade-in slide-in-from-bottom-8 duration-1000 delay-200">
          <div 
            onClick={loadSampleData}
            className="p-6 rounded-xl data-card cursor-pointer group hover:border-[var(--accent-purple)] transition-colors duration-300"
          >
            <Database className="w-8 h-8 text-[var(--accent-purple)] mb-4 opacity-80 group-hover:opacity-100 group-hover:scale-110 transition-all" />
            <h4 className="text-lg font-bold text-[var(--text-primary)] mb-2">Retail Sales Demo</h4>
            <p className="text-sm text-[var(--text-muted)] leading-relaxed">
              Explore Superstore Sales data. 10k rows of transactions across regions, categories, and segments.
            </p>
          </div>

          <div 
            onClick={loadSampleData}
            className="p-6 rounded-xl data-card cursor-pointer group hover:border-[var(--accent-green)] transition-colors duration-300"
          >
            <Activity className="w-8 h-8 text-[var(--accent-green)] mb-4 opacity-80 group-hover:opacity-100 group-hover:scale-110 transition-all cursor-pointer" />
            <h4 className="text-lg font-bold text-[var(--text-primary)] mb-2">Churn Prediction</h4>
            <p className="text-sm text-[var(--text-muted)] leading-relaxed">
              Analyze a Telco Customer dataset to identify high-risk churn indicators using Machine Learning capabilities.
            </p>
          </div>

          <div className="p-6 rounded-xl data-card border-none bg-gradient-to-br from-[var(--bg-card)] to-[rgba(0,212,255,0.05)] relative overflow-hidden">
            <div className="absolute top-0 right-0 w-32 h-32 bg-[var(--accent-cyan)] opacity-10 rounded-full blur-[40px] -mr-10 -mt-10 pointer-events-none" />
            <FileText className="w-8 h-8 text-[var(--accent-cyan)] mb-4 opacity-80" />
            <h4 className="text-lg font-bold text-[var(--text-primary)] mb-2">Secure & Private</h4>
            <p className="text-sm text-[var(--text-muted)] leading-relaxed">
              All data is processed in isolated sessions with immediate teardown on exit. No persistent cloud storage.
            </p>
          </div>
        </div>

      </div>
    </div>
  );
}
