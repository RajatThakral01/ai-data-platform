"use client";

import React from "react";
import { BarChart3, ExternalLink, Filter, Database, Layers } from "lucide-react";
import { useStore } from "@/lib/store";

export default function AdvancedDashboardPage() {
  const { sessionId, filename } = useStore();

  const features = [
    {
      icon: Layers,
      title: "30+ Chart Types",
      description: "Bar, line, scatter, heatmap, treemap, funnel and more",
    },
    {
      icon: Filter,
      title: "Cross-filtering",
      description: "Click any chart to filter all others instantly",
    },
    {
      icon: Database,
      title: "Connected to your data",
      description: "All your uploaded data is available in Metabase",
    },
  ];

  if (!sessionId) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-8">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-12">
            <p className="text-sm font-mono text-gray-500 mb-2">BI ANALYTICS</p>
            <h1 className="text-4xl font-bold flex items-center justify-center gap-3 mb-2">
              <BarChart3 className="w-8 h-8" style={{ color: "var(--accent-cyan)" }} />
              Advanced BI Dashboard
            </h1>
            <p className="text-gray-400">Explore your data with Metabase</p>
          </div>

          <div className="bg-slate-900/50 border border-gray-700/50 rounded-lg p-8 text-center">
            <p className="text-gray-400 mb-4">
              Please upload a dataset first to access the BI dashboard.
            </p>
            <a
              href="/dashboard/upload"
              className="inline-block px-6 py-2 rounded text-sm font-medium"
              style={{
                backgroundColor: "var(--accent-cyan)",
                color: "#000",
              }}
            >
              Upload Data
            </a>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-12">
          <p className="text-sm font-mono text-gray-500 mb-2">BI ANALYTICS</p>
          <h1 className="text-4xl font-bold flex items-center gap-3 mb-2">
            <BarChart3 className="w-8 h-8" style={{ color: "var(--accent-cyan)" }} />
            Advanced BI Dashboard
          </h1>
          <p className="text-gray-400">Explore your data with Metabase</p>
        </div>

        {/* Main Launch Button */}
        <div className="mb-12">
          <a
            href="http://localhost:3001"
            target="_blank"
            rel="noopener noreferrer"
            className="group inline-flex items-center gap-3 px-8 py-4 rounded-lg font-semibold text-lg transition-all duration-300"
            style={{
              backgroundColor: "var(--accent-cyan)",
              color: "#000",
              border: "2px solid var(--accent-cyan)",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = "transparent";
              e.currentTarget.style.color = "var(--accent-cyan)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = "var(--accent-cyan)";
              e.currentTarget.style.color = "#000";
            }}
          >
            Launch Metabase Dashboard
            <ExternalLink className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
          </a>
        </div>

        {/* Feature Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
          {features.map((feature) => {
            const IconComponent = feature.icon;
            return (
              <div
                key={feature.title}
                className="data-card group relative rounded-lg border p-6 transition-all duration-300 hover:border-gray-600/75 hover:bg-slate-800/30"
                style={{
                  backgroundColor: "var(--bg-card)",
                  borderColor: "var(--border-subtle)",
                }}
              >
                <div className="mb-4">
                  <div
                    className="w-12 h-12 rounded-lg flex items-center justify-center mb-4 group-hover:scale-110 transition-transform"
                    style={{ backgroundColor: "var(--accent-cyan)", color: "#000" }}
                  >
                    <IconComponent className="w-6 h-6" />
                  </div>
                  <h3 className="text-lg font-semibold mb-2" style={{ color: "var(--text-primary)" }}>
                    {feature.title}
                  </h3>
                </div>
                <p style={{ color: "var(--text-muted)" }}>
                  {feature.description}
                </p>
              </div>
            );
          })}
        </div>

        {/* Info Note */}
        <div
          className="rounded-lg border p-4 text-sm"
          style={{
            backgroundColor: "rgba(34, 211, 238, 0.05)",
            borderColor: "var(--accent-cyan)",
            color: "var(--text-primary)",
          }}
        >
          <p>
            <span style={{ color: "var(--accent-cyan)", fontWeight: "600" }}>💡 Pro Tip:</span>{" "}
            Metabase opens in a new tab. Your data from{" "}
            <span className="font-mono font-semibold">{filename}</span> is already available there.
          </p>
        </div>
      </div>
    </div>
  );
}
