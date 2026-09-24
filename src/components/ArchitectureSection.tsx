import React from 'react';
import { Layers, Radio, Eye, Cpu, Gauge, RefreshCw } from 'lucide-react';

export const ArchitectureSection: React.FC = () => {
  const layers = [
    {
      num: '01',
      title: 'World & Orbit Dynamics',
      plain: 'Moves the Target',
      tech: 'SGP4/SDP4 orbital propagation, 6-DOF UAV kinematics, and OpenUSD scene graph representing satellite ephemeris.',
      icon: Radio
    },
    {
      num: '02',
      title: 'Optical Physics Layer',
      plain: 'Simulates Atmosphere',
      tech: 'Kolmogorov phase screens via 2D FFT spectral synthesis, Rytov scintillation flicker, and Koschmieder contrast extinction.',
      icon: Eye
    },
    {
      num: '03',
      title: 'Sensor & Camera Layer',
      plain: 'Captures Real Photons',
      tech: '640x480 Monochrome FPA, 4°x3° FOV (109.08 µrad/px IFOV), rolling shutter geometric skew, and Poisson shot noise.',
      icon: Gauge
    },
    {
      num: '04',
      title: 'AI PAT Engine',
      plain: 'Understands & Tracks',
      tech: 'Sub-pixel 2D Gaussian centroiding (<1.2 px) + Unscented Kalman Filter (UKF) trajectory prediction with covariance reacquisition.',
      icon: Cpu
    },
    {
      num: '05',
      title: 'Control & Gimbal Layer',
      plain: 'Steers the Actuators',
      tech: 'Cascaded position/velocity loop with velocity feedforward, second-order gimbal inertia, and 5°-10°/s slew limiter.',
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
            Engineered with Layered Disclosure: every component delivers intuitive plain-English functionality paired with aerospace-grade mathematics.
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
                Numerical Integrity Proof: Decoupled Simulation & Control Clock
              </span>
              <p className="text-slate-300 text-sm font-sans mt-1">
                Physics propagation and gimbal mechatronics execute on a deterministic <span className="text-white font-bold">50 Hz FixedUpdate tick</span>, completely decoupled from the variable GUI rendering thread (30-60 Hz). This eliminates frame-rate-dependent PID gain shifts.
              </p>
            </div>
            <div className="shrink-0 px-4 py-2 rounded bg-cyan-500/10 border border-cyan-400 text-cyan-300 font-bold text-center">
              50 Hz Deterministic
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
