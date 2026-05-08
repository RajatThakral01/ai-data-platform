'use client';

import { useEffect, useRef, useState } from 'react';

interface Stat {
  value: number;
  label: string;
  prefix?: string;
  suffix?: string;
  display?: string; // override display e.g. "167/167"
}

const STATS: Stat[] = [
  { value: 7,   label: 'AI Modules',     suffix: '' },
  { value: 167, label: 'Tests Passing',  suffix: '', display: '167/167' },
  { value: 10,  label: 'Domains',        suffix: '+' },
  { value: 3,   label: 'LLM Providers',  suffix: '' },
];

function easeOutQuart(t: number) {
  return 1 - Math.pow(1 - t, 4);
}

function Counter({ stat }: { stat: Stat }) {
  const [count, setCount] = useState(0);
  const hasRunRef = useRef(false);
  const elRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = elRef.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      entries => {
        if (entries[0].isIntersecting && !hasRunRef.current) {
          hasRunRef.current = true;
          const duration = 1500;
          const startTime = performance.now();

          const tick = (now: number) => {
            const elapsed = now - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const eased = easeOutQuart(progress);
            setCount(Math.round(eased * stat.value));
            if (progress < 1) requestAnimationFrame(tick);
          };

          requestAnimationFrame(tick);
        }
      },
      { threshold: 0.5 }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, [stat.value]);

  const displayValue = stat.display
    ? stat.display
    : `${stat.prefix ?? ''}${count}${stat.suffix ?? ''}`;

  return (
    <div ref={elRef} className="text-center group">
      <div
        className="font-mono text-4xl md:text-5xl font-bold mb-2 transition-all duration-300"
        style={{
          color: '#3b82f6',
          textShadow: '0 0 20px rgba(59,130,246,0.4)',
        }}
      >
        {displayValue}
      </div>
      <div className="text-xs uppercase tracking-widest text-[var(--text-muted)] font-mono">
        {stat.label}
      </div>
    </div>
  );
}

export default function StatsCounter() {
  return (
    <section className="relative py-16 px-4">
      {/* Divider line */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-px h-12"
        style={{ background: 'linear-gradient(to bottom, transparent, rgba(59,130,246,0.3))' }} />

      {/* Background strip */}
      <div className="max-w-4xl mx-auto rounded-2xl px-8 py-10 relative overflow-hidden"
        style={{
          background: 'rgba(15,15,26,0.6)',
          border: '1px solid rgba(59,130,246,0.12)',
          backdropFilter: 'blur(8px)',
        }}>

        {/* Glow center */}
        <div className="absolute inset-0 pointer-events-none"
          style={{ background: 'radial-gradient(ellipse at 50% 50%, rgba(59,130,246,0.04) 0%, transparent 70%)' }} />

        <div className="relative grid grid-cols-2 md:grid-cols-4 gap-8">
          {STATS.map(stat => (
            <Counter key={stat.label} stat={stat} />
          ))}
        </div>
      </div>
    </section>
  );
}
