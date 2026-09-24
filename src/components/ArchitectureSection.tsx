import React from 'react';
import { Radio, Eye, Cpu, Gauge, RefreshCw } from 'lucide-react';

export const ArchitectureSection: React.FC = () => {
  const layers = [
    {
      num: '01',
      title: 'Scenario & World',
      plain: 'Moves the Target',
      tech: 'Versioned JSON scenarios drive a seeded fixed-step 2D world, configurable beacon trajectories, decoys, and repeatable disturbances.',
      icon: Radio
    },
    {
      num: '02',
      title: 'Disturbance Pipeline',
      plain: 'Simulates Atmosphere',
      tech: 'A defined render order applies camera motion, platform jitter, atmospheric blur and attenuation, sensor noise, then configured dropout.',
      icon: Eye
    },
    {
      num: '03',
      title: 'Sensor & Camera Layer',
      plain: 'Normalizes Every Source',
      tech: 'Immutable timestamped frame packets unify the simulator, native-resolution MP4 files, single images, and image sequences.',
      icon: Gauge
    },
    {
      num: '04',
      title: 'AI PAT Engine',
      plain: 'Understands & Tracks',
      tech: 'Full-frame MAD/DoG proposals, NanoSpot refinement, compact candidate evidence, optional CodeLock identity, and a six-state constant-acceleration Kalman filter.',
      icon: Cpu
    },
    {
      num: '05',
      title: 'Control & Gimbal Layer',
      plain: 'Steers the Actuators',
      tech: 'Explicit SEARCH→ACQUIRE→TRACK→COAST→REACQUIRE logic drives configurable PID, anti-windup, feed-forward, rate, acceleration, and travel limits.',
      icon: RefreshCw
    }
  ];

  return (
    <section id="architecture" className="py-20 bg-[#050811]">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center mb-16">
          <span className="text-xs font-mono px-3 py-1 rounded bg-cyan-500/10 border border-cyan-500/30 text-cyan-300">
            SYSTEM DESIGN & RIGOR
          </span>
          <h2 className="text-3xl sm:text-4xl font-bold font-mono text-white mt-3 mb-2">
            5-Layer Decoupled Architecture
          </h2>
          <p className="text-slate-400 max-w-2xl mx-auto text-sm">
            The simulator, algorithms, control loop, and evaluator are joined by immutable contracts so ground truth never enters detection or control.
          </p>
        </div>

        {/* Layer Cards */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-12">
          {layers.map((l) => {
            const Icon = l.icon;
            return (
              <div
                key={l.num}
                className="bg-slate-900/60 border border-slate-800 hover:border-cyan-500/50 p-5 rounded-xl transition-all hover:-translate-y-1 group"
              >
                <div className="flex items-center justify-between mb-4">
                  <span className="text-xs font-mono font-bold text-cyan-400 group-hover:text-cyan-300">
                    LAYER {l.num}
                  </span>
                  <Icon className="w-5 h-5 text-slate-500 group-hover:text-cyan-400 transition-colors" />
                </div>
                <h3 className="text-base font-bold text-white font-mono mb-1">{l.title}</h3>
                <p className="text-xs font-bold text-emerald-400 mb-3 italic">"{l.plain}"</p>
                <p className="text-xs text-slate-400 leading-relaxed font-sans">{l.tech}</p>
              </div>
            );
          })}
        </div>

        {/* Decoupled Clock Callout */}
        <div className="p-6 rounded-xl bg-slate-900/80 border border-cyan-500/30 glow-box-cyan max-w-4xl mx-auto text-left font-mono text-xs">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <span className="text-cyan-400 font-bold uppercase tracking-wider">
                Reproducibility Contract: Fixed Simulation Clock & Seeded Randomness
              </span>
              <p className="text-slate-300 text-sm font-sans mt-1">
                Each scenario records its update rate and random seed. The engine advances by that fixed step while the PyQt interface consumes immutable snapshots on a worker thread, keeping GUI timing out of the experiment.
              </p>
            </div>
            <div className="shrink-0 px-4 py-2 rounded bg-cyan-500/10 border border-cyan-400 text-cyan-300 font-bold text-center">
              30 Hz Default
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
