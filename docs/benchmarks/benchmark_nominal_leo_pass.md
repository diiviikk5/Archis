# Nominal LEO Pass Benchmark

<!-- generated-by: scripts/generate_benchmark_evidence.py engine-fingerprint: dddfe241f2cae04eb877fb2cda66009abd9ef2d17df4ea467e9946edec42d95f -->

Generated from three 60-second runs (1,800 frames each) using seeds 26169–26171.

| Metric | SIH gate | Measured range | Result |
| --- | ---: | ---: | --- |
| Acquisition time | ≤ 2.0 s | 0.100 s | PASS |
| Centroid RMSE | ≤ 10 px | 0.023–0.028 px | PASS |
| Pointing RMSE | ≤ 10 px | 2.860–2.888 px | PASS |
| Target loss | < 5% | 0.00% | PASS |
| Worst re-acquisition | ≤ 1.0 s when applicable | n/a | PASS |
| Processing throughput | ≥ 20 FPS | 113.4–149.2 FPS | 3/3 on this host |

Deterministic accuracy/control verdict: **PASS**. Throughput is reported separately because it depends on the host. A scenario is not claimed as a universal strict pass from these development-machine timings.

Host: `Intel(R) Core(TM) i5-1035G1 CPU @ 1.00GHz` · `Linux-7.2.5-3-omarchy-x86_64-with-glibc2.44` · Python `3.14.7` · NumPy `2.5.3` · OpenCV `4.14.0`.
