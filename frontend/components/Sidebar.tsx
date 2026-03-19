"use client";

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  LayoutDashboard, 
  BarChart2, 
  BarChart3, 
  Wand2, 
  BrainCircuit, 
  Lightbulb, 
  MessageSquareText, 
  FileText, 
  Activity
} from 'lucide-react';
import { useStore } from '@/lib/store';
import { cn } from '@/lib/utils';

const navItems = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Smart EDA', href: '/dashboard/eda', icon: BarChart2 },
  { name: 'Data Cleaning', href: '/dashboard/cleaning', icon: Wand2 },
  { name: 'ML Recommender', href: '/dashboard/ml', icon: BrainCircuit },
  { name: 'Data Insights', href: '/dashboard/insights', icon: Lightbulb },
  { name: 'NL Query', href: '/dashboard/query', icon: MessageSquareText },
  { name: 'Report Generator', href: '/dashboard/report', icon: FileText },
  { name: 'Observatory', href: '/dashboard/observatory', icon: Activity },
  { name: 'BI Dashboard', href: '/dashboard/advanced', icon: BarChart3 },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { sessionId, filename, rowCount, columns } = useStore();

  // If no session is active, don't render the sidebar space
  if (!sessionId) {
    return null;
  }

  const truncatedFilename = filename && filename.length > 20 
    ? filename.substring(0, 20) + '...' 
    : (filename || 'dataset.csv');

  return (
    <aside className="w-64 h-screen bg-card border-r border-[var(--border-subtle)] flex flex-col justify-between hidden md:flex sticky top-0">
      <div>
        <div className="p-6 border-b border-[var(--border-subtle)] flex items-center gap-2">
          <span className="text-[var(--accent-cyan)] font-bold text-xl drop-shadow-[0_0_10px_rgba(0,212,255,0.8)]">⚡</span> 
          <h1 className="text-xl font-bold tracking-tight text-[var(--text-primary)]">
            DataPlatform
          </h1>
        </div>

        <div className="p-6 border-b border-[var(--border-subtle)]">
          <div className="text-sm font-semibold text-[var(--text-primary)] mb-1 truncate" title={filename || 'dataset'}>
            {truncatedFilename}
          </div>
          <div className="text-xs text-[var(--text-muted)] font-mono mb-3">
            {rowCount} rows × {columns.length} cols
          </div>
          <div className="flex items-center gap-2 text-xs">
            <span className="w-2 h-2 rounded-full bg-[var(--accent-green)] shadow-[0_0_8px_rgba(0,255,136,0.6)]"></span>
            <span className="text-[var(--accent-green)] font-medium tracking-wide">ACTIVE</span>
          </div>
        </div>

        <nav className="p-4 space-y-1">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link 
                key={item.name} 
                href={item.href}
                className={cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-all group relative",
                  isActive 
                    ? "text-[var(--accent-cyan)] bg-[rgba(0,212,255,0.05)]" 
                    : "text-[var(--text-muted)] hover:bg-[var(--bg-card-hover)] hover:text-[var(--text-primary)]"
                )}
              >
                {isActive && (
                  <div className="absolute left-0 top-0 bottom-0 w-1 bg-[var(--accent-cyan)] rounded-r shadow-[0_0_10px_rgba(0,212,255,0.5)]"></div>
                )}
                <item.icon className={cn("w-[18px] h-[18px]", isActive ? "text-[var(--accent-cyan)]" : "text-[var(--text-muted)] group-hover:text-[var(--text-primary)]")} />
                {item.name}
              </Link>
            )
          })}
        </nav>
      </div>

      <div className="p-6 border-t border-[var(--border-subtle)] text-xs">
        <div className="flex items-center gap-2 mb-2">
          <span className="w-2 h-2 rounded-full bg-[var(--accent-green)] shadow-[0_0_5px_rgba(0,255,136,0.5)]"></span>
          <span className="text-[var(--text-muted)] font-medium">Groq Active</span>
        </div>
        <div className="text-[var(--text-muted)] font-mono opacity-50">v2.0.0</div>
      </div>
    </aside>
  );
}
