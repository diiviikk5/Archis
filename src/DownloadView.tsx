import React, { useState } from "react";
import { motion, type Variants } from "motion/react";
import {
  Circle,
  ArrowLeft,
  Download,
  Terminal,
  Check,
  Copy,
  Monitor,
  Apple,
  Cpu,
  ShieldCheck,
  ExternalLink,
  ChevronRight,
  Box,
} from "lucide-react";

interface DownloadViewProps {
  onBack: () => void;
  onOpenDocs: () => void;
}

const heroContainer: Variants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.12, delayChildren: 0.15 },
  },
};

const heroItem: Variants = {
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0, transition: { duration: 0.45 } },
};

export function DownloadView({ onBack, onOpenDocs }: DownloadViewProps) {
  const [copied, setCopied] = useState(false);
  const [selectedPlatform, setSelectedPlatform] = useState<"windows" | "macos" | "linux" | "docker">("windows");

  const installCommand = "curl -fsSL https://get.archis.network | bash";

  const handleCopy = () => {
    navigator.clipboard.writeText(installCommand);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <main className="flex min-h-screen w-full bg-black selection:bg-white/30 p-2 lg:h-screen lg:overflow-hidden lg:p-4 text-white font-sans">
      {/* LEFT COLUMN: Pure centered typography over purple shader */}
      <aside className="hidden lg:flex relative w-[46%] flex-col items-center justify-center p-12 rounded-3xl overflow-hidden shadow-2xl h-full border border-white/10">
        {/* Looping video — Pure without dark overlay */}
        <video
          autoPlay
          loop
          muted
          playsInline
          className="absolute inset-0 h-full w-full object-cover"
          src="/assets/hf_20260506_081238_406ed0e3-5d83-436e-a512-0bbff7ec5b95.mp4"
        />

        {/* In between: Just Archis and a 2-3 line description, zero boxes */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          className="relative z-10 flex flex-col items-center justify-center text-center max-w-sm px-6"
        >
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-orbitron font-bold tracking-wider text-white drop-shadow-[0_0_35px_rgba(255,255,255,0.4)]">
            Archis
          </h1>
          <p className="mt-4 text-xs sm:text-sm font-mono text-white/60 leading-relaxed max-w-xs">
            Autonomous optical alignment and orbital tracking digital twin platform.
          </p>
        </motion.div>
      </aside>

      {/* RIGHT COLUMN: Minimalist Stealth Download Hub */}
      <section className="flex-1 flex flex-col items-center justify-between py-8 px-4 sm:px-10 lg:px-12 xl:px-16 overflow-y-auto relative">
        {/* Navigation Bar */}
        <div className="w-full max-w-xl flex items-center justify-between mb-4">
          <button
            onClick={onBack}
            className="flex items-center gap-2 text-xs font-mono text-white/50 hover:text-white transition-colors duration-200 cursor-pointer"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>TERMINAL</span>
          </button>

          <button
            onClick={onOpenDocs}
            className="flex items-center gap-1.5 text-xs font-geist-pixel text-white/60 hover:text-white transition-colors duration-200 cursor-pointer border border-white/10 hover:border-white/30 px-3 py-1.5 rounded-lg bg-white/[0.02]"
          >
            <span>DOCUMENTATION</span>
            <ExternalLink className="w-3 h-3 text-white/60" />
          </button>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="w-full max-w-xl space-y-6 my-auto"
        >
          {/* Header - Minimal & Punchy with Orbitron */}
          <header className="space-y-1.5">
            <div className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded border border-white/20 bg-white/5 text-white/70 text-[10px] font-geist-pixel tracking-widest uppercase">
              RELEASE // v1.4.2
            </div>
            <h1 className="text-2xl sm:text-3xl font-orbitron font-semibold tracking-tight text-white">
              GET ARCHIS TERMINAL
            </h1>
            <p className="text-white/50 text-xs font-mono">
              High-rate optical acquisition &amp; real-time digital twin client.
            </p>
          </header>

          {/* Primary Download Card */}
          <div className="p-5 rounded-2xl bg-white/[0.03] border border-white/20 backdrop-blur-xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="space-y-1.5">
              <div className="text-[10px] font-geist-pixel text-white/50 tracking-wider uppercase">
                TARGET BUILD (WINDOWS X64)
              </div>
              <div className="text-base font-orbitron font-semibold text-white">
                Archis Terminal 1.4.2
              </div>
              <div className="text-xs text-white/40 font-mono">
                Windows 10 / 11 • 84.6 MB • SHA-256 Verified
              </div>
            </div>

            <div className="flex sm:flex-col gap-2 w-full sm:w-auto">
              <a
                href="#download-msi"
                onClick={(e) => {
                  e.preventDefault();
                  alert("Downloading Archis Terminal v1.4.2 Installer (.msi)...");
                }}
                className="flex-1 sm:flex-initial px-5 py-2.5 rounded-xl bg-white hover:bg-neutral-200 text-black font-semibold text-xs font-mono flex items-center justify-center gap-2 transition-all cursor-pointer shadow active:scale-95"
              >
                <Download className="w-3.5 h-3.5" />
                <span>DOWNLOAD .MSI</span>
              </a>
              <a
                href="#download-zip"
                onClick={(e) => {
                  e.preventDefault();
                  alert("Downloading Archis Terminal v1.4.2 Portable (.zip)...");
                }}
                className="px-4 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-white/60 hover:text-white text-[11px] font-mono text-center border border-white/10 transition-colors"
              >
                Portable .zip
              </a>
            </div>
          </div>

          {/* CLI One-Liner */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-[11px] font-geist-pixel text-white/40 uppercase tracking-wider">
              <span>CLI INSTALLER (UNIX)</span>
              <span className="text-[10px]">CURL // SH</span>
            </div>
            <div className="flex items-center justify-between p-3 rounded-xl bg-white/[0.02] border border-white/15 font-mono text-xs text-white">
              <code className="text-white/90 select-all overflow-x-auto pr-2 font-mono">
                {installCommand}
              </code>
              <button
                onClick={handleCopy}
                className="p-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-white/80 hover:text-white transition-colors cursor-pointer shrink-0"
                title="Copy command"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-white" /> : <Copy className="w-3.5 h-3.5" />}
              </button>
            </div>
          </div>

          {/* Platform Selectors Grid */}
          <div className="space-y-2.5">
            <div className="text-[11px] font-geist-pixel text-white/40 uppercase tracking-wider">
              ALL PLATFORMS
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              <PlatformTab
                active={selectedPlatform === "windows"}
                onClick={() => setSelectedPlatform("windows")}
                icon={Monitor}
                label="Windows"
                sub="x64 / ARM"
              />
              <PlatformTab
                active={selectedPlatform === "macos"}
                onClick={() => setSelectedPlatform("macos")}
                icon={Apple}
                label="macOS"
                sub="Apple / Intel"
              />
              <PlatformTab
                active={selectedPlatform === "linux"}
                onClick={() => setSelectedPlatform("linux")}
                icon={Cpu}
                label="Linux"
                sub="AppImage / Deb"
              />
              <PlatformTab
                active={selectedPlatform === "docker"}
                onClick={() => setSelectedPlatform("docker")}
                icon={Box}
                label="Docker"
                sub="Headless"
              />
            </div>

            {/* Platform Details Card - Minimal & Clean */}
            <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/10 text-xs font-mono">
              {selectedPlatform === "windows" && (
                <div className="flex items-center justify-between flex-wrap gap-2 text-white/70">
                  <span className="text-white/40">Windows 10 / 11 (64-bit)</span>
                  <div className="flex items-center gap-3">
                    <a
                      href="#msi"
                      onClick={(e) => { e.preventDefault(); alert("Downloading MSI..."); }}
                      className="text-white hover:underline underline-offset-4 font-medium"
                    >
                      Installer (.msi)
                    </a>
                    <span className="text-white/20">•</span>
                    <a
                      href="#zip"
                      onClick={(e) => { e.preventDefault(); alert("Downloading ZIP..."); }}
                      className="text-white/50 hover:text-white"
                    >
                      Portable (.zip)
                    </a>
                  </div>
                </div>
              )}
              {selectedPlatform === "macos" && (
                <div className="flex items-center justify-between flex-wrap gap-2 text-white/70">
                  <span className="text-white/40">macOS 13.0+</span>
                  <div className="flex items-center gap-3">
                    <a
                      href="#dmg-arm"
                      onClick={(e) => { e.preventDefault(); alert("Downloading Apple Silicon DMG..."); }}
                      className="text-white hover:underline underline-offset-4 font-medium"
                    >
                      Apple Silicon (.dmg)
                    </a>
                    <span className="text-white/20">•</span>
                    <a
                      href="#dmg-intel"
                      onClick={(e) => { e.preventDefault(); alert("Downloading Intel DMG..."); }}
                      className="text-white/50 hover:text-white"
                    >
                      Intel x64 (.dmg)
                    </a>
                  </div>
                </div>
              )}
              {selectedPlatform === "linux" && (
                <div className="flex items-center justify-between flex-wrap gap-2 text-white/70">
                  <span className="text-white/40">Linux x86_64</span>
                  <div className="flex items-center gap-3">
                    <a
                      href="#appimage"
                      onClick={(e) => { e.preventDefault(); alert("Downloading AppImage..."); }}
                      className="text-white hover:underline underline-offset-4 font-medium"
                    >
                      AppImage (92 MB)
                    </a>
                    <span className="text-white/20">•</span>
                    <a
                      href="#deb"
                      onClick={(e) => { e.preventDefault(); alert("Downloading DEB..."); }}
                      className="text-white/50 hover:text-white"
                    >
                      .deb package
                    </a>
                  </div>
                </div>
              )}
              {selectedPlatform === "docker" && (
                <div className="flex items-center justify-between flex-wrap gap-2 text-white/70">
                  <code className="text-white/90 font-mono">docker pull ghcr.io/archis-fsoc/terminal:v1.4.2</code>
                  <span className="text-white/40 text-[10px]">Multi-arch</span>
                </div>
              )}
            </div>
          </div>

          {/* Minimal Specs Footnote */}
          <div className="pt-3 border-t border-white/10 flex items-center justify-between text-[10px] font-mono text-white/35">
            <span className="flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-white/50" />
              <span>SHA-256 Verified</span>
            </span>
            <span>4GB RAM • OpenGL 4.1+ / Metal</span>
          </div>
        </motion.div>

        {/* Minimal Footer */}
        <div className="w-full max-w-xl text-center text-[10px] text-white/25 font-geist-pixel mt-4 uppercase tracking-widest">
          Archis Laser Terminal // Open Source Academic Edition
        </div>
      </section>
    </main>
  );
}

interface PlatformTabProps {
  active: boolean;
  onClick: () => void;
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  sub: string;
}

function PlatformTab({ active, onClick, icon: Icon, label, sub }: PlatformTabProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`p-2.5 rounded-xl border text-left transition-all duration-150 cursor-pointer ${
        active
          ? "bg-white/10 border-white/40 text-white shadow-sm"
          : "bg-white/[0.02] hover:bg-white/[0.05] border-white/10 text-white/50"
      }`}
    >
      <Icon className={`w-3.5 h-3.5 mb-1 ${active ? "text-white" : "text-white/40"}`} />
      <div className="text-xs font-orbitron font-medium">{label}</div>
      <div className="text-[10px] text-white/35 truncate font-mono">{sub}</div>
    </button>
  );
}

export default DownloadView;
