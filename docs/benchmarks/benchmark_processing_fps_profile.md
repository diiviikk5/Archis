# Processing Throughput Profile

<!-- generated-by: scripts/generate_benchmark_evidence.py engine-fingerprint: dddfe241f2cae04eb877fb2cda66009abd9ef2d17df4ea467e9946edec42d95f -->

These are wall-clock measurements, not deterministic algorithm outputs. They must be regenerated on the designated Windows 11 x64 reference machine before a release claim is made.

| Scenario | Measured range | Runs meeting ≥20 FPS |
| --- | ---: | ---: |
| Nominal LEO Pass | 113.4–149.2 FPS | 3/3 |
| High-Speed Evasive Target | 112.1–141.7 FPS | 3/3 |
| Heavy Atmospheric Turbulence | 17.8–27.9 FPS | 2/3 |
| Cloud Dropout and Re-acquisition | 127.7–129.3 FPS | 3/3 |
| Platform Vibration | 131.9–147.3 FPS | 3/3 |

Across all 15 runs: minimum **17.8 FPS**, median **128.9 FPS**, maximum **149.2 FPS**. Heavy-turbulence throughput near 20 FPS is therefore explicitly treated as host-dependent, not a universal pass.

Host: `Intel(R) Core(TM) i5-1035G1 CPU @ 1.00GHz` · `Linux-7.2.5-3-omarchy-x86_64-with-glibc2.44` · Python `3.14.7` · NumPy `2.5.3` · OpenCV `4.14.0`.
