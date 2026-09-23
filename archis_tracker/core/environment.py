"""
Archis Optical Tracker - Virtual Environment Generator
Generates a configurable 2000x2000+ virtual world with starfield and calibration grid.
"""
import numpy as np
from typing import Tuple, List, Optional
from .config import EnvironmentConfig


class VirtualEnvironment:
    def __init__(self, config: Optional[EnvironmentConfig] = None):
        self.config = config or EnvironmentConfig()
        self.width = self.config.screen_width
        self.height = self.config.screen_height
        
        # Generate persistent stars without modifying NumPy's process-global
        # random state. The scenario seed therefore owns every stochastic
        # element in a run.
        rng = np.random.default_rng(self.config.random_seed)
        self.star_x = rng.uniform(20, self.width - 20, self.config.star_count).astype(np.float32)
        self.star_y = rng.uniform(20, self.height - 20, self.config.star_count).astype(np.float32)
        self.star_brightness = rng.uniform(40, 180, self.config.star_count).astype(np.float32)
        self.star_size = rng.choice([1, 1, 1, 2], size=self.config.star_count)
        
        # Global background base intensity
        self.bg_intensity = self.config.background_intensity

    def render_viewport_patch(self, center_x: float, center_y: float, 
                              vp_width: int, vp_height: int) -> np.ndarray:
        """
        Efficiently generates and extracts a 640x480 sub-region around (center_x, center_y)
        from the 2000x2000 virtual space, rendering stars and grid lines on-the-fly.
        """
        # Create base canvas with low ambient background noise
        patch = np.full((vp_height, vp_width), self.bg_intensity, dtype=np.float32)
        
        # Viewport bounds in world coordinates
        x_min = center_x - vp_width / 2.0
        y_min = center_y - vp_height / 2.0
        x_max = x_min + vp_width
        y_max = y_min + vp_height
        
        # 1. Render grid lines
        grid_sp = self.config.grid_spacing
        first_grid_x = int(np.ceil(x_min / grid_sp)) * grid_sp
        for gx in range(first_grid_x, int(x_max) + 1, grid_sp):
            px = int(gx - x_min)
            if 0 <= px < vp_width:
                patch[:, px] += 8.0  # Faint coordinate grid lines
                
        first_grid_y = int(np.ceil(y_min / grid_sp)) * grid_sp
        for gy in range(first_grid_y, int(y_max) + 1, grid_sp):
            py = int(gy - y_min)
            if 0 <= py < vp_height:
                patch[py, :] += 8.0
                
        # 2. Render visible background stars in this viewport
        mask = (self.star_x >= x_min) & (self.star_x < x_max) &                (self.star_y >= y_min) & (self.star_y < y_max)
        
        vis_sx = (self.star_x[mask] - x_min).astype(int)
        vis_sy = (self.star_y[mask] - y_min).astype(int)
        vis_b = self.star_brightness[mask]
        vis_sz = self.star_size[mask]
        
        for px, py, b, sz in zip(vis_sx, vis_sy, vis_b, vis_sz):
            if 0 <= px < vp_width and 0 <= py < vp_height:
                if sz == 1:
                    patch[py, px] = min(255.0, patch[py, px] + b)
                else:
                    y1 = max(0, py - 1)
                    y2 = min(vp_height, py + 2)
                    x1 = max(0, px - 1)
                    x2 = min(vp_width, px + 2)
                    patch[y1:y2, x1:x2] += b * 0.75
                    
        return patch
