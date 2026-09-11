import React from 'react';
import { Radio, Crosshair, Download, ExternalLink, ShieldCheck, Activity } from 'lucide-react';

export const Navbar: React.FC = () => {
  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-[#050811]/80 backdrop-blur-md border-b border-cyan-500/20">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center space-x-3">
          <div className="w-9 h-9 rounded-lg bg-cyan-500/10 border border-cyan-400/40 flex items-center justify-center glow-box-cyan">
            <Crosshair className="w-5 h-5 text-cyan-400" />
          </div>
          <div>
            <span className="text-xl font-bold tracking-wider text-white font-mono flex items-center gap-2">
              ARCHIS <span className="text-xs px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 font-sans border border-cyan-500/30">SIH26169</span>
            </span>
            <p className="text-[10px] text-slate-400 tracking-wider uppercase font-mono">FSOC Alignment Digital Twin</p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="hidden md:flex items-center space-x-8 text-sm font-mono text-slate-300">
          <a href="#simulator" className="hover:text-cyan-400 transition-colors flex items-center gap-1.5">
            <Activity className="w-4 h-4 text-cyan-400" /> Live Simulator
          </a>
          <a href="#architecture" className="hover:text-cyan-400 transition-colors">
            5-Layer Architecture
          </a>
          <a href="#benchmark" className="hover:text-cyan-400 transition-colors">
            Benchmark-2 (.mp4)
          </a>
          <a href="#compliance" className="hover:text-cyan-400 transition-colors flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-emerald-400" /> SIH Annexure
          </a>
        </nav>

        {/* CTA */}
        <div className="flex items-center space-x-3">
          <a
            href="#downloads"
            className="px-4 py-2 rounded-md bg-cyan-500/15 hover:bg-cyan-500/25 border border-cyan-400/50 text-cyan-300 text-xs font-mono font-bold tracking-wider transition-all flex items-center gap-2 glow-box-cyan"
          >
            <Download className="w-3.5 h-3.5" /> Desktop App (v1.0)
          </a>
        </div>
      </div>
    </header>
  );
};
