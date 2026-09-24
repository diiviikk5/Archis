import React from 'react';
import { Video, CheckCircle, Database } from 'lucide-react';

export const BenchmarkSection: React.FC = () => {
  return (
    <section id="benchmark" className="py-20 bg-[#070b16] border-t border-cyan-500/20">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center mb-16">
          <span className="text-xs font-mono px-3 py-1 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-300">
            30% OF TOTAL SCORE
          </span>
          <h2 className="text-3xl sm:text-4xl font-bold font-mono text-white mt-3 mb-2">
            Benchmark Performance-2: Source Abstraction
          </h2>
          <p className="text-slate-400 max-w-2xl mx-auto text-sm">
            The same immutable frame contract drives reproducible simulation and native-resolution organizer video, with optional CSV/JSON truth sidecars.
          </p>
        </div>

        {/* 2-Column Comparison */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-center max-w-5xl mx-auto">
          {/* Card 1: The Abstraction Contract */}
          <div className="bg-slate-900/80 border border-cyan-500/30 p-6 rounded-xl font-mono text-xs space-y-4">
            <div className="flex items-center gap-2 text-cyan-400 font-bold text-sm">
              <Video className="w-4 h-4" /> VideoSourceProvider Interface
            </div>
            <p className="text-slate-300 font-sans text-sm leading-relaxed">
              Standardizes the byte buffer contract. The AI PAT engine consumes identical monochrome timestamped frames regardless of input origin:
            </p>

            <div className="space-y-2">
              <div className="p-3 rounded bg-slate-950/80 border border-slate-700 flex items-start gap-3">
                <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                <div>
                  <span className="text-white font-bold">SimulatedCameraSource</span>
                  <p className="text-slate-400 text-[11px] font-sans">
                    Pulls frames from the live 3D synthetic canvas with closed-loop gimbal re-aiming.
                  </p>
                </div>
              </div>

              <div className="p-3 rounded bg-slate-950/80 border border-emerald-500/40 flex items-start gap-3">
                <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                <div>
                  <span className="text-white font-bold">FileVideoSource (Benchmark-2 Ready)</span>
                  <p className="text-slate-400 text-[11px] font-sans">
                    Ingests organizer .mp4 video files directly at 30 FPS, scoring centroid error and RMSE against ground truth.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Card 2: Rehearsed Benchmark-2 Scorecard */}
          <div className="bg-slate-900/80 border border-emerald-500/30 p-6 rounded-xl font-mono text-xs space-y-4">
            <div className="flex items-center gap-2 text-emerald-400 font-bold text-sm">
              <Database className="w-4 h-4" /> Rehearsed Scoring Validation
            </div>
            <p className="text-slate-300 font-sans text-sm leading-relaxed">
              Fifteen 60-second runs (five scenarios, seeds 26169-26171) on the development machine:
            </p>

            <div className="space-y-2.5">
              <div className="flex justify-between py-1.5 border-b border-slate-800">
                <span className="text-slate-400">Centroid RMSE:</span>
                <span className="text-emerald-300 font-bold">0.02-0.26 px</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-800">
                <span className="text-slate-400">Pointing RMSE:</span>
                <span className="text-amber-300 font-bold">1.00-13.15 px</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-800">
                <span className="text-slate-400">Worst Target Loss:</span>
                <span className="text-emerald-300 font-bold">0.50% (Spec &lt; 5%)</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-800">
                <span className="text-slate-400">Measured Throughput:</span>
                <span className="text-emerald-300 font-bold">75-333 FPS (Spec &ge; 20)</span>
              </div>
              <div className="flex justify-between py-1.5">
                <span className="text-slate-400">Strict Scenario Gate:</span>
                <span className="text-amber-300 font-bold">4/5 pass; jitter needs tuning</span>
              </div>
            </div>
            <p className="text-[11px] leading-relaxed text-slate-400 font-sans">
              Platform jitter kept centroid accuracy below 0.04 px but produced 12.99-13.15 px pointing RMSE, above the strict 10 px gate. Results are reproducible evidence, not a guarantee for unseen video.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
};
