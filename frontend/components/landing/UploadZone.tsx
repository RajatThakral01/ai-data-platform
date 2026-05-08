'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useDropzone } from 'react-dropzone';
import { UploadCloud, Loader2, AlertCircle } from 'lucide-react';
import { uploadFile } from '@/lib/api';
import { useStore } from '@/lib/store';
import { cn } from '@/lib/utils';

const SAMPLE_CHIPS = [
  { label: 'Try Telecom Churn',  domain: 'telecom'  },
  { label: 'Try Retail Sales',   domain: 'retail'   },
  { label: 'Try HR Attrition',   domain: 'hr'       },
  { label: 'Try Finance Risk',   domain: 'finance'  },
];

const LLM_PROVIDERS = [
  { name: 'groq',   primary: true  },
  { name: 'gemini', primary: false },
  { name: 'ollama', primary: false },
];

export default function UploadZone() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const { setSessionId, setFilename, setColumns, setRowCount } = useStore();

  const handleFileUpload = async (file: File) => {
    setError(null);
    setIsUploading(true);
    try {
      const data = await uploadFile(file);
      setSessionId(data.session_id);
      setFilename(data.filename);
      setColumns(data.column_names);
      setRowCount(data.rows);
      router.push('/dashboard');
    } catch (err: unknown) {
      console.error('Upload Error:', err);
      const errorMsg =
        err && typeof err === 'object' && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : err instanceof Error
          ? err.message
          : 'Failed to upload file. Please try again.';
      setError(errorMsg || 'Failed to upload file. Please try again.');
      setIsUploading(false);
    }
  };

  const onDrop = (acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) handleFileUpload(acceptedFiles[0]);
  };

  const { getRootProps, getInputProps, isDragActive, isDragReject, open } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
    },
    maxFiles: 1,
    maxSize: 200 * 1024 * 1024,
    noClick: true,
    noKeyboard: true,
    disabled: isUploading,
  });

  const handleSampleChip = (domain: string) => {
    setError(`Sample datasets coming soon. Upload your own ${domain} CSV to explore the platform.`);
  };

  return (
    <section id="upload" className="py-20 px-4 relative">
      {/* Section header */}
      <div className="text-center mb-10">
        <span className="font-mono text-xs text-[#64748b] uppercase tracking-[0.2em]">
          get started
        </span>
        <h2 className="font-display text-3xl md:text-4xl font-extrabold text-[var(--text-primary)] mt-3">
          Drop your data. Get answers.
        </h2>
        <p className="text-[var(--text-muted)] mt-3 max-w-lg mx-auto text-sm">
          CSV or Excel, up to 200 MB. Your data never leaves your session.
        </p>
      </div>

      <div className="max-w-2xl mx-auto flex flex-col items-center gap-6">

        {/* Drop zone */}
        <div
          {...getRootProps()}
          className={cn(
            'w-full rounded-2xl relative overflow-hidden cursor-pointer transition-all duration-300',
            isDragReject && 'opacity-60'
          )}
          style={{
            padding: '2px', // border via background-image trick
          }}
        >
          {/* Marching border wrapper */}
          <div
            className={cn('w-full h-full rounded-2xl', !isDragActive && 'marching-border')}
            style={isDragActive ? {
              background: 'linear-gradient(135deg, #3b82f6, #60a5fa)',
              padding: '2px',
              borderRadius: '16px',
            } : { padding: '2px' }}
          >
            <div
              className={cn(
                'relative rounded-2xl overflow-hidden flex flex-col items-center justify-center',
                'text-center transition-all duration-300 min-h-[240px]'
              )}
              style={{
                background: isDragActive
                  ? 'rgba(59,130,246,0.08)'
                  : 'rgba(10,10,20,0.9)',
                border: isDragActive ? 'none' : '1px solid rgba(59,130,246,0.15)',
                boxShadow: isDragActive ? '0 0 40px rgba(59,130,246,0.2) inset' : 'none',
              }}
            >
              <input {...getInputProps()} />

              {/* Scan line (only when not dragging/uploading) */}
              {!isDragActive && !isUploading && (
                <div
                  className="absolute left-0 right-0 h-px pointer-events-none z-10"
                  style={{
                    background: 'linear-gradient(to right, transparent, rgba(59,130,246,0.6), transparent)',
                    animation: 'scanLine 2.8s ease-in-out infinite',
                  }}
                />
              )}

              <div className="relative z-20 flex flex-col items-center gap-4 px-8 py-10">
                {isUploading ? (
                  <>
                    <Loader2
                      className="w-14 h-14 animate-spin"
                      style={{ color: '#3b82f6', filter: 'drop-shadow(0 0 12px rgba(59,130,246,0.5))' }}
                    />
                    <div className="space-y-1">
                      <h3 className="text-lg font-bold text-[var(--text-primary)]">
                        Initializing Analysis…
                      </h3>
                      <p className="text-sm font-mono text-[var(--text-muted)]">
                        Indexing dataset · preparing session environment
                      </p>
                    </div>
                  </>
                ) : isDragActive ? (
                  <>
                    <UploadCloud
                      className="w-14 h-14"
                      style={{ color: '#3b82f6', filter: 'drop-shadow(0 0 16px rgba(59,130,246,0.7))' }}
                    />
                    <h3 className="text-lg font-bold text-[#3b82f6]">
                      Release to upload & analyze
                    </h3>
                  </>
                ) : (
                  <>
                    <div
                      className="p-4 rounded-full mb-2"
                      style={{ background: 'rgba(59,130,246,0.06)', border: '1px solid rgba(59,130,246,0.15)' }}
                    >
                      <UploadCloud className="w-10 h-10 text-[var(--text-muted)]" />
                    </div>
                    <div>
                      <h3 className="text-lg font-bold text-[var(--text-primary)] mb-1">
                        Drag & drop your dataset
                      </h3>
                      <p className="text-sm text-[var(--text-muted)]">
                        CSV, XLS, XLSX · up to 200 MB
                      </p>
                    </div>

                    <div className="flex items-center gap-3 w-full max-w-xs">
                      <div className="h-px flex-1"
                        style={{ background: 'linear-gradient(to right, transparent, rgba(59,130,246,0.2), transparent)' }} />
                      <span className="text-xs font-mono text-[var(--text-muted)] uppercase tracking-wider">or</span>
                      <div className="h-px flex-1"
                        style={{ background: 'linear-gradient(to right, transparent, rgba(59,130,246,0.2), transparent)' }} />
                    </div>

                    {/* Upload button */}
                    <button
                      type="button"
                      onClick={e => { e.stopPropagation(); open(); }}
                      className="px-8 py-3 rounded-lg font-semibold text-sm text-white transition-all duration-200"
                      style={{
                        background: 'linear-gradient(135deg, #2563eb, #3b82f6)',
                        boxShadow: '0 0 20px rgba(59,130,246,0.3)',
                      }}
                      onMouseEnter={e => {
                        e.currentTarget.style.boxShadow = '0 0 32px rgba(59,130,246,0.5)';
                        e.currentTarget.style.transform = 'translateY(-1px)';
                      }}
                      onMouseLeave={e => {
                        e.currentTarget.style.boxShadow = '0 0 20px rgba(59,130,246,0.3)';
                        e.currentTarget.style.transform = 'translateY(0)';
                      }}
                    >
                      Browse Local Files
                    </button>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="w-full px-4 py-3 rounded-lg flex items-start gap-3 text-red-400 text-sm animate-fade-slide-up"
            style={{ background: 'rgba(239,68,68,0.06)', border: '1px solid rgba(239,68,68,0.25)' }}>
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <p>{error}</p>
          </div>
        )}

        {/* Sample chips */}
        <div className="flex flex-wrap gap-2 justify-center">
          {SAMPLE_CHIPS.map(chip => (
            <button
              key={chip.domain}
              onClick={() => handleSampleChip(chip.domain)}
              className="px-4 py-1.5 rounded-full font-mono text-xs transition-all duration-200"
              style={{
                background: 'rgba(59,130,246,0.04)',
                border: '1px solid rgba(59,130,246,0.15)',
                color: '#64748b',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.borderColor = 'rgba(59,130,246,0.5)';
                e.currentTarget.style.color = '#60a5fa';
                e.currentTarget.style.background = 'rgba(59,130,246,0.08)';
              }}
              onMouseLeave={e => {
                e.currentTarget.style.borderColor = 'rgba(59,130,246,0.15)';
                e.currentTarget.style.color = '#64748b';
                e.currentTarget.style.background = 'rgba(59,130,246,0.04)';
              }}
            >
              {chip.label}
            </button>
          ))}
        </div>

        {/* LLM routing indicator */}
        <div className="flex items-center gap-1.5 font-mono text-xs">
          <span className="text-[#64748b]">routing:</span>
          {LLM_PROVIDERS.map((p, i) => (
            <React.Fragment key={p.name}>
              {i > 0 && <span className="text-[#334155]">→</span>}
              <span
                className="px-2 py-0.5 rounded text-[10px] transition-colors"
                style={{
                  background: p.primary ? 'rgba(59,130,246,0.12)' : 'transparent',
                  color: p.primary ? '#3b82f6' : '#475569',
                  border: p.primary ? '1px solid rgba(59,130,246,0.25)' : '1px solid transparent',
                  fontWeight: p.primary ? 600 : 400,
                }}
              >
                {p.name}
              </span>
            </React.Fragment>
          ))}
          <span className="ml-1 w-1.5 h-1.5 rounded-full bg-[var(--accent-green)] animate-pulse"
            style={{ boxShadow: '0 0 6px rgba(0,255,136,0.5)' }} />
        </div>
      </div>
    </section>
  );
}
