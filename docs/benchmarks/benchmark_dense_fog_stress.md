# Heavy Atmospheric Turbulence Benchmark

<!-- generated-by: scripts/generate_benchmark_evidence.py engine-fingerprint: a709e0f7501437d006e000b7e253f0481b2972cd73cd741b08294bc2491bfeb3 -->

Generated from three 60-second runs (1,800 frames each) using seeds 26169–26171.

| Metric | SIH gate | Measured range | Result |
| --- | ---: | ---: | --- |
| Acquisition time | ≤ 2.0 s | 0.100 s | PASS |
| Centroid RMSE | ≤ 10 px | 2.554–2.589 px | PASS |
| Pointing RMSE | ≤ 10 px | 3.038–3.083 px | PASS |
| Target loss | < 5% | 0.00% | PASS |
| Worst re-acquisition | ≤ 1.0 s when applicable | n/a | PASS |
| Conservative throughput (1000 / p95 latency) | ≥ 20 FPS | 14.8–23.8 FPS | 2/3 on this host |

Deterministic accuracy/control verdict: **PASS**. Throughput is reported separately because it depends on the host. A scenario is not claimed as a universal strict pass from these development-machine timings.

Host: `Intel(R) Core(TM) i5-1035G1 CPU @ 1.00GHz` · `Linux-7.2.5-3-omarchy-x86_64-with-glibc2.44` · Python `3.14.7` · NumPy `2.5.3` · OpenCV `5.0.0`.
