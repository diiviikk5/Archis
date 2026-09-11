# Sinusoidal Transverse Wave Oscillation

## Overview
Harmonic perturbation modeling, spatial wavenumber, and frequency-dependent slew rate compensation.

## Mathematical Formulation
The optical tracking parameters adhere strictly to the system requirements:
- Update frequency: $\ge 30\,\text{Hz}$
- Sampling interval: $\Delta t = 0.0333\,\text{s}$
- Spatial resolution: $640 \times 480\,\text{pixels}$
- Coordinate space: $2000 \times 2000\,\text{pixels}$

$$\mathbf{e}(t) = \mathbf{x}_{\text{target}}(t) - \mathbf{x}_{\text{boresight}}$$

$$\text{RMS}_{\text{error}} = \sqrt{\frac{1}{N} \sum_{k=1}^{N} \|\mathbf{e}_k\|^2} \le 10.0\,\text{px}$$

## Verification Procedure
Automated verification tests run via `archis_tracker/tests/` ensure zero deviation from official thresholds.
