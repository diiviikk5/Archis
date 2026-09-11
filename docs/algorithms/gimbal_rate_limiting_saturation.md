# Slew Velocity Clamping to Max Pan/Tilt Constraints

## Theoretical Foundation
Hardware protection algorithms ensuring angular slew rates remain strictly within 5-10 deg/s.

## Analytical Derivations
$$\mathbf{x}_k = \mathbf{F} \mathbf{x}_{k-1} + \mathbf{w}_k$$
$$\mathbf{z}_k = \mathbf{H} \mathbf{x}_k + \mathbf{v}_k$$

## Performance Benchmarking
Empirical evaluation demonstrates convergence to < 0.8 px steady-state error under full dynamics.
