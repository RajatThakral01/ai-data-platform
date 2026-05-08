'use client';

import { useEffect, useRef, useState } from 'react';
import CsvMorph from './CsvMorph';

const DOMAINS = ['Telecom', 'Retail', 'Finance', 'HR', 'Marketing'];
const INTERVAL_MS = 2500;

export default function HeroSection() {
  const [currentIdx, setCurrentIdx] = useState(0);
  const [nextIdx, setNextIdx]       = useState(1);
  const [animating, setAnimating]   = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    timerRef.current = setInterval(() => {
      setAnimating(true);
      // After "out" animation (300ms), swap word
      setTimeout(() => {
        setCurrentIdx(i => {
          const next = (i + 1) % DOMAINS.length;
          setNextIdx((next + 1) % DOMAINS.length);
          return next;
        });
        setAnimating(false);
      }, 320);
    }, INTERVAL_MS);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  return (
    <section className="relative min-h-screen flex flex-col items-center justify-center px-4 pt-20 pb-8 text-center overflow-hidden">

      {/* Grid overlay */}
      <div className="absolute inset-0 grid-bg opacity-50 pointer-events-none" />

      {/* Radial glow blobs */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2
          w-[600px] h-[400px] rounded-full pointer-events-none"
        style={{ background: 'radial-gradient(ellipse, rgba(59,130,246,0.06) 0%, transparent 70%)' }} />

      {/* Session badge */}
      <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full mb-8
          font-mono text-xs text-[#64748b] border border-[rgba(59,130,246,0.2)]"
        style={{ background: 'rgba(59,130,246,0.04)' }}>
        <span className="w-2 h-2 rounded-full bg-[var(--accent-green)] animate-pulse"
          style={{ boxShadow: '0 0 6px rgba(0,255,136,0.6)' }} />
        <span>session_active · multi-LLM routing online</span>
      </div>

      {/* Headline */}
      <h1 className="font-display text-5xl sm:text-6xl md:text-7xl font-extrabold tracking-tight
          text-[var(--text-primary)] max-w-3xl leading-[1.08] mb-4">
        Raw data →{' '}
        <span className="text-transparent bg-clip-text"
          style={{ backgroundImage: 'linear-gradient(135deg, #3b82f6 0%, #60a5fa 50%, #93c5fd 100%)' }}>
          instant intelligence.
        </span>
      </h1>

      {/* Rotating domain line */}
      <div className="flex items-center justify-center gap-3 mb-6 h-10 overflow-hidden">
        <span className="font-display text-2xl md:text-3xl font-bold text-[var(--text-muted)]">
          Built for
        </span>
        <div className="relative h-10 flex items-center overflow-hidden" style={{ minWidth: '140px' }}>
          <span
            className={animating ? 'word-out' : 'word-in'}
            style={{
              fontFamily: 'var(--font-display), Inter, sans-serif',
              fontSize: 'clamp(1.4rem, 3vw, 1.875rem)',
              fontWeight: 800,
              color: '#3b82f6',
              display: 'block',
              textShadow: '0 0 20px rgba(59,130,246,0.4)',
            }}
          >
            {DOMAINS[currentIdx]}
          </span>
        </div>
      </div>

      {/* Subheadline */}
      <p className="text-base md:text-lg text-[var(--text-muted)] max-w-2xl mx-auto leading-relaxed mb-12">
        Upload any CSV or Excel file. Get automated EDA, AI insights,
        natural language querying, and a production-grade BI dashboard —&nbsp;
        <span className="text-[var(--text-primary)]">zero code required.</span>
      </p>

      {/* CTA row */}
      <div className="flex flex-col sm:flex-row items-center gap-4 mb-16">
        <a href="#upload"
          className="px-8 py-3.5 rounded-lg font-semibold text-sm text-white transition-all duration-200"
          style={{
            background: 'linear-gradient(135deg, #2563eb, #3b82f6)',
            boxShadow: '0 0 24px rgba(59,130,246,0.35)',
          }}
          onMouseEnter={e => (e.currentTarget.style.boxShadow = '0 0 36px rgba(59,130,246,0.55)')}
          onMouseLeave={e => (e.currentTarget.style.boxShadow = '0 0 24px rgba(59,130,246,0.35)')}>
          Upload Your Dataset
        </a>
        <a href="#features"
          className="px-8 py-3.5 rounded-lg font-semibold text-sm text-[var(--text-muted)]
            border border-[var(--border-subtle)] hover:border-[#3b82f6] hover:text-[#3b82f6]
            transition-all duration-200">
          Explore Features
        </a>
      </div>

      {/* CSV Morph centerpiece */}
      <div className="w-full max-w-4xl px-4">
        <CsvMorph />
      </div>

      {/* Scroll hint */}
      <div className="mt-12 flex flex-col items-center gap-2 text-[#64748b] text-xs font-mono animate-bounce">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path d="M8 3v10M4 9l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
        <span>scroll to explore</span>
      </div>
    </section>
  );
}
