# Mie Scattering & Dense Fog Attenuation

## Overview
Aerosol droplet diffraction, forward scattering phase function, and Gaussian spatial blur filtering.

## Mathematical Formulation
The optical tracking parameters adhere strictly to the system requirements:
- Update frequency: >= 30 Hz
- Sampling interval: dt = 0.0333 s
- Spatial resolution: 640x480 pixels
- Coordinate space: 2000x2000 pixels

$$\mathbf{e}(t) = \mathbf{x}_{\text{target}}(t) - \mathbf{x}_{\text{boresight}}$$
$$\text{RMS}_{\text{error}} = \sqrt{\frac{1}{N} \sum_{k=1}^{N} \|\mathbf{e}_k\|^2} \le 10.0\,\text{px}$$

## Verification Procedure
Automated verification tests run via `archis_tracker/tests/` ensure zero deviation from official thresholds.
