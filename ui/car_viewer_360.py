"""
Premium Luxury Car 360° Rotation Viewer Component.
Displays sequential car images with smooth rotation, mouse dragging,
scroll wheel/touchpad horizontal scrolling, and keyboard support.
"""

import os
import re
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import (
    QColor, QPainter, QPixmap, QRadialGradient, QPen, QPainterPath
)
from app_paths import resource_path


# ── Points to the INTERPOLATED frames folder (80 frames, super smooth) ─────────
_HARDCODED_CAR_IMAGES_DIR = r"C:\Users\AinavilliRamaDurgaPr\Pictures\l\vcast_app_2 (2)\vcast_app_2\frames_interpolated"


def _resolve_car_images_dir() -> str:
    candidates = [
        _HARDCODED_CAR_IMAGES_DIR,
        resource_path("frames_interpolated"),
        resource_path("car_images"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "frames_interpolated"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "car_images"),
    ]
    for path in candidates:
        if os.path.isdir(path):
            print(f"[LuxuryCar360Viewer] Using frames dir: {path}")
            return path
    print(f"[LuxuryCar360Viewer] WARNING: frames directory not found! Tried: {candidates}")
    return _HARDCODED_CAR_IMAGES_DIR


class LuxuryCar360Viewer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setMinimumSize(600, 300)
        self.setFixedHeight(300)
        self.setFocusPolicy(Qt.StrongFocus)

        self._pixmaps: list[QPixmap] = []
        self._load_frames()

        self._num_frames: int = len(self._pixmaps)
        self._angle: float = 0.0
        self._is_paused: bool = False

        self._drag_active: bool = False
        self._drag_start_x: float = 0.0
        self._drag_start_angle: float = 0.0
        self._last_displayed_frame: int = -1

        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._on_tick)
        self._anim_timer.start(16)   # 60 FPS

        self._resume_timer = QTimer(self)
        self._resume_timer.setSingleShot(True)
        self._resume_timer.timeout.connect(self.update)

        self.setStyleSheet("background: transparent; border: none;")

    # ── Frame Loading ──────────────────────────────────────────────────────────
    def _load_frames(self):
        dir_path = _resolve_car_images_dir()
        matched: list[str] = []
        if os.path.isdir(dir_path):
            for fname in os.listdir(dir_path):
                if re.match(r"^frame_\d+\.png$", fname, re.IGNORECASE):
                    matched.append(fname)
        matched.sort()
        print(f"[LuxuryCar360Viewer] Found {len(matched)} frame(s)")

        for fname in matched:
            px = QPixmap(os.path.join(dir_path, fname))
            if not px.isNull():
                self._pixmaps.append(px)

        if not self._pixmaps:
            print("[LuxuryCar360Viewer] No frames found – using fallback.")
            for _ in range(24):
                dummy = QPixmap(600, 300)
                dummy.fill(QColor(50, 50, 50))
                self._pixmaps.append(dummy)

    # ── Helpers ────────────────────────────────────────────────────────────────
    def _frame_index(self) -> int:
        return int(self._angle) % self._num_frames

    def _repaint_if_changed(self):
        idx = self._frame_index()
        if idx != self._last_displayed_frame:
            self._last_displayed_frame = idx
            self.update()

    # ── Auto-rotation ──────────────────────────────────────────────────────────
    def _on_tick(self):
        if self._is_paused or self._drag_active or self._resume_timer.isActive():
            return
        # With 80 frames, full spin in 10s → 80/(10×60) = 0.1333 per tick
        step = self._num_frames / (10.0 * 60.0)
        self._angle = (self._angle + step) % self._num_frames
        self._repaint_if_changed()

    def _pause_temporarily(self):
        self._resume_timer.stop()
        self._resume_timer.start(2000)

    # ── Mouse ──────────────────────────────────────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_active = True
            self._drag_start_x = event.position().x()
            self._drag_start_angle = self._angle
            self._resume_timer.stop()
            self.setFocus()

    def mouseMoveEvent(self, event):
        if not self._drag_active:
            return
        dx = event.position().x() - self._drag_start_x
        # Full widget width = one full 360° rotation
        sensitivity = max(self.width(), 100)
        self._angle = (self._drag_start_angle + (dx / sensitivity) * self._num_frames) % self._num_frames
        self._repaint_if_changed()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_active = False
            self._pause_temporarily()

    # ── Scroll ─────────────────────────────────────────────────────────────────
    def wheelEvent(self, event):
        self._resume_timer.stop()
        dx = event.angleDelta().x()
        dy = event.angleDelta().y()
        if dx != 0:
            self._angle = (self._angle + (dx / 120.0) * 2) % self._num_frames
        elif dy != 0:
            direction = 1 if dy > 0 else -1
            self._angle = (self._angle + direction * 2) % self._num_frames
        self._repaint_if_changed()
        self._pause_temporarily()

    # ── Keyboard ───────────────────────────────────────────────────────────────
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Left:
            self._angle = (self._angle - 2) % self._num_frames
            self._repaint_if_changed()
            self._pause_temporarily()
        elif event.key() == Qt.Key_Right:
            self._angle = (self._angle + 2) % self._num_frames
            self._repaint_if_changed()
            self._pause_temporarily()
        elif event.key() == Qt.Key_Space:
            self._is_paused = not self._is_paused
            self._resume_timer.stop()
            self.update()
        else:
            super().keyPressEvent(event)

    # ── Paint ──────────────────────────────────────────────────────────────────
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        w, h = self.width(), self.height()
        rect  = self.rect()

        painter.save()

        clip_path = QPainterPath()
        clip_path.addRoundedRect(QRectF(rect).adjusted(0.5, 0.5, -0.5, -0.5), 13, 13)
        painter.setClipPath(clip_path)

        # Studio background
        painter.fillRect(rect, QColor(255, 255, 255))
        bg_grad = QRadialGradient(w / 2.0, h / 2.0, max(w, h) / 1.6)
        bg_grad.setColorAt(0.0, QColor(255, 255, 255))
        bg_grad.setColorAt(0.7, QColor(245, 246, 248))
        bg_grad.setColorAt(1.0, QColor(230, 233, 238))
        painter.fillRect(rect, bg_grad)

        # Car frame
        pixmap = self._pixmaps[self._frame_index()]
        scaled = pixmap.scaled(
            int(w * 0.95), int(h * 0.92),
            Qt.KeepAspectRatio, Qt.SmoothTransformation,
        )
        img_x = int(w / 2.0 - scaled.width()  / 2.0)
        img_y = int(h / 2.0 - scaled.height() / 2.2)
        painter.drawPixmap(img_x, img_y, scaled)

        # Focus ring
        if self.hasFocus():
            painter.setPen(QPen(QColor(14, 165, 233, 120), 1.5))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(QRectF(rect).adjusted(0.7, 0.7, -0.7, -0.7), 13, 13)

        painter.restore()
