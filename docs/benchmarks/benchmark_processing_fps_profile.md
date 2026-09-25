# Processing Throughput Profile

<!-- generated-by: scripts/generate_benchmark_evidence.py engine-fingerprint: ad8cd198e6eefbf589b795f8c5b69f79dc60663bd270a16797f9c4582a0d227a -->

These are wall-clock measurements, not deterministic algorithm outputs. They must be regenerated on the designated Windows 11 x64 reference machine before a release claim is made.

| Scenario | Measured range | Runs meeting ≥20 FPS |
| --- | ---: | ---: |
| Nominal LEO Pass | 96.7–187.9 FPS | 3/3 |
| High-Speed Evasive Target | 89.9–169.2 FPS | 3/3 |
| Heavy Atmospheric Turbulence | 28.4–31.8 FPS | 3/3 |
| Cloud Dropout and Re-acquisition | 66.8–144.4 FPS | 3/3 |
| Platform Vibration | 77.2–165.8 FPS | 3/3 |

Across all 15 runs: minimum **28.4 FPS**, median **89.9 FPS**, maximum **187.9 FPS**. Heavy-turbulence throughput near 20 FPS is therefore explicitly treated as host-dependent, not a universal pass.

Host: `Intel(R) Core(TM) i5-1035G1 CPU @ 1.00GHz` · `Linux-7.2.5-3-omarchy-x86_64-with-glibc2.44` · Python `3.14.7` · NumPy `2.5.3` · OpenCV `5.0.0`.
