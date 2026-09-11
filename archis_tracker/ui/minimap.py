"""
Archis Optical Tracker - Global Virtual Scene Minimap
Provides full 2000x2000 global overview with target trajectory trails,
secondary decoys, and interactive Click-to-Designate / Drop-Decoy functionality.
"""
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from typing import Optional, List
from ..core.target import TargetBeacon
from ..core.camera import VirtualCamera


class MinimapWidget(QWidget):
    designate_world_signal = pyqtSignal(float, float)  # (world_x, world_y)
    spawn_decoy_world_signal = pyqtSignal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(220, 220)
        
        self.world_w: float = 2000.0
        self.world_h: float = 2000.0
        self.primary_target: Optional[TargetBeacon] = None
        self.camera: Optional[VirtualCamera] = None
        self.secondary_targets: List[TargetBeacon] = []
        
        # Internal coordinate transform cache
        self.last_offset_x: float = 0.0
        self.last_offset_y: float = 0.0
        self.last_side: float = 200.0

    def set_references(self, primary_target: TargetBeacon, camera: VirtualCamera, 
                       secondary_targets: List[TargetBeacon]):
        self.primary_target = primary_target
        self.camera = camera
        self.secondary_targets = secondary_targets
        self.update()

    def mousePressEvent(self, event):
        if self.last_side <= 0.01:
            return
        pos = event.position()
        mx = (pos.x() - self.last_offset_x) / self.last_side
        my = (pos.y() - self.last_offset_y) / self.last_side
        
        if 0.0 <= mx <= 1.0 and 0.0 <= my <= 1.0:
            world_x = float(mx * self.world_w)
            world_y = float(my * self.world_h)
            if event.button() == Qt.MouseButton.LeftButton:
                self.designate_world_signal.emit(world_x, world_y)
            elif event.button() == Qt.MouseButton.RightButton:
                self.spawn_decoy_world_signal(world_x, world_y)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        side = min(rect.width(), rect.height()) - 10
        offset_x = (rect.width() - side) / 2.0
        offset_y = (rect.height() - side) / 2.0
        
        self.last_offset_x = offset_x
        self.last_offset_y = offset_y
        self.last_side = side
        
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

        # 2. Coordinate Grid Lines
        painter.setPen(QPen(QColor(30, 38, 54), 1.0, Qt.PenStyle.DotLine))
        for g in range(500, int(self.world_w), 500):
            gx, _ = to_map(g, 0)
            painter.drawLine(QPointF(gx, offset_y), QPointF(gx, offset_y + side))
            _, gy = to_map(0, g)
            painter.drawLine(QPointF(offset_x, gy), QPointF(offset_x + side, gy))

        # 3. Primary Target Trajectory Trail
        if self.primary_target and len(self.primary_target.trail) > 1:
            painter.setPen(QPen(QColor(56, 189, 248, 80), 1.0))
            pts = list(self.primary_target.trail)
            for i in range(len(pts) - 1):
                p1_x, p1_y = to_map(pts[i][0], pts[i][1])
                p2_x, p2_y = to_map(pts[i+1][0], pts[i+1][1])
                painter.drawLine(QPointF(p1_x, p1_y), QPointF(p2_x, p2_y))

        # 4. Secondary Targets / Decoys
        for decoy in self.secondary_targets:
            dx, dy = to_map(decoy.x, decoy.y)
            painter.setPen(QPen(QColor(249, 115, 22), 1.0))
            painter.setBrush(QBrush(QColor(249, 115, 22, 180)))
            painter.drawEllipse(QPointF(dx, dy), 2.5, 2.5)

        # 5. Camera Viewport Bounding Frustum (640x480 box in world coordinates)
        if self.camera:
            cam_wx = self.camera.world_x
            cam_wy = self.camera.world_y
            cam_w = self.camera.width    # 640
            cam_h = self.camera.height   # 480
            
            box_x, box_y = to_map(cam_wx - cam_w / 2.0, cam_wy - cam_h / 2.0)
            box_w = (cam_w / self.world_w) * side
            box_h = (cam_h / self.world_h) * side
            
            painter.setPen(QPen(QColor(255, 255, 255, 140), 1.0))
            painter.setBrush(QBrush(QColor(255, 255, 255, 12)))
            painter.drawRect(QRectF(box_x, box_y, box_w, box_h))
            
            # Camera Boresight Center
            ccx, ccy = to_map(cam_wx, cam_wy)
            painter.setPen(QPen(QColor(255, 255, 255, 180), 1.0))
            painter.drawLine(QPointF(ccx - 3, ccy), QPointF(ccx + 3, ccy))
            painter.drawLine(QPointF(ccx, ccy - 3), QPointF(ccx, ccy + 3))

        # 6. Primary Target Marker
        if self.primary_target:
            tx, ty = to_map(self.primary_target.x, self.primary_target.y)
            painter.setPen(QPen(QColor(74, 222, 128), 1.5))
            painter.setBrush(QBrush(QColor(74, 222, 128, 220)))
            painter.drawEllipse(QPointF(tx, ty), 3.5, 3.5)

        # 7. Minimap Header & Hint
        painter.setFont(QFont("Consolas", 8))
        painter.setPen(QColor(148, 163, 184))
        painter.drawText(int(offset_x + 6), int(offset_y + 14), "GLOBAL SPACE [2000x2000]")
