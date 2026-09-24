import React from 'react';
import { PackageCheck, Terminal, FileCode, Check } from 'lucide-react';

export const DownloadsSection: React.FC = () => {
  return (
    <section id="downloads" className="py-20 bg-[#050811] border-t border-cyan-500/20">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center mb-16">
          <span className="text-xs font-mono px-3 py-1 rounded bg-cyan-500/10 border border-cyan-500/30 text-cyan-300">
            DEPLOYMENT & RUNTIMES
          </span>
          <h2 className="text-3xl sm:text-4xl font-bold font-mono text-white mt-3 mb-2">
            Get ARCHIS Desktop & Datasets
          </h2>
          <p className="text-slate-400 max-w-2xl mx-auto text-sm">
            Reproducible Windows packages, complete Python source, and evidence generated from the same tracking engine.
          </p>
        </div>

        {/* Download Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto">
          {/* Card 1: Windows */}
          <div className="bg-slate-900/70 border border-cyan-500/30 p-6 rounded-xl flex flex-col justify-between glow-box-cyan">
            <div>
              <span className="text-xs font-mono text-cyan-400 uppercase">Windows Workstation</span>
              <h3 className="text-lg font-bold text-white font-mono mt-1 mb-2">ARCHIS Ground Station</h3>
              <p className="text-xs text-slate-400 mb-4 font-sans">
                PyQt6/Fluent ground station packaged from the tested Python 3.11 x64 environment.
              </p>
              <ul className="text-xs text-slate-300 space-y-1.5 mb-6 font-sans">
                <li className="flex items-center gap-2">
                  <Check className="w-3.5 h-3.5 text-emerald-400" /> Windows 11 x64 installer + portable ZIP
                </li>
                <li className="flex items-center gap-2">
                  <Check className="w-3.5 h-3.5 text-emerald-400" /> Drag-and-drop .mp4 Ingestion
                </li>
                <li className="flex items-center gap-2">
                  <Check className="w-3.5 h-3.5 text-emerald-400" /> One-click CSV/JSON Telemetry Export
                </li>
              </ul>
            </div>
            <div className="w-full py-2.5 rounded-lg bg-cyan-500/20 border border-cyan-400 text-cyan-300 font-bold font-mono text-xs flex items-center justify-center gap-2">
              <PackageCheck className="w-4 h-4" /> Built by Windows release workflow
            </div>
          </div>

          {/* Card 2: Python Engine Source */}
          <div className="bg-slate-900/70 border border-slate-700 p-6 rounded-xl flex flex-col justify-between">
            <div>
              <span className="text-xs font-mono text-slate-400 uppercase">Open-Source Engine</span>
              <h3 className="text-lg font-bold text-white font-mono mt-1 mb-2">Python Core Package</h3>
              <p className="text-xs text-slate-400 mb-4 font-sans">
                Full standalone Python package with OpenCV sub-pixel centroiding, EKF estimation, and benchmark runners.
              </p>
              <div className="bg-slate-950 p-3 rounded font-mono text-[11px] text-cyan-300 mb-6 border border-slate-800">
                <code>python -m pip install -e .</code><br />
                <code>archis gui</code>
              </div>
            </div>
            <div className="w-full py-2.5 rounded-lg bg-slate-800 border border-slate-600 text-white font-bold font-mono text-xs flex items-center justify-center gap-2">
              <Terminal className="w-4 h-4 text-cyan-400" /> Source tree is the canonical artifact
            </div>
          </div>

          {/* Card 3: Benchmark-2 Dataset */}
          <div className="bg-slate-900/70 border border-slate-700 p-6 rounded-xl flex flex-col justify-between">
            <div>
              <span className="text-xs font-mono text-emerald-400 uppercase">Evaluation Evidence</span>
              <h3 className="text-lg font-bold text-white font-mono mt-1 mb-2">Reports & Truth Sidecars</h3>
              <p className="text-xs text-slate-400 mb-4 font-sans">
                Per-frame CSV, machine-readable JSON, and branded HTML reports with seeds, configuration, versions, and pass/fail gates.
              </p>
              <ul className="text-xs text-slate-300 space-y-1.5 mb-6 font-sans">
                <li className="flex items-center gap-2">
                  <Check className="w-3.5 h-3.5 text-emerald-400" /> Deterministic three-seed scenario matrix
                </li>
                <li className="flex items-center gap-2">
                  <Check className="w-3.5 h-3.5 text-emerald-400" /> CSV and JSON ground-truth sidecars
                </li>
                <li className="flex items-center gap-2">
                  <Check className="w-3.5 h-3.5 text-emerald-400" /> Benchmark, compare, and stress-test CLI
                </li>
              </ul>
            </div>
            <div className="w-full py-2.5 rounded-lg bg-slate-800 border border-slate-600 text-white font-bold font-mono text-xs flex items-center justify-center gap-2">
              <FileCode className="w-4 h-4 text-emerald-400" /> docs/benchmarks/generated
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
