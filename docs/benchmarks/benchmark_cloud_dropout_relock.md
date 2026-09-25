# Cloud Dropout and Re-acquisition Benchmark

<!-- generated-by: scripts/generate_benchmark_evidence.py engine-fingerprint: ad8cd198e6eefbf589b795f8c5b69f79dc60663bd270a16797f9c4582a0d227a -->

Generated from three 60-second runs (1,800 frames each) using seeds 26169–26171.

| Metric | SIH gate | Measured range | Result |
| --- | ---: | ---: | --- |
| Acquisition time | ≤ 2.0 s | 0.100 s | PASS |
| Centroid RMSE | ≤ 10 px | 0.099–0.102 px | PASS |
| Pointing RMSE | ≤ 10 px | 0.958–0.966 px | PASS |
| Target loss | < 5% | 0.50% | PASS |
| Worst re-acquisition | ≤ 1.0 s when applicable | 0.300 s | PASS |
| Conservative throughput (1000 / p95 latency) | ≥ 20 FPS | 66.8–144.4 FPS | 3/3 on this host |

Deterministic accuracy/control verdict: **PASS**. Throughput is reported separately because it depends on the host. A scenario is not claimed as a universal strict pass from these development-machine timings.

Host: `Intel(R) Core(TM) i5-1035G1 CPU @ 1.00GHz` · `Linux-7.2.5-3-omarchy-x86_64-with-glibc2.44` · Python `3.14.7` · NumPy `2.5.3` · OpenCV `5.0.0`.
