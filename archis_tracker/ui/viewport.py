"""Sensor image presentation. Overlays never modify detector input."""
import numpy as np
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QImage, QColor, QPen
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from ..core.config import TrackingState


class ViewportWidget(QWidget):
    designate_target_signal = pyqtSignal(float, float)
    spawn_decoy_signal = pyqtSignal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 240)
        self.frame_image = None
        self.detection = None
        self.pred_x, self.pred_y = 320.0, 240.0
        self.state = TrackingState.IDLE
        self.error_px = 0.0
        self.show_crosshair = True
        self.show_alignment_rings = False
        self.show_detection = True
        self.show_prediction = False
        self.show_error_vector = False
        self.show_gate = False
        self.show_heatmap = False
        self.last_scale = 1.0
        self.last_offset_x = self.last_offset_y = 0.0
        self.frame_width, self.frame_height = 640, 480
        self.setToolTip("Left-click to designate; right-click to add a simulated decoy")

    def update_frame(self, frame_np, detection, pred_x, pred_y, state,
                     pan_deg, tilt_deg, fps, latency_ms, error_px, rms_error_px):
        h, w = frame_np.shape
        self.frame_width, self.frame_height = w, h
        frame_np = np.ascontiguousarray(frame_np)
        self.frame_image = QImage(frame_np.data, w, h, frame_np.strides[0],
                                  QImage.Format.Format_Grayscale8).copy()
        self.detection = detection
        self.pred_x, self.pred_y = pred_x, pred_y
        self.state, self.error_px = state, error_px
        self.update()

    def mousePressEvent(self, event):
        if self.frame_image is None or self.last_scale <= 0:
            return
        vx = (event.position().x() - self.last_offset_x) / self.last_scale
        vy = (event.position().y() - self.last_offset_y) / self.last_scale
        if 0 <= vx < self.frame_width and 0 <= vy < self.frame_height:
            if event.button() == Qt.MouseButton.LeftButton:
                self.designate_target_signal.emit(vx, vy)
            elif event.button() == Qt.MouseButton.RightButton:
                self.spawn_decoy_signal.emit(vx, vy)

    def paintEvent(self, event):
        painter = QPainter(self)
        self._draw(painter, self.width(), self.height(), record_transform=True)

    def render_image(self, width: int = 640, height: int = 480) -> QImage:
        image = QImage(width, height, QImage.Format.Format_ARGB32)
        image.fill(QColor("#101112"))
        painter = QPainter(image)
        self._draw(painter, width, height, record_transform=False)
        painter.end()
        return image

    def _draw(self, painter: QPainter, width: int, height: int, *, record_transform: bool):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.fillRect(QRectF(0, 0, width, height), QColor("#101112"))
        if self.frame_image is None:
            painter.setPen(QColor("#8c9096"))
            painter.drawText(QRectF(0, 0, width, height), Qt.AlignmentFlag.AlignCenter, "Sensor ready")
            return
        scale = min(width / self.frame_width, height / self.frame_height)
        rw, rh = self.frame_width * scale, self.frame_height * scale
        ox, oy = (width-rw)/2, (height-rh)/2
        if record_transform:
            self.last_scale, self.last_offset_x, self.last_offset_y = scale, ox, oy
        image_rect = QRectF(ox, oy, rw, rh)
        painter.drawImage(image_rect, self.frame_image)
        painter.setClipRect(image_rect)

        def point(x, y):
            return QPointF(ox+x*scale, oy+y*scale)

        center = point(self.frame_width/2, self.frame_height/2)
        detection = self.detection
        if self.show_alignment_rings:
            painter.setPen(QPen(QColor(74, 222, 128, 65), 1))
            for fraction in (0.125, 0.25, 0.375):
                radius = min(rw, rh) * fraction
                painter.drawEllipse(center, radius, radius)
        if self.show_heatmap and detection is not None and detection.heatmap is not None:
            bounds = getattr(detection, "heatmap_bbox", None)
            if bounds is not None:
                heat = np.clip(detection.heatmap, 0, 1)
                rgba = np.zeros((*heat.shape, 4), dtype=np.uint8)
                rgba[..., :3] = (58, 192, 211)
                rgba[..., 3] = (heat * 100).astype(np.uint8)
                hh, hw = heat.shape
                overlay = QImage(rgba.data, hw, hh, hw*4, QImage.Format.Format_RGBA8888)
                x, y, w, h = bounds
                painter.drawImage(QRectF(ox+x*scale, oy+y*scale, w*scale, h*scale), overlay)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        if self.show_gate and detection is not None and detection.gate_bbox:
            x, y, w, h = detection.gate_bbox
            painter.setPen(QPen(QColor(150, 157, 162, 100), 1, Qt.PenStyle.DashLine))
            painter.drawRect(QRectF(ox+x*scale, oy+y*scale, w*scale, h*scale))
        if self.show_crosshair:
            painter.setPen(QPen(QColor(220, 226, 228, 130), 1))
            cx, cy = center.x(), center.y()
            for start, end in (
                (QPointF(cx-17, cy), QPointF(cx-6, cy)),
                (QPointF(cx+6, cy), QPointF(cx+17, cy)),
                (QPointF(cx, cy-17), QPointF(cx, cy-6)),
                (QPointF(cx, cy+6), QPointF(cx, cy+17)),
            ):
                painter.drawLine(start, end)
        if detection is not None and detection.detected:
            centroid = point(detection.x, detection.y)
            if self.show_detection:
                x, y, w, h = detection.bbox
                painter.setPen(QPen(QColor("#71cca1"), 1.2))
                painter.drawRect(QRectF(ox+x*scale, oy+y*scale, max(4, w*scale), max(4, h*scale)))
                painter.drawEllipse(centroid, 2, 2)
            if self.show_error_vector:
                painter.setPen(QPen(QColor("#e0b66c"), 1, Qt.PenStyle.DashLine))
                painter.drawLine(center, centroid)
        if self.show_prediction and self.state in (TrackingState.TRACKING, TrackingState.DEAD_RECKONING):
            painter.setPen(QPen(QColor("#60c4d6"), 1, Qt.PenStyle.DotLine))
            painter.drawEllipse(point(self.pred_x, self.pred_y), 6, 6)
