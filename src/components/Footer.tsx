import React from 'react';
import { Crosshair, ShieldCheck } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="bg-[#03060c] border-t border-slate-800 py-12 font-mono text-xs text-slate-500">
      <div className="max-w-7xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-6">
        <div className="flex items-center gap-2.5">
          <Crosshair className="w-4 h-4 text-cyan-400" />
          <span className="text-white font-bold tracking-wider">ARCHIS</span>
          <span>| Team INCEPTION | Smart India Hackathon 2026</span>
        </div>

        <div className="flex items-center gap-4 text-[11px]">
          <span>Problem Statement: SIH26169</span>
          <span>•</span>
          <span className="text-emerald-400 flex items-center gap-1">
            <ShieldCheck className="w-3.5 h-3.5" /> 100% Annexure Compliant
          </span>
        </div>
      </div>
    </footer>
  );
};
