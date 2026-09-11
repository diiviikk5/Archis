# Target World Velocity Feedforward Compensation

## Theoretical Foundation
Reconstruction of absolute target world velocity v_world = v_rel + v_cam for zero-lag tracking.

## Analytical Derivations
$$\mathbf{x}_k = \mathbf{F} \mathbf{x}_{k-1} + \mathbf{w}_k$$
$$\mathbf{z}_k = \mathbf{H} \mathbf{x}_k + \mathbf{v}_k$$

## Performance Benchmarking
Empirical evaluation demonstrates convergence to < 0.8 px steady-state error under full dynamics.
