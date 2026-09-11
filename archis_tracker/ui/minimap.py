"""
Archis Optical Tracker - Global Virtual Scene Minimap
Provides full 2000x2000 global overview with target trajectory trails and camera viewport frustum.
"""
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont
from PyQt6.QtCore import Qt, QRectF, QPointF
from typing import Optional, List
from ..core.target import TargetBeacon
from ..core.camera import VirtualCamera


class MinimapWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(220, 220)
        
        self.world_w: float = 2000.0
        self.world_h: float = 2000.0
        self.primary_target: Optional[TargetBeacon] = None
        self.camera: Optional[VirtualCamera] = None
        self.secondary_targets: List[TargetBeacon] = []

    def set_references(self, primary_target: TargetBeacon, camera: VirtualCamera, 
                       secondary_targets: List[TargetBeacon]):
        self.primary_target = primary_target
        self.camera = camera
        self.secondary_targets = secondary_targets
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        side = min(rect.width(), rect.height()) - 10
        offset_x = (rect.width() - side) / 2.0
        offset_y = (rect.height() - side) / 2.0
        
        # 1. Background
        painter.fillRect(rect, QColor(12, 15, 22))
        map_rect = QRectF(offset_x, offset_y, side, side)
        painter.fillRect(map_rect, QColor(17, 21, 31))
        painter.setPen(QPen(QColor(40, 48, 68), 1.2))
        painter.drawRect(map_rect)
        
        def to_map(wx, wy):
            mx = offset_x + (wx / self.world_w) * side
            my = offset_y + (wy / self.world_h) * side
            return mx, my

        # 2. Grid lines
        painter.setPen(QPen(QColor(30, 38, 54), 1.0, Qt.PenStyle.DotLine))
        for g in range(500, int(self.world_w), 500):
            gx, _ = to_map(g, 0)
            painter.drawLine(QPointF(gx, offset_y), QPointF(gx, offset_y + side))
            _, gy = to_map(0, g)
            painter.drawLine(QPointF(offset_x, gy), QPointF(offset_x + side, gy))

        # 3. Target Trajectory Trail
        if self.primary_target and len(self.primary_target.trail) > 1:
            painter.setPen(QPen(QColor(56, 189, 248, 80), 1.0))
            pts = list(self.primary_target.trail)
            for i in range(len(pts) - 1):
                p1_x, p1_y = to_map(pts[i][0], pts[i][1])
                p2_x, p2_y = to_map(pts[i+1][0], pts[i+1][1])
                painter.drawLine(QPointF(p1_x, p1_y), QPointF(p2_x, p2_y))

        # 4. Camera Viewport Bounding Frustum (640x480 box in world coordinates)
        if self.camera:
            cam_wx = self.camera.world_x
            cam_wy = self.camera.world_y
            cam_w = self.camera.width    # 640
            cam_h = self.camera.height   # 480
            
            x1, y1 = to_map(cam_wx - cam_w / 2.0, cam_wy - cam_h / 2.0)
            x2, y2 = to_map(cam_wx + cam_w / 2.0, cam_wy + cam_h / 2.0)
            
            frustum_rect = QRectF(x1, y1, x2 - x1, y2 - y1)
            # Semi-transparent camera FOV fill
            painter.setBrush(QBrush(QColor(56, 189, 248, 25)))
            painter.setPen(QPen(QColor(56, 189, 248, 180), 1.2))
            painter.drawRect(frustum_rect)
            
            # Viewport Center (Boresight in world coordinates)
            cx, cy = to_map(cam_wx, cam_wy)
            painter.setPen(QPen(QColor(255, 255, 255), 1.0))
            painter.setBrush(QBrush(QColor(56, 189, 248)))
            painter.drawEllipse(QPointF(cx, cy), 2.5, 2.5)

        # 5. Primary Target Spot
        if self.primary_target:
            tx, ty = to_map(self.primary_target.x, self.primary_target.y)
            painter.setPen(QPen(QColor(255, 255, 255), 1.2))
            painter.setBrush(QBrush(QColor(74, 222, 128)))
            painter.drawEllipse(QPointF(tx, ty), 4.0, 4.0)

        # 6. Secondary Decoy Targets
        for sec in self.secondary_targets:
            sx, sy = to_map(sec.x, sec.y)
            painter.setPen(QPen(QColor(244, 63, 94), 1.0))
            painter.setBrush(QBrush(QColor(244, 63, 94, 180)))
            painter.drawEllipse(QPointF(sx, sy), 3.0, 3.0)

        # 7. Minimap Header
        painter.setFont(QFont("Consolas", 8))
        painter.setPen(QColor(148, 163, 184))
        painter.drawText(int(offset_x + 6), int(offset_y + 14), "VIRTUAL SCENE (2000x2000)")
