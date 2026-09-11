"""
Archis Optical Tracker - Camera Viewport Display Widget
Renders the 640x480 monochrome FPA camera feed with real-time aerospace HUD overlays.
"""
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QImage, QColor, QPen, QFont, QBrush, QPolygonF
from PyQt6.QtCore import Qt, QRectF, QPointF
import numpy as np
from typing import Optional
from ..core.detector import DetectionResult
from ..core.config import TrackingState


class ViewportWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(640, 480)
        
        # Internal frame buffer
        self.frame_image: Optional[QImage] = None
        self.detection: Optional[DetectionResult] = None
        self.pred_x: float = 320.0
        self.pred_y: float = 240.0
        self.state: TrackingState = TrackingState.ACQUIRING
        self.pan_deg: float = 0.0
        self.tilt_deg: float = 0.0
        self.fps: float = 30.0
        self.latency_ms: float = 0.0
        self.error_px: float = 0.0
        self.rms_error_px: float = 0.0
        self.snr_db: float = 0.0
        
        # Visual options
        self.show_crosshair: bool = True
        self.show_hud_text: bool = True
        self.show_prediction: bool = True
        self.show_error_vector: bool = True

    def update_frame(self, frame_np: np.ndarray, detection: DetectionResult,
                     pred_x: float, pred_y: float, state: TrackingState,
                     pan_deg: float, tilt_deg: float, fps: float,
                     latency_ms: float, error_px: float, rms_error_px: float):
        """Updates frame data and triggers immediate repaint."""
        h, w = frame_np.shape
        # Convert numpy uint8 array to QImage format
        bytes_per_line = w
        self.frame_image = QImage(frame_np.data, w, h, bytes_per_line, QImage.Format.Format_Grayscale8).copy()
        
        self.detection = detection
        self.pred_x = pred_x
        self.pred_y = pred_y
        self.state = state
        self.pan_deg = pan_deg
        self.tilt_deg = tilt_deg
        self.fps = fps
        self.latency_ms = latency_ms
        self.error_px = error_px
        self.rms_error_px = rms_error_px
        self.snr_db = detection.snr_db if detection else 0.0
        
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        w_widget = rect.width()
        h_widget = rect.height()
        
        # 1. Fill background
        painter.fillRect(rect, QColor(8, 10, 14))
        
        # Compute scaling to maintain 640x480 aspect ratio
        scale_x = w_widget / 640.0
        scale_y = h_widget / 480.0
        scale = min(scale_x, scale_y)
        
        render_w = 640.0 * scale
        render_h = 480.0 * scale
        offset_x = (w_widget - render_w) / 2.0
        offset_y = (h_widget - render_h) / 2.0
        
        # 2. Draw Camera Frame
        if self.frame_image is not None and not self.frame_image.isNull():
            target_rect = QRectF(offset_x, offset_y, render_w, render_h)
            painter.drawImage(target_rect, self.frame_image)
        else:
            painter.setPen(QColor(100, 116, 139))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "INITIALIZING CAMERA FEED...")
            return

        # Transformation helper
        def to_screen(vx, vy):
            return offset_x + vx * scale, offset_y + vy * scale

        center_sx, center_sy = to_screen(320.0, 240.0)

        # 3. Draw Boresight Reticle & Calibration Rings
        if self.show_crosshair:
            # Concentric calibration rings (5px, 10px specification threshold, 20px)
            rings = [5.0, 10.0, 25.0]
            painter.setBrush(Qt.BrushStyle.NoBrush)
            for r_px in rings:
                r_screen = r_px * scale
                if r_px == 10.0:
                    # 10px target specification ring (bright dashed green/cyan)
                    pen = QPen(QColor(56, 189, 248, 160), 1.2, Qt.PenStyle.DashLine)
                else:
                    pen = QPen(QColor(255, 255, 255, 60), 1.0, Qt.PenStyle.DotLine)
                painter.setPen(pen)
                painter.drawEllipse(QPointF(center_sx, center_sy), r_screen, r_screen)

            # Center crosshairs
            ch_len = 18.0 * scale
            ch_gap = 4.0 * scale
            painter.setPen(QPen(QColor(255, 255, 255, 180), 1.2))
            # Left, Right, Top, Bottom reticle ticks
            painter.drawLine(QPointF(center_sx - ch_len, center_sy), QPointF(center_sx - ch_gap, center_sy))
            painter.drawLine(QPointF(center_sx + ch_gap, center_sy), QPointF(center_sx + ch_len, center_sy))
            painter.drawLine(QPointF(center_sx, center_sy - ch_len), QPointF(center_sx, center_sy - ch_gap))
            painter.drawLine(QPointF(center_sx, center_sy + ch_gap), QPointF(center_sx, center_sy + ch_len))

        # 4. Draw Detection Bounding Box & Centroid Marker
        if self.detection and self.detection.detected:
            det_sx, det_sy = to_screen(self.detection.x, self.detection.y)
            bx, by, bw, bh = self.detection.bbox
            
            box_sx, box_sy = to_screen(bx, by)
            box_sw = bw * scale
            box_sh = bh * scale
            
            # Corner brackets around detected target
            bracket_len = min(6.0 * scale, box_sw / 2.0)
            if self.error_px <= 10.0:
                box_color = QColor(74, 222, 128)  # Bright green: <= 10px specification passed
            else:
                box_color = QColor(250, 204, 21)  # Amber: tracking lock active but acquiring/converging
                
            painter.setPen(QPen(box_color, 1.5))
            # Top-Left
            painter.drawLine(QPointF(box_sx, box_sy), QPointF(box_sx + bracket_len, box_sy))
            painter.drawLine(QPointF(box_sx, box_sy), QPointF(box_sx, box_sy + bracket_len))
            # Top-Right
            painter.drawLine(QPointF(box_sx + box_sw, box_sy), QPointF(box_sx + box_sw - bracket_len, box_sy))
            painter.drawLine(QPointF(box_sx + box_sw, box_sy), QPointF(box_sx + box_sw, box_sy + bracket_len))
            # Bottom-Left
            painter.drawLine(QPointF(box_sx, box_sy + box_sh), QPointF(box_sx + bracket_len, box_sy + box_sh))
            painter.drawLine(QPointF(box_sx, box_sy + box_sh), QPointF(box_sx, box_sy + box_sh - bracket_len))
            # Bottom-Right
            painter.drawLine(QPointF(box_sx + box_sw, box_sy + box_sh), QPointF(box_sx + box_sw - bracket_len, box_sy + box_sh))
            painter.drawLine(QPointF(box_sx + box_sw, box_sy + box_sh), QPointF(box_sx + box_sw, box_sy + box_sh - bracket_len))
            
            # Sub-pixel Centroid marker
            painter.setPen(QPen(QColor(255, 255, 255), 1.0))
            painter.setBrush(QBrush(box_color))
            painter.drawEllipse(QPointF(det_sx, det_sy), 2.5, 2.5)

            # Error Vector Line to Boresight
            if self.show_error_vector and self.error_px > 1.5:
                painter.setPen(QPen(QColor(244, 63, 94, 180), 1.0, Qt.PenStyle.DashLine))
                painter.drawLine(QPointF(center_sx, center_sy), QPointF(det_sx, det_sy))

        # 5. Draw Kalman Predicted Position Indicator
        if self.show_prediction and self.state in [TrackingState.TRACKING, TrackingState.DEAD_RECKONING]:
            pred_sx, pred_sy = to_screen(self.pred_x, self.pred_y)
            pred_color = QColor(168, 85, 247, 180) if self.state == TrackingState.DEAD_RECKONING else QColor(56, 189, 248, 120)
            painter.setPen(QPen(pred_color, 1.0, Qt.PenStyle.DotLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(pred_sx, pred_sy), 6.0 * scale, 6.0 * scale)

        # 6. Draw Aerospace HUD Text Overlays
        if self.show_hud_text:
            painter.setFont(QFont("Consolas", 9))
            
            # Top-Left Telemetry
            painter.setPen(QColor(255, 255, 255, 220))
            tx = offset_x + 12
            ty = offset_y + 20
            
            # State Banner
            if self.state == TrackingState.TRACKING:
                state_color = QColor(74, 222, 128)
            elif self.state == TrackingState.DEAD_RECKONING:
                state_color = QColor(250, 204, 21)
            elif self.state == TrackingState.SEARCHING:
                state_color = QColor(249, 115, 22)
            else:
                state_color = QColor(244, 63, 94)
                
            painter.setPen(state_color)
            painter.drawText(int(tx), int(ty), f"STATUS: [{self.state.value}]")
            
            painter.setPen(QColor(203, 213, 225))
            painter.drawText(int(tx), int(ty + 16), f"ERROR:   {self.error_px:5.2f} px  (RMS: {self.rms_error_px:4.2f} px)")
            painter.drawText(int(tx), int(ty + 32), f"GIMBAL:  PAN {self.pan_deg:+6.2f}°  TILT {self.tilt_deg:+6.2f}°")
            painter.drawText(int(tx), int(ty + 48), f"SNR:     {self.snr_db:4.1f} dB")
            
            # Top-Right Telemetry
            rx = offset_x + render_w - 120
            painter.drawText(int(rx), int(ty), f"FPS:    {self.fps:4.1f}")
            painter.drawText(int(rx), int(ty + 16), f"LATENCY: {self.latency_ms:4.1f} ms")
            painter.drawText(int(rx), int(ty + 32), "FOV: 4.0°x3.0°")

            # Bottom Center 10px Specification Badge
            if self.detection and self.detection.detected:
                badge_text = "TRACKING LOCKED (<= 10 px PASS)" if self.error_px <= 10.0 else f"ACQUIRING ({self.error_px:.1f} px)"
                badge_color = QColor(74, 222, 128, 200) if self.error_px <= 10.0 else QColor(250, 204, 21, 200)
                painter.setPen(badge_color)
                painter.drawText(QRectF(offset_x, offset_y + render_h - 25, render_w, 20), 
                                 Qt.AlignmentFlag.AlignCenter, badge_text)
