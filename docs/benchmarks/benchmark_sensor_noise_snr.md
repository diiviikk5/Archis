# Sensor Noise vs Centroiding Accuracy

<!-- generated-by: scripts/generate_benchmark_evidence.py engine-fingerprint: dddfe241f2cae04eb877fb2cda66009abd9ef2d17df4ea467e9946edec42d95f -->

This deterministic sweep uses the nominal scenario, seed 26169, zero injected camera jitter, and 180 frames per level. `gaussian_noise_std` is sensor intensity standard deviation in 8-bit pixel units; it is not an unmeasured SNR claim.

| Gaussian noise σ | Centroid RMSE | Pointing RMSE | Target loss | Host throughput |
| ---: | ---: | ---: | ---: | ---: |
| 0 | 0.025 px | 1.880 px | 0.00% | 150.4 FPS |
| 8 | 0.051 px | 1.853 px | 0.00% | 53.9 FPS |
| 16 | 0.091 px | 1.833 px | 0.00% | 48.9 FPS |

Host throughput is informational and machine-dependent. Host: `Intel(R) Core(TM) i5-1035G1 CPU @ 1.00GHz` · `Linux-7.2.5-3-omarchy-x86_64-with-glibc2.44` · Python `3.14.7` · NumPy `2.5.3` · OpenCV `4.14.0`.
