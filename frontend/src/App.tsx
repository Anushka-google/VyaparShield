import React, { useState } from 'react';
import { 
  ShieldCheck, 
  ReceiptIndianRupee, 
  Activity, 
  CheckSquare, 
  Lock, 
  FileText, 
  Bell, 
  RefreshCw 
} from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState<'finance' | 'incidents' | 'approvals' | 'security'>('finance');

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 font-sans">
      {/* Sidebar Navigation */}
      <aside className="w-64 border-r border-slate-800 bg-slate-900/60 flex flex-col justify-between">
        <div>
          {/* Brand Logo & Header */}
          <div className="p-6 border-b border-slate-800 flex items-center space-x-3">
            <div className="p-2 bg-indigo-600 rounded-lg text-white">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <h1 className="font-bold text-lg tracking-tight text-white">NexusOps AI</h1>
              <span className="text-xs text-indigo-400 font-medium">Enterprise V1.0</span>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="p-4 space-y-1">
            <button
              onClick={() => setActiveTab('finance')}
              className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'finance'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <ReceiptIndianRupee className="w-5 h-5" />
              <span>VyaparShield (Finance)</span>
            </button>

            <button
              onClick={() => setActiveTab('incidents')}
              className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'incidents'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Activity className="w-5 h-5" />
              <span>AegisOps (Incidents)</span>
            </button>

            <button
              onClick={() => setActiveTab('approvals')}
              className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'approvals'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <CheckSquare className="w-5 h-5" />
              <div className="flex-1 flex justify-between items-center">
                <span>Agent Approvals</span>
                <span className="bg-amber-500/20 text-amber-400 text-xs px-2 py-0.5 rounded-full font-semibold">2</span>
              </div>
            </button>

            <button
              onClick={() => setActiveTab('security')}
              className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'security'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Lock className="w-5 h-5" />
              <span>AgentGuard / Policies</span>
            </button>
          </nav>
        </div>

        {/* User & Tenant Info */}
        <div className="p-4 border-t border-slate-800 bg-slate-900/40">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Active Tenant</div>
          <div className="text-sm font-medium text-slate-200 truncate">Acme Textiles MSME</div>
          <div className="text-xs text-slate-500 font-mono truncate">GSTIN: 27AAAAA0000A1Z5</div>
          <div className="mt-3 inline-block px-2 py-0.5 bg-emerald-500/10 text-emerald-400 text-xs rounded border border-emerald-500/20 font-medium">
            Role: Business Owner
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Top Header */}
        <header className="h-16 border-b border-slate-800 bg-slate-900/40 px-8 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <span className="text-sm text-slate-400">Environment:</span>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
              Development (v1.0.0-dev)
            </span>
          </div>

          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2 text-xs text-slate-400 bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-700">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span>Backend API: Online</span>
            </div>
            <button className="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800">
              <Bell className="w-5 h-5" />
            </button>
          </div>
        </header>

        {/* Dashboard Body */}
        <div className="flex-1 overflow-y-auto p-8 space-y-8">
          {/* Welcome Banner */}
          <div className="bg-gradient-to-r from-indigo-900/40 to-slate-900 border border-indigo-500/20 rounded-2xl p-6">
            <h2 className="text-2xl font-bold text-white mb-1">NexusOps Command Center</h2>
            <p className="text-slate-400 text-sm">
              VyaparShield MSME Invoice-to-Cash, AegisOps SRE Incident Response, and AgentGuard Policy Enforcement.
            </p>
          </div>

          {/* Metric Overview Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-sm">
              <div className="flex justify-between items-start mb-2">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total Receivables</span>
                <ReceiptIndianRupee className="w-4 h-4 text-emerald-400" />
              </div>
              <div className="text-2xl font-bold text-white tracking-tight">₹ 14,82,500</div>
              <span className="text-xs text-amber-400 font-medium">₹ 3,40,000 overdue (&gt;30 days)</span>
            </div>

            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-sm">
              <div className="flex justify-between items-start mb-2">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Reconciled (MTD)</span>
                <CheckSquare className="w-4 h-4 text-indigo-400" />
              </div>
              <div className="text-2xl font-bold text-white tracking-tight">₹ 8,95,000</div>
              <span className="text-xs text-emerald-400 font-medium">96.4% auto-match rate</span>
            </div>

            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-sm">
              <div className="flex justify-between items-start mb-2">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Pending Approvals</span>
                <Bell className="w-4 h-4 text-amber-400" />
              </div>
              <div className="text-2xl font-bold text-amber-400 tracking-tight">2 Actions</div>
              <span className="text-xs text-slate-400 font-medium">1 Payment reminder, 1 Mitigation</span>
            </div>

            <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-sm">
              <div className="flex justify-between items-start mb-2">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Active Incidents</span>
                <Activity className="w-4 h-4 text-rose-400" />
              </div>
              <div className="text-2xl font-bold text-white tracking-tight">0 Critical</div>
              <span className="text-xs text-emerald-400 font-medium">All telemetry healthy</span>
            </div>
          </div>

          {/* Finance Dashboard View (Phase 1, Phase 2, Phase 3) */}
          {activeTab === 'finance' && (
            <div className="space-y-8">
              
              {/* Quick Link Banner to Live Backend Dashboard */}
              <div className="bg-gradient-to-r from-indigo-950 via-slate-900 to-indigo-900/60 border border-indigo-500/30 rounded-2xl p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-xl">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="px-2.5 py-0.5 rounded text-xs font-bold uppercase tracking-wider bg-indigo-500/20 text-indigo-300 border border-indigo-500/40">
                      Live Command Center
                    </span>
                    <span className="text-xs text-slate-400">All 34 Features Active</span>
                  </div>
                  <h3 className="text-lg font-bold text-white">Full-Screen Interactive Financial Dashboard Available</h3>
                  <p className="text-slate-400 text-xs mt-0.5">
                    View real-time Chart.js interactive graphs, trigger anomaly scans, upload invoice PDFs, and inspect live ML predictions.
                  </p>
                </div>
                <a
                  href="http://127.0.0.1:8000/dashboard"
                  target="_blank"
                  rel="noreferrer"
                  className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl transition shadow-lg shadow-indigo-600/30 flex items-center gap-2 whitespace-nowrap"
                >
                  <Activity className="w-4 h-4" />
                  Launch Live Dashboard (Port 8000)
                </a>
              </div>

              {/* Grid 1: Receivables Aging & Cash Flow Projections */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                
                {/* Receivables Aging Buckets */}
                <div className="border border-slate-800 rounded-2xl p-6 bg-slate-900/60 space-y-4">
                  <div className="flex justify-between items-center">
                    <div>
                      <h3 className="font-bold text-white flex items-center gap-2">
                        <ReceiptIndianRupee className="w-5 h-5 text-indigo-400" />
                        Receivables Aging Buckets (Phase 3)
                      </h3>
                      <p className="text-xs text-slate-400">Deterministic SQL Aging: Current vs 1-30, 31-60, 61-90, 90+ Days</p>
                    </div>
                    <span className="text-xs font-mono font-bold text-slate-300 bg-slate-800 px-2.5 py-1 rounded border border-slate-700">
                      Total: ₹ 14,82,500
                    </span>
                  </div>

                  <div className="space-y-3">
                    {[
                      { label: 'Current (Not Due)', amount: '₹ 8,42,500', count: 18, pct: '57%', color: 'bg-indigo-500' },
                      { label: '1 - 30 Days Overdue', amount: '₹ 3,00,000', count: 6, pct: '20%', color: 'bg-amber-500' },
                      { label: '31 - 60 Days Overdue', amount: '₹ 1,80,000', count: 3, pct: '12%', color: 'bg-orange-500' },
                      { label: '61 - 90 Days Overdue', amount: '₹ 1,10,000', count: 2, pct: '7%', color: 'bg-rose-500' },
                      { label: '90+ Days Overdue', amount: '₹ 50,000', count: 1, pct: '4%', color: 'bg-red-700' },
                    ].map((b, idx) => (
                      <div key={idx} className="space-y-1">
                        <div className="flex justify-between text-xs">
                          <span className="font-medium text-slate-300">{b.label}</span>
                          <span className="font-mono text-slate-200">{b.amount} <span className="text-slate-500">({b.count} inv)</span></span>
                        </div>
                        <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                          <div className={`h-full ${b.color}`} style={{ width: b.pct }}></div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* 30-Day Cash Flow Multi-Scenario Forecast */}
                <div className="border border-slate-800 rounded-2xl p-6 bg-slate-900/60 space-y-4">
                  <div className="flex justify-between items-center">
                    <div>
                      <h3 className="font-bold text-white flex items-center gap-2">
                        <Activity className="w-5 h-5 text-emerald-400" />
                        30-Day Cash Flow Scenarios (Phase 3)
                      </h3>
                      <p className="text-xs text-slate-400">Risk-Adjusted Collections vs Scheduled Operating Obligations</p>
                    </div>
                    <div className="flex gap-1 text-[11px] font-semibold">
                      <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">Best</span>
                      <span className="px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">Base</span>
                      <span className="px-2 py-0.5 rounded bg-rose-500/20 text-rose-400 border border-rose-500/30">Worst</span>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-3 text-center">
                    <div className="p-3 bg-slate-950/60 rounded-xl border border-slate-800">
                      <div className="text-[11px] text-slate-400">Best Case</div>
                      <div className="text-sm font-bold text-emerald-400 mt-1">₹ +4,82,000</div>
                      <div className="text-[10px] text-slate-500">100% on-time</div>
                    </div>
                    <div className="p-3 bg-slate-950/60 rounded-xl border border-slate-800">
                      <div className="text-[11px] text-slate-400">Base Case</div>
                      <div className="text-sm font-bold text-indigo-400 mt-1">₹ +2,45,000</div>
                      <div className="text-[10px] text-slate-500">Risk-weighted</div>
                    </div>
                    <div className="p-3 bg-slate-950/60 rounded-xl border border-slate-800">
                      <div className="text-[11px] text-slate-400">Worst Case</div>
                      <div className="text-sm font-bold text-rose-400 mt-1">₹ -68,000</div>
                      <div className="text-[10px] text-slate-500">+45d delay</div>
                    </div>
                  </div>

                  <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800 text-xs text-slate-300 space-y-1">
                    <div className="flex justify-between">
                      <span className="text-slate-400">Uncertainty Bounds (80% / 95%):</span>
                      <span className="font-mono text-indigo-300">± ₹ 42,500</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Benchmark Model Error (MAE):</span>
                      <span className="font-mono text-emerald-400">₹ 1,850 (vs ₹ 2,500 Naive)</span>
                    </div>
                  </div>
                </div>

              </div>

              {/* Grid 2: Overdue Risk Predictions & Anomaly Triage */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

                {/* Overdue Risk Evaluation Table */}
                <div className="border border-slate-800 rounded-2xl p-6 bg-slate-900/60 space-y-4">
                  <div className="flex justify-between items-center">
                    <div>
                      <h3 className="font-bold text-white flex items-center gap-2">
                        <Lock className="w-5 h-5 text-rose-400" />
                        Predicted Overdue Risk (Phase 3)
                      </h3>
                      <p className="text-xs text-slate-400">Scikit-Learn ML Model / Chronological Holdout</p>
                    </div>
                    <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30">
                      3 High Risk
                    </span>
                  </div>

                  <div className="overflow-x-auto rounded-lg border border-slate-800">
                    <table className="w-full text-left text-xs text-slate-300">
                      <thead className="bg-slate-950 text-slate-400 uppercase tracking-wider border-b border-slate-800">
                        <tr>
                          <th className="p-2.5">Invoice #</th>
                          <th className="p-2.5">Customer</th>
                          <th className="p-2.5">Balance</th>
                          <th className="p-2.5">Risk Score</th>
                          <th className="p-2.5">Key Factor</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 font-mono">
                        <tr className="hover:bg-slate-800/40">
                          <td className="p-2.5 text-white">INV-2026-901</td>
                          <td className="p-2.5 font-sans">Slow Payer Ltd</td>
                          <td className="p-2.5 text-rose-400">₹ 2,36,000</td>
                          <td className="p-2.5"><span className="px-2 py-0.5 rounded text-[10px] bg-rose-500/20 text-rose-400 border border-rose-500/30">92% CRITICAL</span></td>
                          <td className="p-2.5 font-sans text-slate-400">ALREADY_OVERDUE (34d)</td>
                        </tr>
                        <tr className="hover:bg-slate-800/40">
                          <td className="p-2.5 text-white">INV-2026-880</td>
                          <td className="p-2.5 font-sans">Delta Traders</td>
                          <td className="p-2.5 text-amber-400">₹ 1,18,000</td>
                          <td className="p-2.5"><span className="px-2 py-0.5 rounded text-[10px] bg-amber-500/20 text-amber-400 border border-amber-500/30">68% HIGH</span></td>
                          <td className="p-2.5 font-sans text-slate-400">HIGH_LATE_RATIO (75%)</td>
                        </tr>
                        <tr className="hover:bg-slate-800/40">
                          <td className="p-2.5 text-white">INV-2026-101</td>
                          <td className="p-2.5 font-sans">Delhi Retail Mart</td>
                          <td className="p-2.5 text-emerald-400">₹ 11,800</td>
                          <td className="p-2.5"><span className="px-2 py-0.5 rounded text-[10px] bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">12% LOW</span></td>
                          <td className="p-2.5 font-sans text-slate-400">RELIABLE_PAYER</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Anomaly Triage Feed */}
                <div className="border border-slate-800 rounded-2xl p-6 bg-slate-900/60 space-y-4">
                  <div className="flex justify-between items-center">
                    <div>
                      <h3 className="font-bold text-white flex items-center gap-2">
                        <Bell className="w-5 h-5 text-amber-400" />
                        Anomaly Triage Queue (Phase 3)
                      </h3>
                      <p className="text-xs text-slate-400">Deterministic Rules + IsolationForest ML Outlier Scoring</p>
                    </div>
                    <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                      Top-K Throttled
                    </span>
                  </div>

                  <div className="space-y-3">
                    <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-1.5">
                      <div className="flex justify-between items-start">
                        <div className="flex items-center gap-1.5">
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-rose-500/20 text-rose-400 border border-rose-500/30">HIGH</span>
                          <span className="font-mono text-xs font-bold text-white">ANOM-01</span>
                        </div>
                        <span className="text-[11px] font-mono text-indigo-400">Score: 90%</span>
                      </div>
                      <p className="text-xs text-slate-300">Rapid identical billing amount ₹ 5,000 issued to same customer within 24 hours.</p>
                      <div className="flex justify-between items-center pt-1 text-[11px]">
                        <span className="text-slate-400">Status: <strong className="text-amber-400">Open</strong></span>
                        <div className="flex gap-1">
                          <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300">Expected</span>
                          <span className="px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">Suspicious</span>
                        </div>
                      </div>
                    </div>

                    <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-1.5">
                      <div className="flex justify-between items-start">
                        <div className="flex items-center gap-1.5">
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30">MEDIUM</span>
                          <span className="font-mono text-xs font-bold text-white">ANOM-02</span>
                        </div>
                        <span className="text-[11px] font-mono text-indigo-400">Score: 78%</span>
                      </div>
                      <p className="text-xs text-slate-300">Invoice amount ₹ 15,00,000 is 4.2 standard deviations above customer historical mean.</p>
                      <div className="flex justify-between items-center pt-1 text-[11px]">
                        <span className="text-slate-400">Status: <strong className="text-amber-400">Open</strong></span>
                        <div className="flex gap-1">
                          <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300">Expected</span>
                          <span className="px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">Suspicious</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

              </div>

            </div>
          )}

          {/* Incidents Placeholder View */}
          {activeTab === 'incidents' && (
            <div className="border border-slate-800 rounded-xl p-8 bg-slate-900/40 text-center space-y-3">
              <Activity className="w-8 h-8 text-rose-400 mx-auto" />
              <h3 className="text-lg font-bold text-white">AegisOps Incident Response</h3>
              <p className="text-slate-400 text-xs max-w-md mx-auto">
                Automated telemetry ingestion, Prometheus metrics, and SRE incident mitigation playbooks.
              </p>
            </div>
          )}

          {/* Approvals Placeholder View */}
          {activeTab === 'approvals' && (
            <div className="border border-slate-800 rounded-xl p-8 bg-slate-900/40 text-center space-y-3">
              <CheckSquare className="w-8 h-8 text-amber-400 mx-auto" />
              <h3 className="text-lg font-bold text-white">AgentGuard Human Approval Gates</h3>
              <p className="text-slate-400 text-xs max-w-md mx-auto">
                Pending high-impact autonomous actions (payment reminders dispatch, cloud mitigations) awaiting human confirmation.
              </p>
            </div>
          )}

          {/* Security Placeholder View */}
          {activeTab === 'security' && (
            <div className="border border-slate-800 rounded-xl p-8 bg-slate-900/40 text-center space-y-3">
              <Lock className="w-8 h-8 text-indigo-400 mx-auto" />
              <h3 className="text-lg font-bold text-white">AgentGuard Policy Enforcement</h3>
              <p className="text-slate-400 text-xs max-w-md mx-auto">
                Deny-by-default execution sandboxes, tool budget restrictions, and immutable audit logs.
              </p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
