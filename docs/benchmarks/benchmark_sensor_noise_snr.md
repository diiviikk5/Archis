# Sensor Noise vs Centroiding Accuracy

<!-- generated-by: scripts/generate_benchmark_evidence.py engine-fingerprint: a709e0f7501437d006e000b7e253f0481b2972cd73cd741b08294bc2491bfeb3 -->

This deterministic sweep uses the nominal scenario, seed 26169, zero injected camera jitter, and 180 frames per level. `gaussian_noise_std` is sensor intensity standard deviation in 8-bit pixel units; it is not an unmeasured SNR claim.

| Gaussian noise σ | Centroid RMSE | Pointing RMSE | Target loss | Host throughput |
| ---: | ---: | ---: | ---: | ---: |
| 0 | 0.024 px | 1.867 px | 0.00% | 89.9 FPS |
| 8 | 0.075 px | 1.833 px | 0.00% | 35.4 FPS |
| 16 | 0.136 px | 1.811 px | 0.00% | 40.9 FPS |

Host throughput is informational and machine-dependent. Host: `Intel(R) Core(TM) i5-1035G1 CPU @ 1.00GHz` · `Linux-7.2.5-3-omarchy-x86_64-with-glibc2.44` · Python `3.14.7` · NumPy `2.5.3` · OpenCV `5.0.0`.
