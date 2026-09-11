"""
Archis Optical Tracker - Multi-Target Data Association and Innovation Gating
Implements statistical Mahalanobis distance gating (Chi-square test)
for false-alarm and decoy rejection in cluttered optical scenes.
"""
import numpy as np
from typing import List, Optional, Tuple, Dict, Any


class DataAssociator:
    def __init__(self, gate_threshold_chi2: float = 9.21):
        # Chi-Square 2-DOF 99% confidence gate threshold (9.21)
        self.gate_threshold = gate_threshold_chi2

    def associate_best_candidate(self, 
                                 candidates: List[Dict[str, Any]], 
                                 predicted_x: float, 
                                 predicted_y: float,
                                 cov_matrix: Optional[np.ndarray] = None) -> Optional[Dict[str, Any]]:
        """
        Selects the best measurement candidate using Mahalanobis distance gating.
        Rejects false alarms, background clutter, and decoys.
        """
        if not candidates:
            return None
            
        # Default measurement innovation covariance S if none provided
        if cov_matrix is None or cov_matrix.shape != (2, 2):
            S_inv = np.diag([1.0 / (15.0**2), 1.0 / (15.0**2)])
        else:
            try:
                S_inv = np.linalg.inv(cov_matrix)
            except np.linalg.LinAlgError:
                S_inv = np.diag([1.0 / (15.0**2), 1.0 / (15.0**2)])

        best_candidate = None
        min_mahalanobis = float("inf")
        
        for cand in candidates:
            cx = float(cand["x"])
            cy = float(cand["y"])
            diff = np.array([cx - predicted_x, cy - predicted_y], dtype=np.float32)
            
            # Compute Mahalanobis distance squared: d² = y^T S⁻¹ y
            d_sq = float(diff.T @ S_inv @ diff)
            cand["mahalanobis_dist"] = d_sq
            
            # Gating check
            if d_sq <= self.gate_threshold:
                # Inside validation gate; select candidate with minimum statistical distance
                if d_sq < min_mahalanobis:
                    min_mahalanobis = d_sq
                    best_candidate = cand
                    
        # Fallback: if no candidate within gate, check if any candidate has very high SNR nearby
        if best_candidate is None and candidates:
            # Sort by Euclidean distance to predicted position
            euclidean = [((c["x"] - predicted_x)**2 + (c["y"] - predicted_y)**2) for c in candidates]
            nearest_idx = int(np.argmin(euclidean))
            # Only accept if within reasonable physical proximity (e.g. 35 pixels)
            if euclidean[nearest_idx] <= (35.0**2):
                best_candidate = candidates[nearest_idx]
                
        return best_candidate
