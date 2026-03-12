"""
Custom UI Components for the Sticker App.
Spinboxes are now in ui.spinboxes module.
"""

from typing import Optional

from PyQt6.QtWidgets import QDial, QComboBox, QLabel, QStyle, QAbstractButton
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QPolygonF, QLinearGradient, QPixmap
from PyQt6.QtCore import Qt, QPoint, QPointF, QRect, QRectF, QSize, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty
import math

# Import Spinboxes from spinboxes module
from ui.spinboxes import StyledSpinBox, StyledDoubleSpinBox


class SmoothDial(QDial):
    """Custom QDial with anti-aliased rendering for smooth look"""
    def __init__(self, parent=None, dark_mode=False):
        super().__init__(parent)
        # Dark mode removed; always use light colors
        self.dark_mode = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # Remove stylesheet if any was set by parent, we do custom painting
        self.setStyleSheet("") 

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        center = rect.center()
        
        # Radius berechnen
        side = min(rect.width(), rect.height()) - 10
        radius = side / 2
        
        # Hintergrund
        bg_color = QColor(255, 255, 255, 38)  # Very light glassy effect
        painter.fillRect(rect, bg_color)
        
        # Rahmen
        border_color = QColor(255, 255, 255, 76)
        pen = QPen(border_color, 2)
        painter.setPen(pen)
        painter.drawEllipse(QPointF(center), radius, radius)
        
        # Knopf-Position berechnen
        angle_deg = self.value() - self.minimum()
        if self.maximum() > self.minimum():
            angle_deg = angle_deg / (self.maximum() - self.minimum()) * 360
        
        # Knopf zeichnen
        angle_rad = math.radians(angle_deg)
        handle_dist = radius * 0.6
        hx = center.x() + handle_dist * math.cos(angle_rad)
        hy = center.y() - handle_dist * math.sin(angle_rad)
        
        handle_radius = 8
        knob_color = QColor(20, 107, 138)
        painter.setBrush(QBrush(knob_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(hx, hy), handle_radius, handle_radius)
        
        # Highlight
        hl_color = QColor(255, 255, 255, 100)
        painter.setBrush(QBrush(hl_color))
        hl_offset = 2
        painter.drawEllipse(QPointF(hx - hl_offset, hy - hl_offset), handle_radius // 2, handle_radius // 2)


class ModernComboBox(QComboBox):
    """Custom QComboBox with modern styling and custom chevron arrow"""
    
    def __init__(self, parent=None, dark_mode=False):
        super().__init__(parent)
        self.dark_mode = dark_mode
        self.setMinimumHeight(36)
        self.setMaximumHeight(36)
        self.setEditable(True)
        line = self.lineEdit()
        if line:
            line.setReadOnly(True)
            line.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            line.setFrame(False)
            line.setStyleSheet("background: transparent; border: none; color: #2c3e50; font-size: 13px; font-weight: 500; padding: 0px;")
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        
        self.setStyleSheet("""
            QComboBox {
                border: 2px solid #e0e0e0;
                border-radius: 14px;
                padding: 7px 40px 7px 12px;
                background-color: #ffffff;
                color: #2c3e50;
                font-size: 13px;
                font-weight: 500;
                min-height: 22px;
            }
            QComboBox:hover {
                border-color: #b0b0b0;
                background-color: #ffffff;
            }
            QComboBox:focus, QComboBox:on {
                border-color: #3498db;
                background-color: #ffffff;
            }
            QComboBox::drop-down {
                border: none;
                background: transparent;
                width: 36px;
            }
            QComboBox::down-arrow {
                width: 0px;
                height: 0px;
            }
            QAbstractItemView {
                border: 2px solid #e0e0e0;
                border-radius: 12px;
                background-color: #ffffff;
                selection-background-color: #3498db;
                selection-color: #ffffff;
                color: #2c3e50;
                outline: none;
                padding: 4px;
            }
            QAbstractItemView::item {
                padding: 8px;
                border-radius: 6px;
                margin: 2px;
            }
            QAbstractItemView::item:hover {
                background-color: #f0f2f5;
            }
            QAbstractItemView::item:selected {
                background-color: #3498db;
                color: #ffffff;
            }
        """)
    
    def paintEvent(self, event):
        """Überschreibe paintEvent um Chevron zu zeichnen"""
        super().paintEvent(event)
        
        # Zeichne Chevron-Pfeil
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Determine color based on state
        view = self.view()
        is_popup_visible = view.isVisible() if view else False
        
        if self.hasFocus() or is_popup_visible:
            color = QColor("#3498db") # Blue
        elif self.underMouse():
            color = QColor("#3498db") # Blue on hover
        else:
            color = QColor("#95a5a6") # Grey
        
        # Position und Größe des Pfeils
        rect = self.rect()
        arrow_x = rect.right() - 20
        arrow_y = rect.center().y()
        
        # Chevron nach unten
        chevron = QPolygonF([
            QPointF(arrow_x - 4, arrow_y - 3),
            QPointF(arrow_x, arrow_y + 2),
            QPointF(arrow_x + 4, arrow_y - 3),
        ])
        
        # Zeichne Chevron
        pen = QPen(color, 2.0)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPolyline(chevron)


class ShimmerLabel(QLabel):
    """QLabel mit animiertem Shimmer-Effekt, der über eine Masken-Pixmap gesteuert wird."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mask_pixmap: Optional[QPixmap] = None
        self._shimmer_progress: float = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(35)
        self._timer.timeout.connect(self._advance_animation)

    def set_mask_pixmap(self, mask_pixmap: Optional[QPixmap]):
        if mask_pixmap is not None and mask_pixmap.isNull():
            mask_pixmap = None
        self._mask_pixmap = mask_pixmap
        if self._mask_pixmap and not self._timer.isActive():
            self._timer.start()
        elif not self._mask_pixmap and self._timer.isActive():
            self._timer.stop()
        self.update()

    def _advance_animation(self):
        if not self._mask_pixmap:
            return
        self._shimmer_progress = (self._shimmer_progress + 0.015) % 1.0
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        pixmap = self.pixmap()
        if not pixmap or pixmap.isNull() or not self._mask_pixmap:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        target_rect = self.contentsRect()
        aligned_rect = self.style().alignedRect(
            self.layoutDirection(),
            self.alignment(),
            pixmap.size(),
            target_rect
        )

        mask_pixmap = self._mask_pixmap
        if mask_pixmap.size() != pixmap.size():
            mask_pixmap = mask_pixmap.scaled(
                pixmap.size(),
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

        shimmer_layer = QPixmap(pixmap.size())
        shimmer_layer.fill(Qt.GlobalColor.transparent)

        w = pixmap.width()
        shimmer_width = w * 0.5
        start_x = (self._shimmer_progress * (w + shimmer_width)) - shimmer_width
        end_x = start_x + shimmer_width

        gradient = QLinearGradient(start_x, 0, end_x, 0)
        gradient.setColorAt(0.0, QColor(0, 0, 0, 0))
        gradient.setColorAt(0.15, QColor(255, 0, 0, 200))    # Red
        gradient.setColorAt(0.30, QColor(255, 255, 0, 200))  # Yellow
        gradient.setColorAt(0.45, QColor(0, 255, 0, 200))    # Green
        gradient.setColorAt(0.60, QColor(0, 255, 255, 200))  # Cyan
        gradient.setColorAt(0.75, QColor(0, 0, 255, 200))    # Blue
        gradient.setColorAt(0.90, QColor(255, 0, 255, 200))  # Magenta
        gradient.setColorAt(1.0, QColor(0, 0, 0, 0))

        layer_painter = QPainter(shimmer_layer)
        layer_painter.fillRect(shimmer_layer.rect(), gradient)
        layer_painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
        layer_painter.drawPixmap(0, 0, mask_pixmap)
        layer_painter.end()

        painter.setOpacity(0.9)
        painter.drawPixmap(aligned_rect.topLeft(), shimmer_layer)
        painter.end()



