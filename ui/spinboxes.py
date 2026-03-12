"""
Styled Spinbox Components - alle Spinbox-Definitionen in einem Modul
"""

from PyQt6.QtWidgets import QSpinBox, QDoubleSpinBox, QToolButton, QAbstractSpinBox
from PyQt6.QtGui import QPainter, QColor, QPolygonF, QPen
from PyQt6.QtCore import Qt, QPointF, QSize
import qtawesome as qta


class SpinArrowButton(QToolButton):
    """Kleiner flacher Button mit Phosphor-Icon für Hoch/Runter."""

    def __init__(self, direction: str, parent=None):
        super().__init__(parent)
        self.direction = direction
        self.setAutoRepeat(True)
        self.setAutoRepeatDelay(250)
        self.setAutoRepeatInterval(60)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._normal_color = "#95a5a6"
        self._hover_color = "#FFC000"
        self._press_color = "#E0A800"
        self._update_icon(self._normal_color)
        self.setIconSize(QSize(14, 14))
        self.setStyleSheet("QToolButton { background: transparent; border: none; }"
                           "QToolButton:hover { background: rgba(255, 192, 0, 20); border-radius: 4px; }"
                           "QToolButton:pressed { background: rgba(255, 192, 0, 50); border-radius: 4px; }")

    def _update_icon(self, color):
        icon_name = "ph.caret-up" if self.direction == "up" else "ph.caret-down"
        self.setIcon(qta.icon(icon_name, color=color))

    def enterEvent(self, event):
        super().enterEvent(event)
        self._update_icon(self._hover_color)

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self._update_icon(self._normal_color)

    def mousePressEvent(self, event):
        self._update_icon(self._press_color)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self.underMouse():
            self._update_icon(self._hover_color)
        else:
            self._update_icon(self._normal_color)
        super().mouseReleaseEvent(event)


_ARROW_WIDTH = 24
_ARROW_MARGIN = 2


def _init_custom_arrows(spinbox: QAbstractSpinBox):
    spinbox.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
    setattr(spinbox, "_arrow_width", _ARROW_WIDTH)
    setattr(spinbox, "_arrow_margin", _ARROW_MARGIN)
    up_button = SpinArrowButton("up", spinbox)
    down_button = SpinArrowButton("down", spinbox)
    up_button.clicked.connect(spinbox.stepUp)
    down_button.clicked.connect(spinbox.stepDown)
    up_button.raise_()
    down_button.raise_()
    setattr(spinbox, "_up_button", up_button)
    setattr(spinbox, "_down_button", down_button)
    _update_text_margins(spinbox)
    _position_arrows(spinbox)


def _update_text_margins(spinbox: QAbstractSpinBox):
    line = spinbox.lineEdit()
    if line is not None:
        right_padding = spinbox._arrow_width + spinbox._arrow_margin + 2  # type: ignore[attr-defined]
        line.setTextMargins(4, 0, right_padding, 0)


def _position_arrows(spinbox: QAbstractSpinBox):
    if not hasattr(spinbox, "_up_button"):
        return
    margin = spinbox._arrow_margin  # type: ignore[attr-defined]
    width = spinbox._arrow_width  # type: ignore[attr-defined]
    total_height = max(0, spinbox.height() - margin * 2)
    half = max(1, total_height // 2)
    x = spinbox.width() - width - margin
    spinbox._up_button.setGeometry(int(x), int(margin), int(width), int(half))  # type: ignore[attr-defined]
    spinbox._down_button.setGeometry(int(x), int(margin + half), int(width), int(max(1, total_height - half)))  # type: ignore[attr-defined]


class StyledSpinBox(QSpinBox):
    """Styled SpinBox mit custom gemalten Pfeilen für Ganzzahl-Werte"""
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Linksbündiger Text
        self.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        self.setStyleSheet("""
            QSpinBox {
                padding: 4px 2px 4px 2px;
                border: 2px solid #e0e0e0;
                border-radius: 14px;
                background: #f8f9fa;
                min-height: 36px;
                color: #2c3e50;
                font-size: 13px;
                font-weight: 500;
            }
            QSpinBox:hover {
                border-color: #b0b0b0;
                background: #ffffff;
            }
            QSpinBox:focus {
                border-color: #3498db;
                background: #ffffff;
            }
            QSpinBox::up-button {
                width: 0px;
                border: none;
                background: none;
            }
            QSpinBox::down-button {
                width: 0px;
                border: none;
                background: none;
            }
        """)
        _init_custom_arrows(self)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        _update_text_margins(self)
        _position_arrows(self)


class StyledDoubleSpinBox(QDoubleSpinBox):
    """Styled DoubleSpinBox mit custom gemalten Pfeilen für Dezimal-Werte"""
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Linksbündiger Text
        self.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        self.setStyleSheet("""
            QDoubleSpinBox {
                padding: 4px 2px 4px 2px;
                border: 2px solid #e0e0e0;
                border-radius: 14px;
                background: #f8f9fa;
                min-height: 36px;
                color: #2c3e50;
                font-size: 13px;
                font-weight: 500;
            }
            QDoubleSpinBox:hover {
                border-color: #b0b0b0;
                background: #ffffff;
            }
            QDoubleSpinBox:focus {
                border-color: #3498db;
                background: #ffffff;
            }
            QDoubleSpinBox::up-button {
                width: 0px;
                border: none;
                background: none;
            }
            QDoubleSpinBox::down-button {
                width: 0px;
                border: none;
                background: none;
            }
        """)
        _init_custom_arrows(self)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        _update_text_margins(self)
        _position_arrows(self)