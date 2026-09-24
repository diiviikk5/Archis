"""
Archis Optical Tracker - Multi-Algorithm Computer Vision Beacon Detector
Implements Intensity-Weighted Centroid (IWC), Analytical 2D Gaussian Surface Fit,
and Normalized Cross-Correlation (NCC) template matching with dynamic track gating.
"""
import numpy as np
import cv2
from typing import Tuple, Optional, List, Dict, Any
from .config import TrackingAlgorithm, AGCMode, DetectorConfig
from .association import DataAssociator
from .ai_detector import NanoSpotDetector
from .photometry import SpotPhotometry, measure_spot


class DetectionResult:
    def __init__(self, detected: bool, x: float = 0.0, y: float = 0.0,
                 bbox: Tuple[int, int, int, int] = (0, 0, 0, 0),
                 gate_bbox: Optional[Tuple[int, int, int, int]] = None,
                 confidence: float = 0.0, peak_intensity: float = 0.0,
                 snr_db: float = 0.0, algorithm_used: str = "IWC",
                 heatmap: Optional[np.ndarray] = None,
                 is_decoy: bool = False,
                 heatmap_bbox: Optional[Tuple[int, int, int, int]] = None,
                 fwhm_px: Optional[float] = None,
                 snr_aperture: Optional[float] = None,
                 snr_peak: Optional[float] = None,
                 clipped: bool = False,
                 saturated_fraction: float = 0.0):
        self.detected = detected
        self.x = x  # Sub-pixel continuous coordinates in viewport (0 to 640)
        self.y = y  # (0 to 480)
        self.bbox = bbox  # (x, y, w, h)
        self.gate_bbox = gate_bbox  # Track gate region
        self.confidence = confidence  # 0.0 to 1.0
        self.peak_intensity = peak_intensity
        self.snr_db = snr_db
        self.algorithm_used = algorithm_used
        self.heatmap = heatmap
        self.is_decoy = is_decoy
        self.heatmap_bbox = heatmap_bbox
        self.fwhm_px = fwhm_px
        self.snr_aperture = snr_aperture
        self.snr_peak = snr_peak
        self.clipped = clipped
        self.saturated_fraction = saturated_fraction

    @property
    def saturated(self) -> bool:
        return self.saturated_fraction > 0.05


class BeaconDetector:
    def __init__(self, config: Optional[DetectorConfig] = None):
        self.config = config or DetectorConfig()
        self.associator = DataAssociator(gate_threshold_chi2=9.21)
        self.ai_detector = NanoSpotDetector()
        self.spot_scale_px = float(self.config.fallback_fwhm_px)
        
        # Stored target template for Correlation Tracking (NCC)
        self.target_template: Optional[np.ndarray] = None
        self.template_size = 21
        self.last_candidates: List[DetectionResult] = []

    def apply_agc(self, frame: np.ndarray) -> np.ndarray:
        """Applies Automatic Gain Control (Linear, Histogram Equalization, Plateau)."""
        mode = self.config.agc_mode
        if mode == AGCMode.LINEAR:
            return frame
        elif mode == AGCMode.HISTOGRAM_EQUALIZATION:
            return cv2.equalizeHist(frame)
        elif mode == AGCMode.PLATEAU_EQUALIZATION:
            # Plateau equalization: clamp histogram peaks to avoid noise explosion
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            return clahe.apply(frame)
        return frame

    def detect(self, frame: np.ndarray, 
               predicted_pos: Optional[Tuple[float, float]] = None,
               cov_matrix: Optional[np.ndarray] = None) -> DetectionResult:
        """
        Detects designated optical beacon using selected aerospace CV tracking algorithm.
        """
        self.last_candidates = []
        h, w = frame.shape
        agc_frame = self.apply_agc(frame)
        photometry_frame = cv2.medianBlur(agc_frame, 3)
        photometry_background = float(np.median(photometry_frame))
        photometry_residual = np.maximum(
            photometry_frame.astype(np.float32) - photometry_background, 0.0
        )
        
        # 1. Determine Search Region (Track Gate vs Full Viewport)
        gate_box = None
        crop_x0, crop_y0 = 0, 0
        search_frame = agc_frame
        
        if self.config.enable_track_gate and predicted_pos is not None:
            px, py = predicted_pos
            scale_gate = int(np.ceil(8.0 * self.spot_scale_px))
            g_sz = max(self.config.gate_size_px, scale_gate)
            # Ensure gate center stays inside frame
            gx1 = max(0, int(px - g_sz / 2.0))
            gy1 = max(0, int(py - g_sz / 2.0))
            gx2 = min(w, gx1 + g_sz)
            gy2 = min(h, gy1 + g_sz)
            
            if (gx2 - gx1) >= 20 and (gy2 - gy1) >= 20:
                gate_box = (gx1, gy1, gx2 - gx1, gy2 - gy1)
                crop_x0, crop_y0 = gx1, gy1
                search_frame = agc_frame[gy1:gy2, gx1:gx2]

        # 1.1 AI Deep Learning NanoSpot-Net ONNX Inference
        if self.config.algorithm == TrackingAlgorithm.AI_ONNX and not self.ai_detector.is_loaded:
            return DetectionResult(False, gate_bbox=gate_box, algorithm_used="ONNX unavailable")
        if self.config.algorithm == TrackingAlgorithm.AI_ONNX:
            sh, sw = search_frame.shape
            if sh > 80 or sw > 80:
                # Acquisition mode: extract native-scale 64x64 candidate ROI around brightest spatial region
                cand_y, cand_x = np.unravel_index(np.argmax(search_frame), search_frame.shape)
                patch_sz = 64
                px1 = max(0, min(sw - patch_sz, int(cand_x) - patch_sz // 2))
                py1 = max(0, min(sh - patch_sz, int(cand_y) - patch_sz // 2))
                ai_input_patch = search_frame[py1:py1 + patch_sz, px1:px1 + patch_sz]
                patch_off_x, patch_off_y = px1, py1
            else:
                ai_input_patch = search_frame
                patch_off_x, patch_off_y = 0, 0

            detected, sub_x, sub_y, ai_conf, is_decoy, heatmap = self.ai_detector.detect_spot(
                ai_input_patch,
                min_confidence=self.config.ai_confidence_threshold,
                enable_decoy_filter=self.config.enable_ai_decoy_filter
            )
            if not self.ai_detector.is_loaded:
                return DetectionResult(False, gate_bbox=gate_box, algorithm_used="ONNX inference failed")
            heatmap_box = (crop_x0 + patch_off_x, crop_y0 + patch_off_y,
                           ai_input_patch.shape[1], ai_input_patch.shape[0])
            if detected:
                final_x = float(crop_x0 + patch_off_x + sub_x)
                final_y = float(crop_y0 + patch_off_y + sub_y)
                # Derive the displayed extent from the actual response component.
                mask = (heatmap >= max(0.25, float(heatmap.max()) * 0.5)).astype(np.uint8)
                _, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
                hy, hx = np.unravel_index(heatmap.argmax(), heatmap.shape)
                component = stats[labels[hy, hx]]
                scale_x, scale_y = ai_input_patch.shape[1] / 64.0, ai_input_patch.shape[0] / 64.0
                gbx = crop_x0 + patch_off_x + int(component[0] * scale_x)
                gby = crop_y0 + patch_off_y + int(component[1] * scale_y)
                bw = max(1, min(w - gbx, int(np.ceil(component[2] * scale_x))))
                bh = max(1, min(h - gby, int(np.ceil(component[3] * scale_y))))
                area = float(component[4] * scale_x * scale_y)
                measured_peak = float(ai_input_patch.max())

                if predicted_pos is not None:
                    cand = [{"x": final_x, "y": final_y, "peak": measured_peak,
                             "global_bbox": (gbx, gby, bw, bh),
                             "local_bbox": (gbx - crop_x0, gby - crop_y0, bw, bh), "area": area}]
                    best = self.associator.associate_best_candidate(cand, predicted_pos[0], predicted_pos[1], cov_matrix)
                    if best is None:
                        return DetectionResult(detected=False, gate_bbox=gate_box, confidence=ai_conf, heatmap=heatmap, heatmap_bbox=heatmap_box, is_decoy=is_decoy, algorithm_used=TrackingAlgorithm.AI_ONNX.value)

                px_int = int(np.clip(sub_x, 0, ai_input_patch.shape[1] - 1))
                py_int = int(np.clip(sub_y, 0, ai_input_patch.shape[0] - 1))
                peak_val = float(ai_input_patch[py_int, px_int])
                mean_bg, std_bg = cv2.meanStdDev(ai_input_patch)
                snr_db = float(20.0 * np.log10(max(1.0, peak_val - float(mean_bg[0][0])) / max(1.0, float(std_bg[0][0]))))

                photo = self._measure_photometry(
                    photometry_frame, photometry_residual,
                    (final_x, final_y), (gbx, gby, bw, bh),
                )
                return DetectionResult(
                    detected=True,
                    x=final_x,
                    y=final_y,
                    bbox=(gbx, gby, bw, bh),
                    gate_bbox=gate_box,
                    confidence=ai_conf,
                    peak_intensity=peak_val,
                    snr_db=snr_db,
                    algorithm_used=TrackingAlgorithm.AI_ONNX.value,
                    heatmap=heatmap,
                    heatmap_bbox=heatmap_box,
                    is_decoy=is_decoy,
                    fwhm_px=photo.fwhm_px,
                    snr_aperture=photo.snr_aperture,
                    snr_peak=photo.snr_peak,
                    clipped=photo.clipped,
                    saturated_fraction=photo.saturated_fraction,
                )
            else:
                return DetectionResult(
                    detected=False,
                    gate_bbox=gate_box,
                    confidence=ai_conf,
                    algorithm_used=TrackingAlgorithm.AI_ONNX.value,
                    heatmap=heatmap,
                    heatmap_bbox=heatmap_box,
                    is_decoy=is_decoy
                )

        # 2. Noise suppression pre-filter
        filtered = photometry_frame[crop_y0:crop_y0 + search_frame.shape[0],
                                    crop_x0:crop_x0 + search_frame.shape[1]]
        sh, sw = filtered.shape
        
        # 3. Robust full-frame proposal: median/MAD intensity threshold plus
        # difference-of-Gaussians.  Unlike a brightest-pixel shortcut this
        # keeps multiple candidates for association and identity verification.
        mean_val, std_val = cv2.meanStdDev(filtered)
        mean_bg = float(mean_val[0][0])
        std_bg = float(std_val[0][0])
        pixels = filtered.astype(np.float32)
        median = float(np.median(pixels))
        mad = float(np.median(np.abs(pixels - median)))
        robust_sigma = max(1.0, 1.4826 * mad)
        percentile = float(np.percentile(pixels, 99.5))
        dynamic_thresh = max(32.0, median + 7.0 * robust_sigma)
        if percentile > median + 5.0:
            dynamic_thresh = min(dynamic_thresh, percentile)
        dynamic_thresh = min(254.0, dynamic_thresh)
        _, intensity_mask = cv2.threshold(filtered, dynamic_thresh, 255, cv2.THRESH_BINARY)
        if self.config.enable_scale_relative_geometry:
            dog_small_sigma = float(np.clip(self.spot_scale_px / 8.0, 0.8, 2.5))
            dog_large_sigma = 3.0 * dog_small_sigma
        else:
            dog_small_sigma, dog_large_sigma = 0.8, 2.4
        small = cv2.GaussianBlur(filtered, (0, 0), dog_small_sigma)
        large = cv2.GaussianBlur(filtered, (0, 0), dog_large_sigma)
        dog = cv2.subtract(small, large)
        dog_median = float(np.median(dog))
        dog_mad = float(np.median(np.abs(dog.astype(np.float32) - dog_median)))
        dog_threshold = min(254.0, max(28.0, dog_median + 7.0 * max(1.0, 1.4826 * dog_mad)))
        _, dog_mask = cv2.threshold(dog, dog_threshold, 255, cv2.THRESH_BINARY)
        binary = cv2.bitwise_or(intensity_mask, dog_mask)
        
        # Morphological opening to strip salt noise
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        opened = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        
        # 4. Blob / Contour extraction
        contours, _ = cv2.findContours(opened, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        candidates: List[Dict[str, Any]] = []
        
        if self.config.enable_scale_relative_geometry:
            reference_area = np.pi * (self.spot_scale_px * 0.5) ** 2
            minimum_area = max(2.0, 0.08 * reference_area)
            maximum_area = max(64.0, 10.0 * reference_area)
        else:
            minimum_area = float(self.config.min_target_area)
            maximum_area = float(self.config.max_target_area)

        for c in contours:
            area = cv2.contourArea(c)
            if minimum_area <= area <= maximum_area:
                bx, by, bw, bh = cv2.boundingRect(c)
                aspect = float(bw) / float(max(1, bh))
                if 0.30 <= aspect <= 3.2:
                    # Global frame coordinates
                    cx_global = float(bx + bw / 2.0 + crop_x0)
                    cy_global = float(by + bh / 2.0 + crop_y0)
                    
                    roi = filtered[by:by+bh, bx:bx+bw]
                    peak = float(np.max(roi)) if roi.size > 0 else 0.0
                    
                    candidates.append({
                        "x": cx_global,
                        "y": cy_global,
                        "local_bbox": (bx, by, bw, bh),
                        "global_bbox": (bx + crop_x0, by + crop_y0, bw, bh),
                        "peak": peak,
                        "area": area,
                        "compactness": float(area) / float(max(1, bw * bh)),
                    })

        # Fallback if binary threshold failed to catch beacon
        if not candidates:
            max_val, max_loc = cv2.minMaxLoc(filtered)[1], cv2.minMaxLoc(filtered)[3]
            if max_val > mean_bg + 1.8 * std_bg and max_val > 45.0:
                lx, ly = max_loc
                candidates.append({
                    "x": float(lx + crop_x0),
                    "y": float(ly + crop_y0),
                    "local_bbox": (max(0, lx-5), max(0, ly-5), 11, 11),
                    "global_bbox": (max(0, lx-5 + crop_x0), max(0, ly-5 + crop_y0), 11, 11),
                    "peak": float(max_val),
                    "area": 25.0,
                    "compactness": 1.0,
                })

        if not candidates:
            return DetectionResult(detected=False, gate_bbox=gate_box)

        # 5. Candidate verification and data association.  The compact
        # verifier is intentionally soft evidence; CodeLock performs the hard
        # temporal identity decision when configured.
        for candidate in candidates:
            contrast = np.clip((candidate["peak"] - mean_bg) / max(40.0, 3.0 * std_bg), 0.0, 1.0)
            size = np.clip(candidate["area"] / max(1.0, self.config.min_target_area * 2.0), 0.0, 1.0)
            candidate["verifier_score"] = float(0.55 * contrast + 0.30 * candidate["compactness"] + 0.15 * size)

        if predicted_pos is not None:
            best = self.associator.associate_best_candidate(
                candidates, predicted_pos[0], predicted_pos[1], cov_matrix
            )
            if best is None:
                best = candidates[0]
        else:
            best = max(candidates, key=lambda c: (c["verifier_score"], c["peak"]))

        gbx, gby, gbw, gbh = best["global_bbox"]
        lbx, lby, lbw, lbh = best["local_bbox"]
        
        # 6. Apply Selected Sub-Pixel Centroid Algorithm
        algo = self.config.algorithm
        final_x, final_y = best["x"], best["y"]

        heatmap = None
        heatmap_bbox = None
        is_decoy = False
        ai_confidence = None

        if algo in (TrackingAlgorithm.IWC, TrackingAlgorithm.HYBRID):
            # Intensity-Weighted Centroid
            pad = max(3, int(np.ceil(self.spot_scale_px * 0.5)))
            rx1 = max(0, lbx - pad)
            ry1 = max(0, lby - pad)
            rx2 = min(sw, lbx + lbw + pad)
            ry2 = min(sh, lby + lbh + pad)
            
            roi = filtered[ry1:ry2, rx1:rx2].astype(np.float32)
            roi_bg = np.percentile(roi, 15) if roi.size > 0 else mean_bg
            roi_sub = np.maximum(0.0, roi - roi_bg)
            mass = float(np.sum(roi_sub))
            if mass > 1e-4:
                yy, xx = np.indices(roi_sub.shape)
                final_x = float(np.sum(xx * roi_sub) / mass) + rx1 + crop_x0
                final_y = float(np.sum(yy * roi_sub) / mass) + ry1 + crop_y0

            if algo == TrackingAlgorithm.HYBRID and self.ai_detector.is_loaded:
                patch_size = 64
                center_x = int(round(final_x - crop_x0))
                center_y = int(round(final_y - crop_y0))
                px1 = max(0, min(sw - patch_size, center_x - patch_size // 2)) if sw >= patch_size else 0
                py1 = max(0, min(sh - patch_size, center_y - patch_size // 2)) if sh >= patch_size else 0
                patch = search_frame[py1:min(sh, py1 + patch_size), px1:min(sw, px1 + patch_size)]
                detected_ai, ax, ay, ai_confidence, is_decoy, heatmap = self.ai_detector.detect_spot(
                    patch,
                    min_confidence=self.config.ai_confidence_threshold,
                    enable_decoy_filter=self.config.enable_ai_decoy_filter,
                )
                heatmap_bbox = (crop_x0 + px1, crop_y0 + py1, patch.shape[1], patch.shape[0])
                ai_x = float(crop_x0 + px1 + ax)
                ai_y = float(crop_y0 + py1 + ay)
                # NanoSpot is a local refiner, never a license to jump to a
                # different response inside the crop.  This protects square
                # and saturated beacons while retaining sub-pixel refinement
                # on Gaussian spots.
                if detected_ai and not is_decoy and np.hypot(ai_x - final_x, ai_y - final_y) <= 2.5:
                    final_x, final_y = ai_x, ai_y

        elif algo == TrackingAlgorithm.GAUSSIAN_FIT:
            # Analytical 2D Gaussian Surface Fitting with IWC baseline
            pad = max(3, int(np.ceil(self.spot_scale_px * 0.5)))
            rx1 = max(0, lbx - pad)
            ry1 = max(0, lby - pad)
            rx2 = min(sw, lbx + lbw + pad)
            ry2 = min(sh, lby + lbh + pad)
            
            roi = filtered[ry1:ry2, rx1:rx2].astype(np.float32)
            roi_bg = np.percentile(roi, 15) if roi.size > 0 else mean_bg
            roi_sub = np.maximum(0.0, roi - roi_bg)
            mass = float(np.sum(roi_sub))
            
            if mass > 1e-4:
                yy, xx = np.indices(roi_sub.shape)
                iwc_x = float(np.sum(xx * roi_sub) / mass)
                iwc_y = float(np.sum(yy * roi_sub) / mass)
            else:
                iwc_x = float(lbw / 2.0 + pad)
                iwc_y = float(lbh / 2.0 + pad)

            # Refine with 2D Gaussian log-polynomial peak fit around centroid
            p_x = int(round(iwc_x))
            p_y = int(round(iwc_y))
            if 1 <= p_x < roi.shape[1] - 1 and 1 <= p_y < roi.shape[0] - 1:
                v_center = max(1.0, roi[p_y, p_x])
                v_left = max(1.0, roi[p_y, p_x - 1])
                v_right = max(1.0, roi[p_y, p_x + 1])
                v_up = max(1.0, roi[p_y - 1, p_x])
                v_down = max(1.0, roi[p_y + 1, p_x])
                
                curv_x = v_left - 2.0 * v_center + v_right
                curv_y = v_up - 2.0 * v_center + v_down
                if curv_x < -2.0 and curv_y < -2.0:
                    l_c = np.log(v_center)
                    denom_x = 2.0 * (np.log(v_left) - 2.0 * l_c + np.log(v_right))
                    denom_y = 2.0 * (np.log(v_up) - 2.0 * l_c + np.log(v_down))
                    dx = float((np.log(v_left) - np.log(v_right)) / denom_x) if abs(denom_x) > 1e-5 else 0.0
                    dy = float((np.log(v_up) - np.log(v_down)) / denom_y) if abs(denom_y) > 1e-5 else 0.0
                    dx = np.clip(dx, -0.6, 0.6)
                    dy = np.clip(dy, -0.6, 0.6)
                    final_x = float(p_x + dx) + rx1 + crop_x0
                    final_y = float(p_y + dy) + ry1 + crop_y0
                else:
                    final_x = iwc_x + rx1 + crop_x0
                    final_y = iwc_y + ry1 + crop_y0
            else:
                final_x = iwc_x + rx1 + crop_x0
                final_y = iwc_y + ry1 + crop_y0

        elif algo == TrackingAlgorithm.CORRELATION_NCC:
            # Normalized Cross-Correlation Template Matching
            if self.target_template is None:
                # Initialize template around candidate
                tpad = self.template_size // 2
                tx1 = max(0, lbx + lbw // 2 - tpad)
                ty1 = max(0, lby + lbh // 2 - tpad)
                tx2 = min(sw, tx1 + self.template_size)
                ty2 = min(sh, ty1 + self.template_size)
                if (tx2 - tx1) == self.template_size and (ty2 - ty1) == self.template_size:
                    self.target_template = filtered[ty1:ty2, tx1:tx2].copy()
            else:
                # Run template matching in search frame
                if search_frame.shape[0] >= self.template_size and search_frame.shape[1] >= self.template_size:
                    res = cv2.matchTemplate(search_frame, self.target_template, cv2.TM_CCOEFF_NORMED)
                    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
                    if max_val > 0.4:
                        final_x = float(max_loc[0] + self.template_size / 2.0 + crop_x0)
                        final_y = float(max_loc[1] + self.template_size / 2.0 + crop_y0)

        # Compute classical confidence, then attach scale-aware photometry in
        # full sensor coordinates. Aperture SNR is the filter-facing metric;
        # the legacy dB value remains available to the existing UI.
        noise_floor = max(1.0, std_bg)
        signal_level = max(1.0, best["peak"] - mean_bg)
        photo = self._measure_photometry(
            photometry_frame, photometry_residual,
            (final_x, final_y), (gbx, gby, gbw, gbh),
        )
        snr_db = float(20.0 * np.log10(max(photo.snr_peak or 1e-6, 1e-6)))
        classical_confidence = float(np.clip(signal_level / (3.0 * noise_floor), 0.0, 1.0))
        verifier_confidence = float(best.get("verifier_score", classical_confidence))
        if algo == TrackingAlgorithm.HYBRID:
            confidence = 0.45 * classical_confidence + 0.25 * verifier_confidence
            confidence += 0.30 * (float(ai_confidence) if ai_confidence is not None else verifier_confidence)
            confidence = float(np.clip(confidence, 0.0, 1.0))
        else:
            confidence = classical_confidence

        self.last_candidates = [
            DetectionResult(
                True, float(candidate["x"]), float(candidate["y"]),
                candidate["global_bbox"], gate_box,
                float(candidate["verifier_score"]), float(candidate["peak"]),
                snr_db, algo.value,
            )
            for candidate in sorted(candidates, key=lambda item: item["verifier_score"], reverse=True)
        ]

        return DetectionResult(
            detected=True,
            x=final_x,
            y=final_y,
            bbox=(gbx, gby, gbw, gbh),
            gate_bbox=gate_box,
            confidence=confidence,
            peak_intensity=best["peak"],
            snr_db=snr_db,
            algorithm_used=algo.value,
            heatmap=heatmap,
            heatmap_bbox=heatmap_bbox,
            is_decoy=is_decoy,
            fwhm_px=photo.fwhm_px,
            snr_aperture=photo.snr_aperture,
            snr_peak=photo.snr_peak,
            clipped=photo.clipped,
            saturated_fraction=photo.saturated_fraction,
        )

    def _measure_photometry(
        self,
        frame: np.ndarray,
        residual: np.ndarray,
        center_xy: tuple[float, float],
        bbox: tuple[int, int, int, int],
    ) -> SpotPhotometry:
        photo = measure_spot(frame, residual, center_xy, bbox, self.spot_scale_px)
        if (
            not photo.clipped
            and not photo.saturated
            and photo.snr_aperture is not None
            and photo.snr_aperture >= 5.0
        ):
            measured = float(np.clip(
                photo.fwhm_px,
                self.config.minimum_fwhm_px,
                self.config.maximum_fwhm_px,
            ))
            self.spot_scale_px = 0.85 * self.spot_scale_px + 0.15 * measured
        return photo
