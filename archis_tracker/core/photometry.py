"""Scale-aware optical spot measurements used by detection and filtering.

The formulas are implemented independently for Archis.  Signal-to-noise is
measured over an aperture instead of inferred from detector confidence, and
all geometry is expressed relative to the measured spot FWHM.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

import cv2
import numpy as np


QUANTISATION_SIGMA_LSB = 1.0 / math.sqrt(12.0)


@dataclass(frozen=True, slots=True)
class SpotPhotometry:
    fwhm_px: float
    snr_aperture: float | None
    snr_peak: float | None
    background_level: float
    background_sigma: float
    clipped: bool
    saturated_fraction: float

    @property
    def saturated(self) -> bool:
        return self.saturated_fraction > 0.05


def robust_sigma(values: np.ndarray, floor: float = QUANTISATION_SIGMA_LSB) -> float:
    """Return ``1.4826 * MAD`` with an explicit quantisation-noise floor."""
    flat = np.asarray(values, dtype=np.float64).reshape(-1)
    if flat.size == 0:
        return float(floor)
    median = float(np.median(flat))
    mad = float(np.median(np.abs(flat - median)))
    return max(float(floor), 1.4826 * mad)


def equivalent_fwhm(residual: np.ndarray, seed_xy: tuple[float, float],
                    fallback_px: float) -> float:
    """Estimate equivalent circular FWHM from the seed's half-maximum component."""
    if residual.ndim != 2 or residual.size == 0:
        return float(fallback_px)
    peak_y = int(np.clip(round(seed_xy[1]), 0, residual.shape[0] - 1))
    peak_x = int(np.clip(round(seed_xy[0]), 0, residual.shape[1] - 1))
    peak = float(residual[peak_y, peak_x])
    if not math.isfinite(peak) or peak <= 0:
        return float(fallback_px)
    mask = (residual >= 0.5 * peak).astype(np.uint8)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    if count <= 1:
        return float(fallback_px)
    label = int(labels[peak_y, peak_x])
    if label <= 0:
        return float(fallback_px)
    area = float(stats[label, cv2.CC_STAT_AREA])
    diameter = 2.0 * math.sqrt(area / math.pi)
    return float(np.clip(diameter, 1.5, 64.0))


def measure_spot(frame: np.ndarray, residual: np.ndarray, center_xy: tuple[float, float],
                 bbox: tuple[int, int, int, int], fallback_fwhm_px: float) -> SpotPhotometry:
    """Measure scale, aperture SNR, clipping and saturation for one selected spot."""
    height, width = frame.shape
    x, y = center_xy
    bx, by, bw, bh = bbox
    analysis_radius = int(np.ceil(max(12.0, 5.0 * fallback_fwhm_px, 3.0 * max(bw, bh))))
    x0 = max(0, int(np.floor(x)) - analysis_radius)
    y0 = max(0, int(np.floor(y)) - analysis_radius)
    x1 = min(width, int(np.ceil(x)) + analysis_radius + 1)
    y1 = min(height, int(np.ceil(y)) + analysis_radius + 1)
    local_residual = residual[y0:y1, x0:x1]
    fwhm = equivalent_fwhm(
        local_residual, (x - x0, y - y0), fallback_fwhm_px
    )
    source = frame[y0:y1, x0:x1].astype(np.float64, copy=False)
    yy, xx = np.ogrid[y0:y1, x0:x1]
    radius = np.sqrt((xx - float(x)) ** 2 + (yy - float(y)) ** 2)
    aperture = radius <= 1.5 * fwhm
    annulus = (radius >= 2.5 * fwhm) & (radius <= 4.0 * fwhm)

    annulus_values = source[annulus]
    if annulus_values.size:
        background = float(np.median(annulus_values))
        sigma = robust_sigma(annulus_values)
    else:
        background = float(np.median(frame))
        sigma = robust_sigma(source)

    aperture_values = source[aperture]
    if aperture_values.size:
        signal = float(np.maximum(aperture_values - background, 0.0).sum())
        snr_aperture = signal / (sigma * math.sqrt(aperture_values.size))
        snr_peak = max(0.0, float(aperture_values.max()) - background) / sigma
        core = aperture_values >= background + 0.5 * max(
            0.0, float(aperture_values.max()) - background
        )
        saturated_fraction = (
            float(np.mean(aperture_values[core] >= 254.5)) if np.any(core) else 0.0
        )
    else:
        snr_aperture = snr_peak = None
        saturated_fraction = 0.0

    clipped = bx <= 0 or by <= 0 or bx + bw >= width or by + bh >= height
    return SpotPhotometry(
        fwhm, snr_aperture, snr_peak, background, sigma, clipped, saturated_fraction
    )


def measurement_sigma_px(photometry: SpotPhotometry, *, calibration: float = 1.5,
                         floor_px: float = 0.15, ceiling_px: float = 20.0,
                         clipped_bias_px: float = 2.0,
                         saturated_bias_px: float = 0.20) -> float:
    """Convert measured spot quality into bounded Kalman position uncertainty."""
    if photometry.snr_aperture is None or photometry.snr_aperture <= 0:
        base = ceiling_px
    else:
        base = calibration * photometry.fwhm_px / (2.0 * photometry.snr_aperture)
    variance = float(np.clip(base, floor_px, ceiling_px)) ** 2
    if photometry.clipped:
        variance += clipped_bias_px ** 2
    if photometry.saturated:
        variance += saturated_bias_px ** 2
    return float(np.clip(math.sqrt(variance), floor_px, ceiling_px))
