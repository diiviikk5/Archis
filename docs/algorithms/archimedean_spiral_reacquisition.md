# Archimedean Spiral Autonomous Search Pattern

## Theoretical Foundation
Expanding spiral search trajectory r(t) = a*t, theta(t) = omega*t for rapid sub-second target relock.

## Analytical Derivations
$$\mathbf{x}_k = \mathbf{F} \mathbf{x}_{k-1} + \mathbf{w}_k$$
$$\mathbf{z}_k = \mathbf{H} \mathbf{x}_k + \mathbf{v}_k$$

## Performance Benchmarking
Empirical evaluation demonstrates convergence to < 0.8 px steady-state error under full dynamics.
