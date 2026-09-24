# Processing Throughput Profile

<!-- generated-by: scripts/generate_benchmark_evidence.py engine-fingerprint: a709e0f7501437d006e000b7e253f0481b2972cd73cd741b08294bc2491bfeb3 -->

These are wall-clock measurements, not deterministic algorithm outputs. They must be regenerated on the designated Windows 11 x64 reference machine before a release claim is made.

| Scenario | Measured range | Runs meeting ≥20 FPS |
| --- | ---: | ---: |
| Nominal LEO Pass | 90.5–97.4 FPS | 3/3 |
| High-Speed Evasive Target | 93.6–96.5 FPS | 3/3 |
| Heavy Atmospheric Turbulence | 14.8–23.8 FPS | 2/3 |
| Cloud Dropout and Re-acquisition | 78.7–82.1 FPS | 3/3 |
| Platform Vibration | 84.7–95.6 FPS | 3/3 |

Across all 15 runs: minimum **14.8 FPS**, median **90.5 FPS**, maximum **97.4 FPS**. Heavy-turbulence throughput near 20 FPS is therefore explicitly treated as host-dependent, not a universal pass.

Host: `Intel(R) Core(TM) i5-1035G1 CPU @ 1.00GHz` · `Linux-7.2.5-3-omarchy-x86_64-with-glibc2.44` · Python `3.14.7` · NumPy `2.5.3` · OpenCV `5.0.0`.
