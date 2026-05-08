'use client';

import dynamic from 'next/dynamic';
import HeroSection from '@/components/landing/HeroSection';
import StatsCounter from '@/components/landing/StatsCounter';
import PipelineStrip from '@/components/landing/PipelineStrip';
import FeatureCards from '@/components/landing/FeatureCards';
import UploadZone from '@/components/landing/UploadZone';

// Canvas component must be client-only — skip SSR
const PipelineGraph = dynamic(
  () => import('@/components/landing/PipelineGraph'),
  { ssr: false }
);

export default function LandingPage() {
  return (
    <div className="relative min-h-screen bg-[var(--bg-primary)] overflow-x-hidden">

      {/* ── Background canvas (fixed, low opacity) ─── */}
      <PipelineGraph />

      {/* ── All foreground content ─────────────────── */}
      <div className="relative z-10">

        {/* 1. Hero: headline + rotating domain + CSV morph */}
        <HeroSection />

        {/* 2. Stats strip */}
        <StatsCounter />

        {/* 3. Pipeline progress strip */}
        <PipelineStrip />

        {/* Separator */}
        <div className="max-w-6xl mx-auto px-4">
          <div className="h-px w-full"
            style={{ background: 'linear-gradient(to right, transparent, rgba(59,130,246,0.2), transparent)' }} />
        </div>

        {/* 4. Feature cards */}
        <FeatureCards />

        {/* Separator */}
        <div className="max-w-6xl mx-auto px-4">
          <div className="h-px w-full"
            style={{ background: 'linear-gradient(to right, transparent, rgba(59,130,246,0.2), transparent)' }} />
        </div>

        {/* 5. Upload zone */}
        <UploadZone />

        {/* 6. Footer */}
        <footer className="text-center py-12 px-4 border-t"
          style={{ borderColor: 'rgba(59,130,246,0.08)' }}>
          <div className="font-mono text-xs text-[#334155] space-y-2">
            <div>
              <span className="text-[#3b82f6]">coldframe</span>
              {' '}v2.0.0 · multi-LLM routing ·{' '}
              <span className="text-[var(--accent-green)]">167/167</span> tests passing
            </div>
            <div className="text-[#1e293b]">
              groq · gemini · nvidia nim · ollama · next.js 14 · fastapi
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
}
