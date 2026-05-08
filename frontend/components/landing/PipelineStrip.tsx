'use client';

import { useEffect, useRef, useState } from 'react';
import {
  UploadCloud, BarChart2, Wand2, Lightbulb,
  BarChart3, MessageSquareText, BrainCircuit, FileText,
  type LucideIcon,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface Step {
  label: string;
  icon: LucideIcon;
  tag: string;
}

const STEPS: Step[] = [
  { label: 'Upload',         icon: UploadCloud,        tag: '01' },
  { label: 'Smart EDA',      icon: BarChart2,           tag: '02' },
  { label: 'Cleaning',       icon: Wand2,               tag: '03' },
  { label: 'Insights',       icon: Lightbulb,           tag: '04' },
  { label: 'BI Dashboard',   icon: BarChart3,           tag: '05' },
  { label: 'NL Query',       icon: MessageSquareText,   tag: '06' },
  { label: 'ML Recommender', icon: BrainCircuit,        tag: '07' },
  { label: 'Report',         icon: FileText,            tag: '08' },
];

const STEP_DELAY_MS = 200;

export default function PipelineStrip() {
  const [activeIndex, setActiveIndex] = useState(-1);
  const hasRunRef = useRef(false);
  const sectionRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const el = sectionRef.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      entries => {
        if (entries[0].isIntersecting && !hasRunRef.current) {
          hasRunRef.current = true;
          let idx = 0;
          const interval = setInterval(() => {
            setActiveIndex(idx);
            idx++;
            if (idx >= STEPS.length) clearInterval(interval);
          }, STEP_DELAY_MS);
        }
      },
      { threshold: 0.3 }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <section ref={sectionRef} className="py-16 px-4 relative">
      {/* Section label */}
      <div className="text-center mb-8">
        <span className="font-mono text-xs text-[#64748b] uppercase tracking-[0.2em]">
          8-module pipeline
        </span>
      </div>

      {/* Strip */}
      <div className="max-w-6xl mx-auto overflow-x-auto pb-2">
        <div className="flex items-center justify-center min-w-max mx-auto gap-0">
          {STEPS.map((step, i) => {
            const isActive = i <= activeIndex;
            const isLast = i === STEPS.length - 1;
            return (
              <div key={step.label} className="flex items-center">
                {/* Step card */}
                <div
                  className={cn(
                    'flex flex-col items-center gap-2 px-3 py-3 rounded-xl border transition-all duration-500',
                    isActive
                      ? 'border-[#3b82f6] text-[#3b82f6] bg-[rgba(59,130,246,0.06)]'
                      : 'border-[var(--border-subtle)] text-[var(--text-muted)] bg-transparent'
                  )}
                  style={isActive ? { boxShadow: '0 0 14px rgba(59,130,246,0.2)' } : {}}
                >
                  {/* Tag */}
                  <span className={cn(
                    'text-[9px] font-mono transition-colors duration-500',
                    isActive ? 'text-[rgba(59,130,246,0.6)]' : 'text-[rgba(100,116,139,0.5)]'
                  )}>
                    {step.tag}
                  </span>

                  {/* Icon */}
                  <step.icon
                    className={cn(
                      'w-5 h-5 transition-all duration-500',
                      isActive ? 'text-[#3b82f6]' : 'text-[var(--text-muted)]'
                    )}
                    style={isActive ? { filter: 'drop-shadow(0 0 6px rgba(59,130,246,0.6))' } : {}}
                  />

                  {/* Label */}
                  <span className={cn(
                    'text-[9px] font-mono whitespace-nowrap transition-colors duration-500',
                    isActive ? 'text-[#93c5fd]' : 'text-[var(--text-muted)]'
                  )}>
                    {step.label}
                  </span>
                </div>

                {/* Connector arrow */}
                {!isLast && (
                  <div className={cn(
                    'flex items-center transition-all duration-500 mx-1',
                    i < activeIndex ? 'text-[#3b82f6] opacity-80' : 'text-[var(--border-subtle)] opacity-50'
                  )}>
                    <svg width="20" height="10" viewBox="0 0 20 10" fill="none">
                      <path d="M0 5h16M12 1l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
