import React, { useState, useEffect, useRef } from "react";
import { ArrowRight, BookOpen, Download, Sparkles } from "lucide-react";
import WarpText from "./WarpText";
import DownloadView from "./DownloadView";
import DocsView from "./DocsView";

export function App() {
  const [view, setView] = useState<"hero" | "download" | "docs">("hero");
  const heroVideoRef = useRef<HTMLVideoElement>(null);

  // Initialize HLS video stream for the Hero view
  useEffect(() => {
    if (view !== "hero") return;
    const video = heroVideoRef.current;
    if (!video) return;

    const streamUrl =
      "https://stream.mux.com/3gErUdcrPfibrZ00ysHSLAupEL01PeX4PpAwgcGpGvbAM.m3u8";

    if ((window as any).Hls && (window as any).Hls.isSupported()) {
      const hls = new (window as any).Hls({
        enableWorker: true,
        lowLatencyMode: true,
      });
      hls.loadSource(streamUrl);
      hls.attachMedia(video);
      hls.on((window as any).Hls.Events.MANIFEST_PARSED, () => {
        video.play().catch(() => {});
      });
      return () => {
        hls.destroy();
      };
    } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
      video.src = streamUrl;
      video.play().catch(() => {});
    }
  }, [view]);

  // When switching views, reset window scroll to top
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "instant" as any });
  }, [view]);

  // View: Documentation Page (Antigravity / Gemini / Stripe Docs style)
  if (view === "docs") {
    return (
      <DocsView
        onBack={() => setView("hero")}
        onOpenDownload={() => setView("download")}
      />
    );
  }

  // View: Download Page (Left looping video + Right Download Hub)
  if (view === "download") {
    return (
      <DownloadView
        onBack={() => setView("hero")}
        onOpenDocs={() => setView("docs")}
      />
    );
  }

  // View: Hero View with Geist Pixel typography, elite top-right Docs button, and Join button
  return (
    <main className="relative w-full h-screen overflow-hidden bg-black flex flex-col items-center justify-center select-none font-sans">
      {/* 1. BACKGROUND VIDEO (Full viewport, Mux HLS stream) */}
      <video
        ref={heroVideoRef}
        autoPlay
        muted
        loop
        playsInline
        preload="auto"
        className="absolute inset-0 w-full h-full object-cover pointer-events-none z-0"
      />

      {/* 2. SUBTLE CINEMATIC CONTRAST OVERLAYS */}
      <div className="absolute inset-0 bg-black/40 pointer-events-none z-1" />
      <div className="absolute inset-0 bg-radial-[circle_at_center,transparent_0%,rgba(0,0,0,0.6)_90%] pointer-events-none z-1" />

      {/* TOP-RIGHT DOCUMENTATION BUTTON (Elite Antigravity / Stripe Style) */}
      <div className="absolute top-6 right-6 sm:top-8 sm:right-8 z-30 flex items-center gap-3">
        <button
          onClick={() => setView("docs")}
          className="group relative inline-flex items-center gap-2.5 px-4 py-2 rounded-full bg-white/[0.07] hover:bg-white text-white hover:text-black border border-white/20 hover:border-white text-xs font-mono tracking-wider transition-all duration-300 backdrop-blur-xl cursor-pointer shadow-[0_0_20px_rgba(255,255,255,0.08)] hover:shadow-[0_0_35px_rgba(255,255,255,0.45)] active:scale-95"
        >
          <span className="w-2 h-2 rounded-full bg-white/80 group-hover:bg-black transition-colors" />
          <span className="font-semibold tracking-wide">DOCS &bull; ARCHITECTURE</span>
          <ArrowRight className="w-3.5 h-3.5 transition-transform duration-200 group-hover:translate-x-1" />
        </button>
      </div>

      {/* 3. MIDDLE-ALIGNED WARP TEXT TITLE */}
      <div className="relative z-10 w-full max-w-[1400px] mx-auto px-6 flex flex-col items-center justify-center text-center">
        <div className="w-full flex flex-col items-center justify-center">
          {/* ARCHIS WARP TEXT */}
          <WarpText
            text="ARCHIS"
            fontFamily="'Geist Pixel', monospace"
            fontSize="clamp(4.5rem, 11vw, 9rem)"
            fontWeight={400}
            letterSpacing="0.08em"
            color="#ffffff"
            warpStrength={0.12}
            warpScale={1.6}
            speed={0.65}
            pointerInfluence={0.42}
            pointerStrength={0.48}
            refraction={0.022}
            ripple={true}
            className="w-full max-w-[1200px] h-[180px] sm:h-[240px] md:h-[280px]"
          />
          {/* OPTICAL ALIGNMENT */}
          <div className="font-geist-pixel text-lg sm:text-2xl md:text-3xl lg:text-[2.25rem] font-normal tracking-[0.22em] text-white/90 mt-1 sm:mt-2 drop-shadow-[0_0_20px_rgba(255,255,255,0.35)] pointer-events-none">
            OPTICAL ALIGNMENT
          </div>
        </div>

        {/* 4. JOIN ARCHIS BUTTON (Opens Download Hub) */}
        <button
          onClick={() => setView("download")}
          className="mt-8 sm:mt-12 group relative inline-flex items-center gap-3.5 px-9 py-4 rounded-full bg-white/10 hover:bg-white text-white hover:text-black border border-white/25 hover:border-white text-xs sm:text-sm tracking-[0.22em] uppercase backdrop-blur-xl transition-all duration-300 shadow-[0_0_30px_rgba(255,255,255,0.14)] hover:shadow-[0_0_45px_rgba(255,255,255,0.6)] cursor-pointer active:scale-95 z-20"
        >
          <span className="font-semibold tracking-[0.2em]">Join Archis</span>
          <ArrowRight className="w-4 h-4 transition-transform duration-200 group-hover:translate-x-1.5 text-white/70 group-hover:text-black" />
        </button>
      </div>
    </main>
  );
}

export default App;
