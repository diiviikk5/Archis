import React, { useEffect, useRef } from 'react';
import { Crosshair, Play, Download, ShieldCheck, Cpu, ArrowRight, Video } from 'lucide-react';

interface HeroSectionProps {
  onOpenSim: () => void;
}

export const HeroSection: React.FC<HeroSectionProps> = ({ onOpenSim }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Procedural animated 3D Starfield & Optical Beam
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };
    window.addEventListener('resize', handleResize);

    // Stars
    const stars = Array.from({ length: 140 }, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      radius: Math.random() * 1.5 + 0.5,
      alpha: Math.random() * 0.8 + 0.2,
      speed: Math.random() * 0.2 + 0.05
    }));

    let t = 0;

    const render = () => {
      // High-performance transparent clear for zero overdraw lag
      ctx.clearRect(0, 0, width, height);

      // Subtle tactical grid
      ctx.strokeStyle = 'rgba(0, 229, 255, 0.04)';
      ctx.lineWidth = 1;
      const gridSize = 70;
      for (let x = 0; x < width; x += gridSize) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
      }
      for (let y = 0; y < height; y += gridSize) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }

      // Subtle ambient stars
      stars.forEach((s) => {
        ctx.fillStyle = `rgba(226, 232, 240, ${s.alpha * 0.7})`;
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.radius, 0, Math.PI * 2);
        ctx.fill();
        s.y -= s.speed;
        if (s.y < 0) s.y = height;
      });

      // Target Satellite Beacon & Tracking Laser Beam
      const targetX = width * 0.62 + Math.sin(t * 0.5) * 110;
      const targetY = height * 0.36 + Math.cos(t * 0.7) * 40;
      const groundStationX = width * 0.34;
      const groundStationY = height * 0.85;

      // Outer laser bloom
      ctx.strokeStyle = 'rgba(0, 229, 255, 0.4)';
      ctx.lineWidth = 3;
      ctx.shadowColor = '#00e5ff';
      ctx.shadowBlur = 14;
      ctx.beginPath();
      ctx.moveTo(groundStationX, groundStationY);
      ctx.lineTo(targetX, targetY);
      ctx.stroke();

      // Core white laser filament
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 1.2;
      ctx.shadowBlur = 4;
      ctx.beginPath();
      ctx.moveTo(groundStationX, groundStationY);
      ctx.lineTo(targetX, targetY);
      ctx.stroke();
      ctx.shadowBlur = 0;

      // Target Crosshair / Reticle
      ctx.strokeStyle = 'rgba(16, 185, 129, 0.95)'; // Locked Green
      ctx.lineWidth = 1.5;
      const rSize = 14;
      ctx.strokeRect(targetX - rSize, targetY - rSize, rSize * 2, rSize * 2);

      // Center centroid dot
      ctx.beginPath();
      ctx.arc(targetX, targetY, 3.5, 0, Math.PI * 2);
      ctx.fillStyle = '#00e5ff';
      ctx.fill();

      // Tracking readout HUD tag
      ctx.fillStyle = 'rgba(16, 185, 129, 0.95)';
      ctx.font = '10px monospace';
      ctx.fillText(`LOCK: TRACKING | ERR: 0.78 px (85.1 µrad)`, targetX + 18, targetY - 6);

      t += 0.02;
      animId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  return (
    <div className="relative min-h-[92vh] flex items-center justify-center pt-24 pb-16 overflow-hidden">
      {/* 1. Fullscreen Background Video (Hardware Accelerated) */}
      <video
        autoPlay
        loop
        muted
        playsInline
        preload="auto"
        className="absolute inset-0 w-full h-full object-cover opacity-60 z-0 pointer-events-none transform-gpu will-change-transform"
        id="hero-video"
      >
        <source src="/hero-bg.mp4" type="video/mp4" />
      </video>

      {/* 2. Seamless Dark Vignette Overlays for Text Legibility & Contrast */}
      <div className="absolute inset-0 bg-gradient-to-b from-[#050811]/85 via-[#050811]/45 to-[#050811] z-10 pointer-events-none" />
      <div className="absolute inset-0 bg-gradient-to-r from-[#050811]/90 via-transparent to-[#050811]/90 z-10 pointer-events-none" />

      {/* 3. Transparent Tactical HUD Canvas (Overlaid on Top of Video) */}
      <canvas ref={canvasRef} className="absolute inset-0 pointer-events-none z-10" />

      {/* Tactical HUD Corner Elements */}
      <div className="absolute top-28 left-8 z-20 hidden lg:block font-mono text-[11px] text-cyan-400/70 border-l border-t border-cyan-500/30 pl-3 pt-2">
        <p>SYS: ARCHIS-OPTICS v1.0.4</p>
        <p>BORESIGHT: 109.08 µrad/px</p>
        <p>GFLAG: CAS_PID_FEEDFORWARD</p>
      </div>

      <div className="absolute top-28 right-8 z-20 hidden lg:block font-mono text-[11px] text-emerald-400/70 text-right border-r border-t border-emerald-500/30 pr-3 pt-2">
        <p>STATUS: OPTICAL LOCK ACTIVE</p>
        <p>ACQ_LATENCY: 182 ms</p>
        <p>SRC: BYTE_AGNOSTIC_MP4</p>
      </div>

      {/* Central Content */}
      <div className="relative z-20 max-w-5xl mx-auto px-6 text-center">
        {/* Category Pill */}
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-cyan-500/10 border border-cyan-400/30 text-cyan-300 text-xs font-mono mb-6 glow-box-cyan">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          SMART INDIA HACKATHON 2026 • PROBLEM ID: SIH26169
        </div>

        {/* Main Title */}
        <h1 className="text-5xl sm:text-7xl font-extrabold tracking-tight text-white mb-6 font-mono">
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-white via-cyan-200 to-cyan-400">
            ARCHIS
          </span>
        </h1>

        <p className="text-xl sm:text-2xl font-bold text-cyan-300 mb-4 max-w-3xl mx-auto font-sans tracking-wide">
          A Physically-Grounded Digital Twin for Mobile FSOC Coarse Alignment
        </p>

        {/* Plain-English Hook + Technical Disclosure */}
        <p className="text-base sm:text-lg text-slate-300 max-w-2xl mx-auto mb-10 leading-relaxed font-sans">
          Bridging the sim-to-real chasm in Free-Space Optical Communications. Validates pointing and tracking algorithms across severe turbulence using{' '}
          <span className="text-white font-semibold underline decoration-cyan-400 decoration-1 underline-offset-4">
            sub-pixel centroiding
          </span>
          ,{' '}
          <span className="text-white font-semibold underline decoration-cyan-400 decoration-1 underline-offset-4">
            predictive Kalman filtering
          </span>
          , and a source-agnostic pipeline ready for Benchmark-2.
        </p>

        {/* CTA Buttons */}
        <div className="flex flex-wrap items-center justify-center gap-4 mb-14">
          <button
            onClick={onOpenSim}
            className="px-6 py-3.5 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-bold text-sm tracking-wider font-mono flex items-center gap-2 shadow-lg shadow-cyan-500/25 transition-all glow-box-cyan transform hover:-translate-y-0.5 cursor-pointer"
          >
            <Play className="w-4 h-4 fill-current" /> LAUNCH IN-BROWSER SIMULATOR
          </button>

          <a
            href="#downloads"
            className="px-6 py-3.5 rounded-lg bg-slate-900/80 hover:bg-slate-800 border border-slate-700 hover:border-cyan-400/50 text-white font-bold text-sm tracking-wider font-mono flex items-center gap-2 transition-all"
          >
            <Download className="w-4 h-4 text-cyan-400" /> DOWNLOAD DESKTOP APP
          </a>
        </div>

        {/* Spec-Exact KPI Badges */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 max-w-4xl mx-auto text-left">
          <div className="p-3.5 rounded-lg bg-slate-900/70 border border-cyan-500/20 backdrop-blur-sm">
            <span className="text-[10px] font-mono text-cyan-400 uppercase">Sub-Pixel Error</span>
            <p className="text-lg font-bold text-white font-mono">&lt; 1.2 px</p>
            <p className="text-[11px] text-slate-400">Spec requirement: &le; 10 px</p>
          </div>

          <div className="p-3.5 rounded-lg bg-slate-900/70 border border-cyan-500/20 backdrop-blur-sm">
            <span className="text-[10px] font-mono text-cyan-400 uppercase">Angular IFOV</span>
            <p className="text-lg font-bold text-white font-mono">109.08 µrad</p>
            <p className="text-[11px] text-slate-400">4°x3° FOV @ 640x480</p>
          </div>

          <div className="p-3.5 rounded-lg bg-slate-900/70 border border-cyan-500/20 backdrop-blur-sm">
            <span className="text-[10px] font-mono text-cyan-400 uppercase">Control Loop</span>
            <p className="text-lg font-bold text-white font-mono">50 Hz Fixed</p>
            <p className="text-[11px] text-slate-400">Decoupled from render FPS</p>
          </div>

          <div className="p-3.5 rounded-lg bg-slate-900/70 border border-emerald-500/30 backdrop-blur-sm">
            <span className="text-[10px] font-mono text-emerald-400 uppercase">Benchmark-2</span>
            <p className="text-lg font-bold text-emerald-300 font-mono">100% Ready</p>
            <p className="text-[11px] text-slate-400">Direct .mp4 ingestion</p>
          </div>
        </div>
      </div>
    </div>
  );
};
