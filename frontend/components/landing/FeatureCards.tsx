'use client';

import { useEffect, useRef, useState } from 'react';

interface Feature {
  tag: string;
  title: string;
  desc: string;
  stat: string;
  accentColor: string;
}

const FEATURES: Feature[] = [
  {
    tag: 'module::eda',
    title: 'Automated Exploratory Analysis',
    desc: 'Distributions, correlations, outliers, and column typing — fully automated, zero code required.',
    stat: '→ stats.columns: 21 · missing: 3.2%',
    accentColor: '#3b82f6',
  },
  {
    tag: 'module::insights',
    title: 'Context-Aware Business Intelligence',
    desc: 'Domain detection, KPI extraction, business questions, and CEO-level AI insights referencing real data.',
    stat: '→ kpis_extracted: 5 · charts: 5',
    accentColor: '#a78bfa',
  },
  {
    tag: 'module::nlq',
    title: 'Natural Language Queries',
    desc: 'Ask questions in plain English. Gets converted to pandas and executed against your dataset instantly.',
    stat: '→ "avg charges by contract type?"',
    accentColor: '#34d399',
  },
  {
    tag: 'module::ml',
    title: 'Smart Algorithm Selection',
    desc: 'Recommends the optimal ML algorithm based on data shape, target variable type, and class balance.',
    stat: '→ model: XGBoost · accuracy: 88.4%',
    accentColor: '#fb923c',
  },
  {
    tag: 'module::bi',
    title: 'Production-Grade BI Dashboards',
    desc: 'Auto-generated HTML dashboards via NVIDIA NIM multi-call architecture. Power BI-quality output.',
    stat: '→ charts: 6 · kpis: 4 · ~24KB HTML',
    accentColor: '#38bdf8',
  },
  {
    tag: 'module::report',
    title: 'One-Click PDF Reports',
    desc: 'Export your full analysis as a stakeholder-ready PDF report. Every module result included.',
    stat: '→ pages: 12 · charts: 8',
    accentColor: '#f472b6',
  },
];

function FeatureCard({ feature, index }: { feature: Feature; index: number }) {
  const [visible, setVisible] = useState(false);
  const cardRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = cardRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      entries => {
        if (entries[0].isIntersecting) {
          setTimeout(() => setVisible(true), index * 80);
          observer.disconnect();
        }
      },
      { threshold: 0.15 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [index]);

  return (
    <div
      ref={cardRef}
      className="group relative flex flex-col p-6 rounded-2xl border transition-all duration-400 cursor-default"
      style={{
        background: 'rgba(15,15,26,0.7)',
        borderColor: 'rgba(59,130,246,0.12)',
        backdropFilter: 'blur(8px)',
        opacity: visible ? 1 : 0,
        transform: visible ? 'translateY(0)' : 'translateY(20px)',
        transition: 'opacity 0.55s ease-out, transform 0.55s ease-out, border-color 0.3s, box-shadow 0.3s',
      }}
      onMouseEnter={e => {
        const el = e.currentTarget;
        el.style.borderColor = feature.accentColor + '50';
        el.style.boxShadow = `0 0 24px ${feature.accentColor}18`;
        el.style.background = 'rgba(15,15,30,0.85)';
      }}
      onMouseLeave={e => {
        const el = e.currentTarget;
        el.style.borderColor = 'rgba(59,130,246,0.12)';
        el.style.boxShadow = 'none';
        el.style.background = 'rgba(15,15,26,0.7)';
      }}
    >
      {/* Tag */}
      <span
        className="font-mono text-[10px] font-medium mb-3 self-start px-2 py-0.5 rounded"
        style={{
          color: feature.accentColor,
          background: feature.accentColor + '18',
          border: `1px solid ${feature.accentColor}30`,
        }}
      >
        {feature.tag}
      </span>

      {/* Title */}
      <h3 className="font-display text-base font-bold text-[var(--text-primary)] mb-3 leading-snug">
        {feature.title}
      </h3>

      {/* Description */}
      <p className="text-sm text-[var(--text-muted)] leading-relaxed flex-1">
        {feature.desc}
      </p>

      {/* Stat */}
      <div
        className="font-mono text-[10px] mt-5 pt-4 border-t leading-relaxed"
        style={{
          borderColor: 'rgba(59,130,246,0.1)',
          color: feature.accentColor + 'aa',
        }}
      >
        {feature.stat}
      </div>

      {/* Corner accent */}
      <div
        className="absolute top-0 right-0 w-16 h-16 rounded-tr-2xl rounded-bl-full opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"
        style={{ background: `radial-gradient(circle at top right, ${feature.accentColor}10, transparent 60%)` }}
      />
    </div>
  );
}

export default function FeatureCards() {
  return (
    <section id="features" className="py-20 px-4 relative">
      {/* Section header */}
      <div className="text-center mb-14">
        <span className="font-mono text-xs text-[#64748b] uppercase tracking-[0.2em]">
          platform modules
        </span>
        <h2 className="font-display text-3xl md:text-4xl font-extrabold text-[var(--text-primary)] mt-3">
          Every tool you need,{' '}
          <span className="text-transparent bg-clip-text"
            style={{ backgroundImage: 'linear-gradient(135deg, #3b82f6, #60a5fa)' }}>
            zero setup.
          </span>
        </h2>
        <p className="text-[var(--text-muted)] mt-3 max-w-xl mx-auto text-sm">
          Upload once, explore everything. All 7 modules share the same session — results flow downstream automatically.
        </p>
      </div>

      {/* Grid */}
      <div className="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {FEATURES.map((f, i) => (
          <FeatureCard key={f.tag} feature={f} index={i} />
        ))}
      </div>
    </section>
  );
}
