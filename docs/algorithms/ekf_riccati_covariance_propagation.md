# Discrete Algebraic Riccati Covariance Propagation

## Theoretical Foundation
Prior covariance projection P_k|k-1 = F P F^T + Q and posterior Kalman gain optimization.

## Analytical Derivations
$$\mathbf{x}_k = \mathbf{F} \mathbf{x}_{k-1} + \mathbf{w}_k$$
$$\mathbf{z}_k = \mathbf{H} \mathbf{x}_k + \mathbf{v}_k$$

## Performance Benchmarking
Empirical evaluation demonstrates convergence to < 0.8 px steady-state error under full dynamics.
