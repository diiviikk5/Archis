# Sensor Noise vs Centroiding Accuracy

<!-- generated-by: scripts/generate_benchmark_evidence.py engine-fingerprint: ad8cd198e6eefbf589b795f8c5b69f79dc60663bd270a16797f9c4582a0d227a -->

This deterministic sweep uses the nominal scenario, seed 26169, zero injected camera jitter, and 180 frames per level. `gaussian_noise_std` is sensor intensity standard deviation in 8-bit pixel units; it is not an unmeasured SNR claim.

| Gaussian noise σ | Centroid RMSE | Pointing RMSE | Target loss | Host throughput |
| ---: | ---: | ---: | ---: | ---: |
| 0 | 0.024 px | 1.867 px | 0.00% | 77.5 FPS |
| 8 | 0.075 px | 1.833 px | 0.00% | 28.6 FPS |
| 16 | 0.136 px | 1.811 px | 0.00% | 60.0 FPS |

Host throughput is informational and machine-dependent. Host: `Intel(R) Core(TM) i5-1035G1 CPU @ 1.00GHz` · `Linux-7.2.5-3-omarchy-x86_64-with-glibc2.44` · Python `3.14.7` · NumPy `2.5.3` · OpenCV `5.0.0`.
