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

          {/* Module Placeholder Status */}
          <div className="border border-slate-800 rounded-xl p-8 bg-slate-900/40 text-center space-y-4">
            <div className="inline-flex p-3 bg-indigo-500/10 text-indigo-400 rounded-full border border-indigo-500/20">
              <FileText className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-semibold text-white">Foundation Ready for Phase A1</h3>
            <p className="text-slate-400 text-sm max-w-md mx-auto">
              FastAPI backend, PostgreSQL schema contracts, and React navigation shell are initialized. Next up is database migrations and tenant isolation suites.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
