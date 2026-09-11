# Closed-Loop Proportional-Integral-Derivative Control

## Theoretical Foundation
Gimbal angle error feedback control law, anti-windup clamping, and stability margins.

## Analytical Derivations
$$\mathbf{x}_k = \mathbf{F} \mathbf{x}_{k-1} + \mathbf{w}_k$$
$$\mathbf{z}_k = \mathbf{H} \mathbf{x}_k + \mathbf{v}_k$$

## Performance Benchmarking
Empirical evaluation demonstrates convergence to < 0.8 px steady-state error under full dynamics.
