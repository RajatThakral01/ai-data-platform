"use client";

import React from 'react';
import { useStore } from '@/lib/store';
import { 
  BarChart2, 
  Wand2, 
  BrainCircuit, 
  Lightbulb, 
  MessageSquareText, 
  FileText,
  Database
} from 'lucide-react';
import Link from 'next/link';

export default function DashboardOverview() {
  const { filename, rowCount, columns } = useStore();

  const quickActions = [
    { 
      title: 'Smart EDA', 
      desc: 'Deep exploratory analysis and statistics', 
      icon: BarChart2, 
      href: '/dashboard/eda',
      color: 'var(--accent-cyan)' 
    },
    { 
      title: 'Data Insights', 
      desc: 'BI Context and Auto-Charts', 
      icon: Lightbulb, 
      href: '/dashboard/insights',
      color: 'var(--accent-purple)' 
    },
    { 
      title: 'ML Recommender', 
      desc: 'Train predictive algorithms', 
      icon: BrainCircuit, 
      href: '/dashboard/ml',
      color: 'var(--accent-green)' 
    },
    { 
      title: 'Data Cleaning', 
      desc: 'Impute missing values and encode', 
      icon: Wand2, 
      href: '/dashboard/cleaning',
      color: 'var(--accent-orange)' 
    },
    { 
      title: 'NL Query', 
      desc: 'Ask questions in plain English', 
      icon: MessageSquareText, 
      href: '/dashboard/query',
      color: '#ff00ff' 
    },
    { 
      title: 'Generate Report', 
      desc: 'Export analysis to PDF', 
      icon: FileText, 
      href: '/dashboard/report',
      color: '#ffff00' 
    },
  ];

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-[var(--text-primary)] mb-2">Command Center</h1>
        <p className="text-[var(--text-muted)]">
          Session Active • <span className="font-mono text-[var(--accent-cyan)]">{filename}</span> loaded successfully.
        </p>
      </div>

      {/* Dataset Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="data-card p-6 border-l-4 border-l-[var(--accent-cyan)]">
          <h3 className="text-sm font-medium text-[var(--text-muted)] uppercase tracking-wider mb-1">Rows</h3>
          <div className="text-3xl font-bold font-mono text-[var(--text-primary)]">{rowCount.toLocaleString()}</div>
        </div>
        <div className="data-card p-6 border-l-4 border-l-[var(--accent-purple)]">
          <h3 className="text-sm font-medium text-[var(--text-muted)] uppercase tracking-wider mb-1">Columns</h3>
          <div className="text-3xl font-bold font-mono text-[var(--text-primary)]">{columns.length}</div>
        </div>
        <div className="data-card p-6 border-l-4 border-l-[var(--accent-green)]">
          <h3 className="text-sm font-medium text-[var(--text-muted)] uppercase tracking-wider mb-1">Memory Size</h3>
          <div className="text-3xl font-bold font-mono text-[var(--text-primary)]">~{(rowCount * columns.length * 8 / 1024 / 1024).toFixed(2)} MB</div>
        </div>
      </div>

      {/* Quick Actions Grid */}
      <div>
        <h2 className="text-xl font-bold text-[var(--text-primary)] mb-4">Select Analysis Module</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {quickActions.map((action) => (
            <Link key={action.title} href={action.href}>
              <div className="data-card p-6 h-full flex items-start gap-4 cursor-pointer group hover:-translate-y-1 transition-transform duration-300">
                <div 
                  className="p-3 rounded-lg shrink-0" 
                  style={{ backgroundColor: `${action.color}15`, color: action.color }}
                >
                  <action.icon className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="font-bold text-[var(--text-primary)] group-hover:text-[var(--accent-cyan)] transition-colors">
                    {action.title}
                  </h3>
                  <p className="text-sm text-[var(--text-muted)] mt-1">
                    {action.desc}
                  </p>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* Columns Preview */}
      <div className="data-card p-6 overflow-hidden">
        <h2 className="text-xl font-bold text-[var(--text-primary)] mb-4 flex items-center gap-2">
          <Database className="w-5 h-5 text-[var(--accent-cyan)]" /> Schema Preview
        </h2>
        <div className="flex flex-wrap gap-2">
          {columns.map(col => (
            <div key={col} className="px-3 py-1 bg-black/40 border border-[var(--border-subtle)] rounded font-mono text-sm text-[var(--text-primary)]">
              {col}
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}
