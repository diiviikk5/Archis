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
        
        # Current world coordinates & kinematics
        self.x: float = self.config.initial_x if self.config.initial_x is not None else 1000.0
        self.y: float = self.config.initial_y if self.config.initial_y is not None else 1000.0
        self.vx: float = 0.0
        self.vy: float = 0.0
        self.ax: float = 0.0
        self.ay: float = 0.0
        
        # Motion parameters
        self.time_elapsed: float = 0.0
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
        self.random_heading: float = np.random.uniform(0, 2 * np.pi)
        
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
        self.trail.clear()
        self.trail.append((self.x, self.y))

    def update(self, dt: float, world_width: float = 2000.0, world_height: float = 2000.0):
        """
        Updates kinematic state (position, velocity, acceleration) according to selected trajectory.
        """
        self.time_elapsed += dt
        t = self.time_elapsed
        prev_x, prev_y = self.x, self.y
        
        if self.trajectory == MotionTrajectory.STRAIGHT_LINE:
            # Linear trajectory with boundary bounce
            if abs(self.vx) < 1e-3 and abs(self.vy) < 1e-3:
                angle = np.pi / 4.0
                self.vx = self.speed * np.cos(angle)
                self.vy = self.speed * np.sin(angle)
                
            self.x += self.vx * dt
            self.y += self.vy * dt
            
            # Boundary bounce with margin
            margin = 50.0
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

        elif self.trajectory == MotionTrajectory.CIRCULAR:
            # Smooth circle tangent to origin (starts exactly at center_x, center_y)
            w = (self.speed / max(10.0, self.radius))
            self.x = self.center_x + self.radius * np.sin(w * t)
            self.y = self.center_y + self.radius * (1.0 - np.cos(w * t))

        elif self.trajectory == MotionTrajectory.FIGURE_OF_8:
            # Lemniscate of Gerono / Lissajous Figure-8 (starts at center_x, center_y)
            w = (self.speed / max(10.0, self.radius))
            self.x = self.center_x + self.radius * np.sin(w * t)
            self.y = self.center_y + (self.radius * 0.5) * np.sin(2 * w * t)

        elif self.trajectory == MotionTrajectory.RANDOM:
            # Smooth Ornstein-Uhlenbeck Brownian drift
            heading_change = np.random.normal(0.0, 0.4) * dt * 5.0
            self.random_heading += heading_change
            
            # Repel from boundaries
            margin = 150.0
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
            spiral_r = (t * 22.0) % (self.radius * 1.2)
            w = 0.7
            self.x = self.center_x + spiral_r * np.sin(w * t)
            self.y = self.center_y + spiral_r * (1.0 - np.cos(w * t))

        elif self.trajectory == MotionTrajectory.SINUSOIDAL:
            # Sinusoidal wave motion along X with vertical oscillation
            w = 0.8
            self.x = self.center_x + (self.speed * t) % (world_width - 400.0)
            self.y = self.center_y + 80.0 * np.sin(w * t)

        # Compute numerical velocity and acceleration
        if dt > 1e-5:
            new_vx = (self.x - prev_x) / dt
            new_vy = (self.y - prev_y) / dt
            self.ax = (new_vx - self.vx) / dt
            self.ay = (new_vy - self.vy) / dt
            self.vx = new_vx
            self.vy = new_vy

        self.trail.append((self.x, self.y))

    def render_onto_viewport(self, canvas: np.ndarray, cam_center_x: float, cam_center_y: float):
        """
        Renders the beacon spot onto the 640x480 viewport canvas based on its shape and size.
        """
        vp_h, vp_w = canvas.shape
        # Target position in viewport coordinates
        target_vp_x = self.x - (cam_center_x - vp_w / 2.0)
        target_vp_y = self.y - (cam_center_y - vp_h / 2.0)
        
        # Check if target is within viewport bounds (with margin)
        half_sz = self.size / 2.0
        if (target_vp_x + half_sz < 0 or target_vp_x - half_sz >= vp_w or
            target_vp_y + half_sz < 0 or target_vp_y - half_sz >= vp_h):
            return  # Target is outside camera FOV
            
        # Draw target according to selected shape
        ix = int(round(target_vp_x))
        iy = int(round(target_vp_y))
        s = max(5, min(20, self.size))
        rad = s // 2
        
        y1 = max(0, iy - rad)
        y2 = min(vp_h, iy + rad + 1)
        x1 = max(0, ix - rad)
        x2 = min(vp_w, ix + rad + 1)
        
        if y1 >= y2 or x1 >= x2:
            return

        if self.shape == TargetShape.SQUARE:
            # Uniform square spot (Default per specification)
            canvas[y1:y2, x1:x2] = np.maximum(canvas[y1:y2, x1:x2], self.intensity)

        elif self.shape == TargetShape.CIRCLE:
            # Circular disc
            yy, xx = np.ogrid[y1 - iy:y2 - iy, x1 - ix:x2 - ix]
            mask = (xx * xx + yy * yy) <= (rad * rad)
            canvas[y1:y2, x1:x2][mask] = np.maximum(canvas[y1:y2, x1:x2][mask], self.intensity)

        elif self.shape == TargetShape.GAUSSIAN:
            # 2D Gaussian Airy Disc profile
            yy, xx = np.ogrid[y1:y2, x1:x2]
            sigma = max(1.0, s / 3.0)
            dist_sq = (xx - target_vp_x)**2 + (yy - target_vp_y)**2
            spot = self.intensity * np.exp(-dist_sq / (2.0 * sigma**2))
            canvas[y1:y2, x1:x2] = np.maximum(canvas[y1:y2, x1:x2], spot)

        elif self.shape == TargetShape.CROSSHAIR:
            # Crosshair spot
            canvas[y1:y2, ix] = np.maximum(canvas[y1:y2, ix], self.intensity)
            canvas[iy, x1:x2] = np.maximum(canvas[iy, x1:x2], self.intensity)
            # Center bright dot
            canvas[max(0, iy-1):min(vp_h, iy+2), max(0, ix-1):min(vp_w, ix+2)] = self.intensity
