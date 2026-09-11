"""
Archis Optical Tracker - Camera Viewport Display Widget
Renders 640x480 monochrome FPA feed with interactive Click-to-Designate,
dynamic track gate, and MIL-STD tactical reticle HUD.
"""
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QImage, QColor, QPen, QFont, QBrush, QPolygonF
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
import numpy as np
from typing import Optional, Tuple
from ..core.detector import DetectionResult
from ..core.config import TrackingState


class ViewportWidget(QWidget):
    # Interactive Operator Signals
    designate_target_signal = pyqtSignal(float, float)  # (viewport_x, viewport_y)
    spawn_decoy_signal = pyqtSignal(float, float)

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
        self.algo_name: str = "Gaussian Fit"
        
        # Visual options
        self.show_crosshair: bool = True
        self.show_hud_text: bool = True
        self.show_prediction: bool = True
        self.show_error_vector: bool = True
        
        # Screen geometry cache
        self.last_scale: float = 1.0
        self.last_offset_x: float = 0.0
        self.last_offset_y: float = 0.0

    def update_frame(self, frame_np: np.ndarray, detection: DetectionResult,
                     pred_x: float, pred_y: float, state: TrackingState,
                     pan_deg: float, tilt_deg: float, fps: float,
                     latency_ms: float, error_px: float, rms_error_px: float):
        """Updates frame data and triggers immediate repaint."""
        h, w = frame_np.shape
        self.frame_image = QImage(frame_np.data, w, h, w, QImage.Format.Format_Grayscale8).copy()
        
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
        self.algo_name = detection.algorithm_used if detection else "Gaussian Fit"
        
        self.update()

    def mousePressEvent(self, event):
        """Interactive click-to-designate or drop-decoy."""
        if self.last_scale <= 0.01:
            return
        # Convert screen click to viewport coordinates (0 to 640, 0 to 480)
        pos = event.position()
        vx = (pos.x() - self.last_offset_x) / self.last_scale
        vy = (pos.y() - self.last_offset_y) / self.last_scale
        
        if 0 <= vx < 640 and 0 <= vy < 480:
            if event.button() == Qt.MouseButton.LeftButton:
                self.designate_target_signal.emit(float(vx), float(vy))
            elif event.button() == Qt.MouseButton.RightButton:
                self.spawn_decoy_signal.emit(float(vx), float(vy))

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
        
        self.last_scale = scale
        self.last_offset_x = offset_x
        self.last_offset_y = offset_y
        
        # 2. Draw Camera Frame
        if self.frame_image is not None and not self.frame_image.isNull():
            target_rect = QRectF(offset_x, offset_y, render_w, render_h)
            painter.drawImage(target_rect, self.frame_image)
        else:
            painter.setPen(QColor(100, 116, 139))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "INITIALIZING FPA SENSOR...")
            return

        def to_screen(vx, vy):
            return offset_x + vx * scale, offset_y + vy * scale

        center_sx, center_sy = to_screen(320.0, 240.0)

        # 3. Dynamic Track Gate & Neural Heatmap
        if self.detection and self.detection.gate_bbox:
            gx, gy, gw, gh = self.detection.gate_bbox
            gsx, gsy = to_screen(gx, gy)
            gsw = gw * scale
            gsh = gh * scale

            # If AI ONNX Heatmap is present, render semi-translucent neural probability field inside the gate
            if self.detection.heatmap is not None and "NanoSpot" in self.algo_name:
                h_arr = np.clip(self.detection.heatmap * 255.0, 0, 255).astype(np.uint8)
                rgba = np.zeros((64, 64, 4), dtype=np.uint8)
                rgba[..., 0] = (h_arr * 0.08).astype(np.uint8)
                rgba[..., 1] = (h_arr * 0.92).astype(np.uint8)
                rgba[..., 2] = (h_arr * 0.98).astype(np.uint8)
                rgba[..., 3] = (h_arr * 0.40).astype(np.uint8)
                h_img = QImage(rgba.data, 64, 64, 64 * 4, QImage.Format.Format_RGBA8888)
                painter.drawImage(QRectF(gsx, gsy, gsw, gsh), h_img)

            # Track gate outline
            painter.setPen(QPen(QColor(56, 189, 248, 140), 1.0, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(QRectF(gsx, gsy, gsw, gsh))
            painter.setFont(QFont("Consolas", 7))
            painter.setPen(QColor(56, 189, 248, 180))
            gate_label = "AI GATE LOCK" if "NanoSpot" in self.algo_name else "GATE LOCK"
            painter.drawText(int(gsx + 4), int(gsy + 12), gate_label)

        # 3.1 Decoy Rejection Warning Banner
        if self.detection and self.detection.is_decoy:
            dp_w = 230.0
            dp_h = 24.0
            dpx = offset_x + render_w / 2.0 - dp_w / 2.0
            dpy = offset_y + 16
            painter.setPen(QPen(QColor(239, 68, 68), 1.2))
            painter.setBrush(QBrush(QColor(69, 10, 10, 230)))
            painter.drawRoundedRect(QRectF(dpx, dpy, dp_w, dp_h), 4.0, 4.0)
            painter.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
            painter.setPen(QColor(254, 202, 202))
            painter.drawText(QRectF(dpx, dpy, dp_w, dp_h), Qt.AlignmentFlag.AlignCenter, "WARNING: DECOY FLARE REJECTED")

        # 4. Boresight Reticle & Calibration Rings
        if self.show_crosshair:
            # Concentric calibration rings (5px, 10px specification threshold, 25px)
            rings = [5.0, 10.0, 25.0]
            painter.setBrush(Qt.BrushStyle.NoBrush)
            for r_px in rings:
                r_screen = r_px * scale
                if r_px == 10.0:
                    pen = QPen(QColor(56, 189, 248, 180), 1.2, Qt.PenStyle.DashLine)
                else:
                    pen = QPen(QColor(255, 255, 255, 60), 1.0, Qt.PenStyle.DotLine)
                painter.setPen(pen)
                painter.drawEllipse(QPointF(center_sx, center_sy), r_screen, r_screen)

            # Center crosshairs
            ch_len = 18.0 * scale
            ch_gap = 4.0 * scale
            painter.setPen(QPen(QColor(255, 255, 255, 180), 1.2))
            painter.drawLine(QPointF(center_sx - ch_len, center_sy), QPointF(center_sx - ch_gap, center_sy))
            painter.drawLine(QPointF(center_sx + ch_gap, center_sy), QPointF(center_sx + ch_len, center_sy))
            painter.drawLine(QPointF(center_sx, center_sy - ch_len), QPointF(center_sx, center_sy - ch_gap))
            painter.drawLine(QPointF(center_sx, center_sy + ch_gap), QPointF(center_sx, center_sy + ch_len))

        # 5. Draw Detection Bounding Box & Sub-Pixel Centroid
        if self.detection and self.detection.detected:
            det_sx, det_sy = to_screen(self.detection.x, self.detection.y)
            bx, by, bw, bh = self.detection.bbox
            
            box_sx, box_sy = to_screen(bx, by)
            box_sw = bw * scale
            box_sh = bh * scale
            
            bracket_len = min(6.0 * scale, box_sw / 2.0)
            box_color = QColor(74, 222, 128) if self.error_px <= 10.0 else QColor(250, 204, 21)
                
            painter.setPen(QPen(box_color, 1.5))
            painter.drawLine(QPointF(box_sx, box_sy), QPointF(box_sx + bracket_len, box_sy))
            painter.drawLine(QPointF(box_sx, box_sy), QPointF(box_sx, box_sy + bracket_len))
            painter.drawLine(QPointF(box_sx + box_sw, box_sy), QPointF(box_sx + box_sw - bracket_len, box_sy))
            painter.drawLine(QPointF(box_sx + box_sw, box_sy), QPointF(box_sx + box_sw, box_sy + bracket_len))
            painter.drawLine(QPointF(box_sx, box_sy + box_sh), QPointF(box_sx + bracket_len, box_sy + box_sh))
            painter.drawLine(QPointF(box_sx, box_sy + box_sh), QPointF(box_sx, box_sy + box_sh - bracket_len))
            painter.drawLine(QPointF(box_sx + box_sw, box_sy + box_sh), QPointF(box_sx + box_sw - bracket_len, box_sy + box_sh))
            painter.drawLine(QPointF(box_sx + box_sw, box_sy + box_sh), QPointF(box_sx + box_sw, box_sy + box_sh - bracket_len))
            
            painter.setPen(QPen(QColor(255, 255, 255), 1.0))
            painter.setBrush(QBrush(box_color))
            painter.drawEllipse(QPointF(det_sx, det_sy), 2.5, 2.5)

            # Error Vector Line to Boresight
            if self.show_error_vector and self.error_px > 1.2:
                painter.setPen(QPen(QColor(244, 63, 94, 180), 1.0, Qt.PenStyle.DashLine))
                painter.drawLine(QPointF(center_sx, center_sy), QPointF(det_sx, det_sy))

        # 6. Draw Kalman Predicted Position
        if self.show_prediction and self.state in [TrackingState.TRACKING, TrackingState.DEAD_RECKONING]:
            pred_sx, pred_sy = to_screen(self.pred_x, self.pred_y)
            pred_color = QColor(168, 85, 247, 180) if self.state == TrackingState.DEAD_RECKONING else QColor(56, 189, 248, 120)
            painter.setPen(QPen(pred_color, 1.0, Qt.PenStyle.DotLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(pred_sx, pred_sy), 6.0 * scale, 6.0 * scale)

        # 7. Aerospace Glassmorphic HUD Overlays
        if self.show_hud_text:
            painter.setFont(QFont("Consolas", 9))
            tx = offset_x + 12
            ty = offset_y + 20

            # State-specific color
            if self.state == TrackingState.TRACKING:
                state_color = QColor(52, 211, 153)   # Emerald
                state_bg = QColor(6, 35, 25, 210)
                state_border = QColor(5, 150, 105, 180)
            elif self.state == TrackingState.DEAD_RECKONING:
                state_color = QColor(245, 158, 11)  # Amber
                state_bg = QColor(38, 27, 10, 210)
                state_border = QColor(217, 119, 6, 180)
            elif self.state == TrackingState.SEARCHING:
                state_color = QColor(56, 189, 248)  # Cyan
                state_bg = QColor(8, 32, 50, 210)
                state_border = QColor(2, 132, 199, 180)
            else:
                state_color = QColor(248, 113, 113)  # Rose
                state_bg = QColor(43, 16, 20, 210)
                state_border = QColor(220, 38, 38, 180)

            # Left telemetry glass card
            left_card_w = 310.0
            left_card_h = 82.0
            painter.setPen(QPen(state_border, 1.0))
            painter.setBrush(QBrush(state_bg))
            painter.drawRoundedRect(QRectF(tx - 4, ty - 12, left_card_w, left_card_h), 6.0, 6.0)

            painter.setPen(state_color)
            painter.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
            painter.drawText(int(tx + 6), int(ty + 6), f"PAT STATE: [{self.state.value}]")

            painter.setFont(QFont("Consolas", 9))
            painter.setPen(QColor(226, 232, 240))
            painter.drawText(int(tx + 6), int(ty + 24), f"BORESIGHT ERR: {self.error_px:5.2f} px  (RMS: {self.rms_error_px:4.2f} px)")
            painter.drawText(int(tx + 6), int(ty + 42), f"PEDESTAL AZ/EL: PAN {self.pan_deg:+6.2f}° | TILT {self.tilt_deg:+6.2f}°")
            if "NanoSpot" in self.algo_name and self.detection:
                ai_text = f"AI LOCKED ({self.detection.confidence*100.0:.0f}%)" if self.detection.detected else "AI SEARCHING"
                painter.drawText(int(tx + 6), int(ty + 60), f"ESTIMATOR SNR:  {self.snr_db:4.1f} dB  | {ai_text}")
            else:
                painter.drawText(int(tx + 6), int(ty + 60), f"ESTIMATOR SNR:  {self.snr_db:4.1f} dB  | CV: {self.algo_name[:14]}")

            # Right optical parameters glass card
            right_card_w = 148.0
            right_card_h = 64.0
            rx = offset_x + render_w - right_card_w - 8
            painter.setPen(QPen(QColor(30, 41, 59, 200), 1.0))
            painter.setBrush(QBrush(QColor(11, 15, 23, 220)))
            painter.drawRoundedRect(QRectF(rx - 4, ty - 12, right_card_w, right_card_h), 6.0, 6.0)

            painter.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
            painter.setPen(QColor(56, 189, 248))
            painter.drawText(int(rx + 6), int(ty + 6), f"CYCLE:  {self.fps:4.1f} FPS")
            painter.setFont(QFont("Consolas", 9))
            painter.setPen(QColor(203, 213, 225))
            painter.drawText(int(rx + 6), int(ty + 24), f"LATENCY:{self.latency_ms:4.1f} ms")
            painter.drawText(int(rx + 6), int(ty + 42), "OPTICS: 4.0°x3.0°")

            # Bottom interaction hint pill
            pill_w = render_w - 24
            pill_h = 24.0
            px = offset_x + 12
            py = offset_y + render_h - 32
            painter.setPen(QPen(QColor(30, 41, 59, 180), 1.0))
            painter.setBrush(QBrush(QColor(11, 15, 23, 220)))
            painter.drawRoundedRect(QRectF(px, py, pill_w, pill_h), 4.0, 4.0)

            painter.setFont(QFont("Segoe UI", 9))
            painter.setPen(QColor(148, 163, 184))
            painter.drawText(QRectF(px, py, pill_w, pill_h), Qt.AlignmentFlag.AlignCenter,
                             "[LEFT CLICK] Designate Optical Beacon Target   |   [RIGHT CLICK] Inject Decoy Flare")

