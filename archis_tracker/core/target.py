"""
Archis Optical Tracker - Moving Optical Beacon Target Generator
Implements Beacon Spot generator with selectable shapes and kinematic trajectories.
"""
import numpy as np
from typing import Tuple, List, Optional
from collections import deque
from .config import TargetConfig, TargetShape, MotionTrajectory


class TargetBeacon:
    def __init__(self, target_id: int, config: Optional[TargetConfig] = None, 
                 is_primary: bool = True):
        self.target_id = target_id
        self.config = config or TargetConfig()
        self.is_primary = is_primary
        self.rng = np.random.default_rng(self.config.random_seed + target_id)
        
        # Current world coordinates & kinematics
        self.x: float = self.config.initial_x if self.config.initial_x is not None else 1000.0
        self.y: float = self.config.initial_y if self.config.initial_y is not None else 1000.0
        self.vx: float = 0.0
        self.vy: float = 0.0
        self.ax: float = 0.0
        self.ay: float = 0.0
        
        # Motion parameters
        self.time_elapsed: float = 0.0
        self.phase = 0.0
        self.linear_heading = np.pi / 4.0
        self.shape: TargetShape = self.config.shape
        self.size: int = self.config.size  # 5-20 pixels
        self.intensity: float = self.config.intensity
        self.trajectory: MotionTrajectory = self.config.trajectory
        self.speed: float = self.config.speed
        self.radius: float = self.config.trajectory_radius
        self.omega: float = self.config.trajectory_omega
        
        # Center anchor for orbital/circular/figure-8 motions
        self.center_x: float = self.x
        self.center_y: float = self.y
        
        # Random motion state (Brownian with momentum)
        self.random_heading: float = float(self.rng.uniform(0, 2 * np.pi))
        
        # Trail history for visualization
        self.trail: deque = deque(maxlen=200)
        self.trail.append((self.x, self.y))

    def reset_position(self, x: float, y: float):
        self.x = x
        self.y = y
        self.center_x = x
        self.center_y = y
        self.vx = 0.0
        self.vy = 0.0
        self.time_elapsed = 0.0
        self.phase = 0.0
        self.ax = self.ay = 0.0
        self.rng = np.random.default_rng(self.config.random_seed + self.target_id)
        self.random_heading = float(self.rng.uniform(0, 2 * np.pi))
        self.trail.clear()
        self.trail.append((self.x, self.y))

    def update(self, dt: float, world_width: float = 2000.0, world_height: float = 2000.0):
        """
        Updates kinematic state (position, velocity, acceleration) according to selected trajectory.
        """
        if dt <= 0:
            return
        self.time_elapsed += dt
        self.phase += max(0.0, self.speed) * dt / max(10.0, self.radius)
        prev_x, prev_y = self.x, self.y
        prev_vx, prev_vy = self.vx, self.vy
        
        if self.trajectory == MotionTrajectory.STRAIGHT_LINE:
            # Linear trajectory with boundary bounce
            self.vx = self.speed * np.cos(self.linear_heading)
            self.vy = self.speed * np.sin(self.linear_heading)
                
            self.x += self.vx * dt
            self.y += self.vy * dt
            
            # Boundary bounce with margin
            # Keep the target centre inside the region that a 640x480 camera
            # can physically centre while its viewport remains in the world.
            margin = min(320.0, world_width / 2.0 - 1.0, world_height / 2.0 - 1.0)
            if self.x <= margin:
                self.x = margin
                self.vx = abs(self.vx)
            elif self.x >= world_width - margin:
                self.x = world_width - margin
                self.vx = -abs(self.vx)
                
            if self.y <= margin:
                self.y = margin
                self.vy = abs(self.vy)
            elif self.y >= world_height - margin:
                self.y = world_height - margin
                self.vy = -abs(self.vy)
            self.linear_heading = np.arctan2(self.vy, self.vx)

        elif self.trajectory == MotionTrajectory.CIRCULAR:
            # Smooth circle tangent to origin (starts exactly at center_x, center_y)
            self.x = self.center_x + self.radius * np.sin(self.phase)
            self.y = self.center_y + self.radius * (1.0 - np.cos(self.phase))

        elif self.trajectory == MotionTrajectory.FIGURE_OF_8:
            # Lemniscate of Gerono / Lissajous Figure-8 (starts at center_x, center_y)
            self.x = self.center_x + self.radius * np.sin(self.phase)
            self.y = self.center_y + (self.radius * 0.5) * np.sin(2 * self.phase)

        elif self.trajectory == MotionTrajectory.RANDOM:
            # Smooth Ornstein-Uhlenbeck Brownian drift
            heading_change = self.rng.normal(0.0, 0.4) * dt * 5.0
            self.random_heading += heading_change
            
            # Repel from boundaries
            margin = min(320.0, world_width / 2.0 - 1.0, world_height / 2.0 - 1.0)
            if self.x < margin:
                self.random_heading = 0.0
            elif self.x > world_width - margin:
                self.random_heading = np.pi
            if self.y < margin:
                self.random_heading = np.pi / 2.0
            elif self.y > world_height - margin:
                self.random_heading = -np.pi / 2.0
                
            self.vx = self.speed * np.cos(self.random_heading)
            self.vy = self.speed * np.sin(self.random_heading)
            self.x += self.vx * dt
            self.y += self.vy * dt

        elif self.trajectory == MotionTrajectory.SPIRAL:
            # Expanding / contracting spiral from center
            spiral_r = self.radius * 0.5 * (1.0 - np.cos(self.phase * 0.25))
            self.x = self.center_x + spiral_r * np.sin(self.phase)
            self.y = self.center_y + spiral_r * np.cos(self.phase)

        elif self.trajectory == MotionTrajectory.SINUSOIDAL:
            # Sinusoidal wave motion along X with vertical oscillation
            self.x = self.center_x + self.radius * np.sin(self.phase)
            self.y = self.center_y + 80.0 * np.sin(2.0 * self.phase)

        # Compute numerical velocity and acceleration
        if dt > 1e-5:
            new_vx = (self.x - prev_x) / dt
            new_vy = (self.y - prev_y) / dt
            self.ax = (new_vx - prev_vx) / dt
            self.ay = (new_vy - prev_vy) / dt
            self.vx = new_vx
            self.vy = new_vy

        self.trail.append((self.x, self.y))

    def render_onto_viewport(self, canvas: np.ndarray, cam_center_x: float, cam_center_y: float):
        """
        Renders the beacon spot onto the 640x480 viewport canvas using continuous sub-pixel optics.
        """
        vp_h, vp_w = canvas.shape
        # Target position in viewport coordinates (continuous sub-pixel)
        tx = self.x - (cam_center_x - vp_w / 2.0)
        ty = self.y - (cam_center_y - vp_h / 2.0)
        
        # Check if target is within viewport bounds (with optical halo margin)
        s = max(5.0, min(25.0, float(self.size)))
        rad = s * 0.5
        halo = rad + 3.0
        
        if (tx + halo < 0 or tx - halo >= vp_w or
            ty + halo < 0 or ty - halo >= vp_h):
            return  # Target outside FOV
            
        # Integer pixel grid bounds
        x1 = max(0, int(np.floor(tx - halo)))
        x2 = min(vp_w, int(np.ceil(tx + halo)) + 1)
        y1 = max(0, int(np.floor(ty - halo)))
        y2 = min(vp_h, int(np.ceil(ty + halo)) + 1)
        
        if y1 >= y2 or x1 >= x2:
            return

        yy, xx = np.mgrid[y1:y2, x1:x2]
        dx = xx - tx
        dy = yy - ty
        dist_sq = dx * dx + dy * dy
        dist = np.sqrt(dist_sq)

        if self.shape == TargetShape.SQUARE:
            # Anti-aliased square box using signed distance field
            dist_box = np.maximum(np.abs(dx) - rad, np.abs(dy) - rad)
            profile = np.clip(0.5 - dist_box, 0.0, 1.0)
            canvas[y1:y2, x1:x2] = np.maximum(canvas[y1:y2, x1:x2], self.intensity * profile)

        elif self.shape == TargetShape.CIRCLE:
            # Anti-aliased circular disk using sub-pixel smooth edge
            profile = np.clip(rad + 0.5 - dist, 0.0, 1.0)
            canvas[y1:y2, x1:x2] = np.maximum(canvas[y1:y2, x1:x2], self.intensity * profile)

        elif self.shape == TargetShape.GAUSSIAN:
            # 2D Gaussian beam / Airy disc core
            sigma = max(1.2, rad / 2.2)
            profile = np.exp(-dist_sq / (2.0 * sigma * sigma))
            canvas[y1:y2, x1:x2] = np.maximum(canvas[y1:y2, x1:x2], self.intensity * profile)

        elif self.shape == TargetShape.CROSSHAIR:
            # Crosshair with central flare
            line_w = 1.0
            cross_x = np.clip(1.0 - (np.abs(dx) - line_w * 0.5), 0.0, 1.0) * (np.abs(dy) <= rad)
            cross_y = np.clip(1.0 - (np.abs(dy) - line_w * 0.5), 0.0, 1.0) * (np.abs(dx) <= rad)
            center_flare = np.exp(-dist_sq / 2.0)
            profile = np.clip(cross_x + cross_y + center_flare, 0.0, 1.0)
            canvas[y1:y2, x1:x2] = np.maximum(canvas[y1:y2, x1:x2], self.intensity * profile)


class TargetManager:
    """
    Production-grade multi-target and decoy coordinator.
    Handles designated primary optical beacon plus user-injected clutter and false alarms.
    """
    def __init__(self, primary_config: Optional[TargetConfig] = None):
        self.primary_target = TargetBeacon(target_id=1, config=primary_config, is_primary=True)
        self.secondary_targets: List[TargetBeacon] = []
        self._next_id = 2

    def add_decoy(self, x: float, y: float, shape: TargetShape = TargetShape.GAUSSIAN,
                  size: int = 10, speed: float = 35.0,
                  trajectory: MotionTrajectory = MotionTrajectory.STRAIGHT_LINE,
                  intensity: float = 220.0, random_seed: int = 26169,
                  range_m: Optional[float] = None,
                  orientation_deg: Optional[Tuple[float, float, float]] = None) -> TargetBeacon:
        cfg = TargetConfig(
            shape=shape, size=size, speed=speed, trajectory=trajectory,
            intensity=intensity, initial_x=x, initial_y=y, random_seed=random_seed,
            range_m=range_m, orientation_deg=orientation_deg,
        )
        decoy = TargetBeacon(target_id=self._next_id, config=cfg, is_primary=False)
        self._next_id += 1
        self.secondary_targets.append(decoy)
        return decoy

    def clear_decoys(self):
        self.secondary_targets.clear()

    def update(self, dt: float, world_width: float = 2000.0, world_height: float = 2000.0):
        self.primary_target.update(dt, world_width, world_height)
        for t in self.secondary_targets:
            t.update(dt, world_width, world_height)

    def render_all_onto_viewport(self, canvas: np.ndarray, cam_center_x: float, cam_center_y: float):
        # Render secondaries first, then primary on top
        for t in self.secondary_targets:
            t.render_onto_viewport(canvas, cam_center_x, cam_center_y)
        self.primary_target.render_onto_viewport(canvas, cam_center_x, cam_center_y)

    def designate_nearest(self, world_x: float, world_y: float) -> Optional[TargetBeacon]:
        """Designates the target closest to (world_x, world_y) as primary."""
        all_targets = [self.primary_target] + self.secondary_targets
        if not all_targets:
            return None
        dists = [(t.x - world_x)**2 + (t.y - world_y)**2 for t in all_targets]
        nearest_idx = int(np.argmin(dists))
        if nearest_idx > 0:
            # Swap primary and secondary
            new_primary = self.secondary_targets[nearest_idx - 1]
            old_primary = self.primary_target
            old_primary.is_primary = False
            new_primary.is_primary = True
            self.secondary_targets[nearest_idx - 1] = old_primary
            self.primary_target = new_primary
        return self.primary_target
