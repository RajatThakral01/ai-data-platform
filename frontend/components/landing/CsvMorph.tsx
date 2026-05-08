'use client';

import { useEffect, useRef, useState } from 'react';
import { cn } from '@/lib/utils';

type Phase = 'csv' | 'morphing' | 'dashboard' | 'resetting';

const CSV_CONTENT = `CustomerID  Churn  MonthlyCharges  Contract          Tenure
─────────────────────────────────────────────────────────────
7590-VHVEG  Yes    89.10           Month-to-month    1
3668-QPYBK  No     29.85           Two year          72
9237-HQITU  Yes    74.40           Month-to-month    5
1022-KDLEM  No     56.15           One year          45
8841-NBROU  Yes    105.65          Month-to-month    2
4419-LBROK  No     42.30           Two year          61
5575-GNVDE  Yes    67.85           Month-to-month    7
1452-KIOVK  No     20.05           Two year          51`;

// Phases: csv(1.2s) → morphing(3s) → dashboard(2.5s) → resetting(0.5s) → loop
const CYCLE_MS = 7200;

/* ── Mini SVG Donut ─────────────────────────────────── */
function DonutChart({ pct = 26.5 }: { pct?: number }) {
  const r = 36;
  const circ = 2 * Math.PI * r;
  const dash = (pct / 100) * circ;
  return (
    <div className="flex flex-col items-center gap-1">
      <svg width="88" height="88" viewBox="0 0 88 88" className="drop-shadow-lg">
        <circle cx="44" cy="44" r={r} fill="none"
          stroke="rgba(59,130,246,0.12)" strokeWidth="10" />
        <circle cx="44" cy="44" r={r} fill="none"
          stroke="#3b82f6" strokeWidth="10"
          strokeDasharray={`${dash} ${circ - dash}`}
          strokeDashoffset={circ / 4}
          strokeLinecap="round"
          style={{ filter: 'drop-shadow(0 0 6px #3b82f6)' }} />
        <text x="44" y="44" textAnchor="middle" dominantBaseline="middle"
          fill="#e2e8f0" fontSize="12" fontWeight="700" fontFamily="JetBrains Mono, monospace">
          {pct}%
        </text>
        <text x="44" y="57" textAnchor="middle" dominantBaseline="middle"
          fill="#64748b" fontSize="7" fontFamily="JetBrains Mono, monospace">
          CHURN
        </text>
      </svg>
    </div>
  );
}

/* ── Mini Bar Chart ─────────────────────────────────── */
function BarChart() {
  const bars = [
    { label: 'M-M',   pct: 78, color: '#3b82f6' },
    { label: '1yr',   pct: 45, color: '#60a5fa' },
    { label: '2yr',   pct: 20, color: '#93c5fd' },
  ];
  return (
    <div className="flex flex-col gap-1 w-full">
      <div className="text-[9px] font-mono text-[#64748b] mb-1">Monthly Charges by Contract</div>
      {bars.map(b => (
        <div key={b.label} className="flex items-center gap-2">
          <div className="text-[8px] font-mono text-[#64748b] w-6 shrink-0">{b.label}</div>
          <div className="flex-1 h-3 bg-[rgba(59,130,246,0.08)] rounded-sm overflow-hidden">
            <div
              className="h-full rounded-sm transition-all duration-700"
              style={{
                width: `${b.pct}%`,
                background: b.color,
                boxShadow: `0 0 8px ${b.color}60`,
              }}
            />
          </div>
          <div className="text-[8px] font-mono text-[#60a5fa] w-6 shrink-0">{b.pct}%</div>
        </div>
      ))}
    </div>
  );
}

/* ── KPI Cards ──────────────────────────────────────── */
function KpiCards() {
  const kpis = [
    { label: 'Churn Rate',  value: '26.5%', color: '#f87171' },
    { label: 'Avg Charges', value: '$64.76', color: '#34d399' },
    { label: 'Avg Tenure',  value: '32 mo',  color: '#60a5fa' },
  ];
  return (
    <div className="flex flex-col gap-2 w-full">
      {kpis.map(k => (
        <div key={k.label}
          className="flex items-center justify-between px-3 py-2 rounded-md"
          style={{ background: 'rgba(15,15,26,0.8)', border: '1px solid rgba(59,130,246,0.15)' }}
        >
          <span className="text-[9px] font-mono text-[#64748b]">{k.label}</span>
          <span className="text-xs font-bold font-mono" style={{ color: k.color }}>{k.value}</span>
        </div>
      ))}
    </div>
  );
}

/* ── Main Component ─────────────────────────────────── */
export default function CsvMorph() {
  const [phase, setPhase] = useState<Phase>('csv');
  const [dashboardVisible, setDashboardVisible] = useState(false);
  const [csvOpacity, setCsvOpacity] = useState(1);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearTimer = () => {
    if (timerRef.current) clearTimeout(timerRef.current);
  };

  const runCycle = () => {
    // csv phase: 1200ms
    setPhase('csv');
    setDashboardVisible(false);
    setCsvOpacity(1);

    timerRef.current = setTimeout(() => {
      // start morphing
      setPhase('morphing');
      // fade CSV out gradually
      setTimeout(() => setCsvOpacity(0), 200);
      // reveal dashboard halfway through beam
      setTimeout(() => setDashboardVisible(true), 1400);

      timerRef.current = setTimeout(() => {
        // hold dashboard
        setPhase('dashboard');

        timerRef.current = setTimeout(() => {
          // reset
          setPhase('resetting');
          setDashboardVisible(false);
          setCsvOpacity(0);

          timerRef.current = setTimeout(() => {
            runCycle();
          }, 500);
        }, 2500); // dashboard hold
      }, 3000); // morphing duration
    }, 1200); // csv display
  };

  useEffect(() => {
    runCycle();
    return clearTimer;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="relative w-full max-w-4xl mx-auto animate-float"
      style={{ borderRadius: '16px', overflow: 'hidden' }}>

      {/* Outer frame */}
      <div className="relative rounded-2xl overflow-hidden"
        style={{
          background: '#080810',
          border: '1px solid rgba(59,130,246,0.2)',
          boxShadow: '0 0 60px rgba(59,130,246,0.08), 0 32px 64px rgba(0,0,0,0.6)',
        }}>

        {/* Title bar */}
        <div className="flex items-center gap-2 px-4 py-2.5 border-b"
          style={{ borderColor: 'rgba(59,130,246,0.1)', background: '#0a0a14' }}>
          <div className="w-3 h-3 rounded-full bg-[#ff5f57]" />
          <div className="w-3 h-3 rounded-full bg-[#febc2e]" />
          <div className="w-3 h-3 rounded-full bg-[#28c840]" />
          <span className="ml-3 text-[10px] font-mono text-[#64748b]">
            {phase === 'csv' || phase === 'morphing' ? 'dataset.csv' : 'coldframe_dashboard.html'}
          </span>
        </div>

        {/* Content area */}
        <div className="relative min-h-[260px] p-5 overflow-hidden">

          {/* CSV Layer */}
          <div
            className="absolute inset-0 p-5 transition-opacity duration-700"
            style={{ opacity: csvOpacity }}
          >
            <pre className="text-[10px] leading-[1.65] whitespace-pre overflow-hidden"
              style={{ fontFamily: 'JetBrains Mono, monospace', color: 'rgba(0,255,136,0.55)' }}>
              {CSV_CONTENT}
            </pre>
          </div>

          {/* Beam */}
          {phase === 'morphing' && (
            <div
              className="absolute top-0 bottom-0 pointer-events-none z-20"
              style={{
                width: '3px',
                background: 'linear-gradient(to bottom, transparent, #3b82f6, transparent)',
                boxShadow: '0 0 30px 8px rgba(59,130,246,0.5), 0 0 60px 20px rgba(59,130,246,0.2)',
                animation: 'beamSweep 3s ease-in-out forwards',
              }}
            />
          )}

          {/* Dashboard Layer */}
          <div
            className="absolute inset-0 p-5 grid grid-cols-3 gap-4 transition-opacity duration-700"
            style={{ opacity: dashboardVisible ? 1 : 0 }}
          >
            {/* Left: Donut */}
            <div className="flex flex-col items-center justify-center">
              <DonutChart pct={26.5} />
              <div className="text-[8px] font-mono text-[#64748b] mt-1 text-center">Churn Rate</div>
            </div>

            {/* Center: Bar Chart */}
            <div className="flex flex-col justify-center">
              <BarChart />
            </div>

            {/* Right: KPI Cards */}
            <div className="flex flex-col justify-center">
              <div className="text-[9px] font-mono text-[#64748b] mb-2">Key Metrics</div>
              <KpiCards />
            </div>
          </div>
        </div>

        {/* Bottom status bar */}
        <div className="flex items-center justify-between px-4 py-2 border-t"
          style={{ borderColor: 'rgba(59,130,246,0.1)', background: '#0a0a14' }}>
          <span className="text-[9px] font-mono" style={{
            color: phase === 'csv' ? 'rgba(0,255,136,0.5)' :
              phase === 'morphing' ? '#3b82f6' : 'rgba(0,255,136,0.6)',
          }}>
            {phase === 'csv' ? '● raw csv · 8 rows · 5 columns' :
              phase === 'morphing' ? '⚡ ai processing...' :
                '✓ coldframe dashboard · groq · gemini'}
          </span>
          <span className="text-[9px] font-mono text-[#64748b]">
            telecom_churn.csv
          </span>
        </div>
      </div>
    </div>
  );
}
