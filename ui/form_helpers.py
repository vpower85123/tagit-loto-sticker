"""
Form Helper Functions
Hilfsfunktionen für konsistente Formular-Layouts und Styling
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QComboBox, QPushButton,
    QHBoxLayout, QVBoxLayout, QFormLayout, QSizePolicy
)
from PyQt6.QtCore import Qt

# Konstanten für einheitliche Größen
UNIT_LABEL_WIDTH = 60
SPINBOX_INPUT_WIDTH = 260
SPINBOX_HEIGHT = 26
TEXT_INPUT_HEIGHT = 36
ROW_SPACING_MAP = {
    "tight": 6,
    "normal": 12,
    "section": 24,
}


def style_text_input(field: QLineEdit, width: int = SPINBOX_INPUT_WIDTH) -> None:
    """Apply consistent sizing and alignment to text inputs."""
    field.setAlignment(Qt.AlignmentFlag.AlignCenter)
    field.setMinimumWidth(width)
    field.setMaximumWidth(width)
    field.setMinimumHeight(TEXT_INPUT_HEIGHT)
    field.setMaximumHeight(TEXT_INPUT_HEIGHT)
    field.setStyleSheet(
        """
        QLineEdit {
            padding: 6px 12px;
            border: 2px solid #000000;
            border-radius: 14px;
            background: #ffffff;
            color: #2c3e50;
            font-size: 13px;
            font-weight: 500;
        }
        QLineEdit:focus {
            border-color: #000000;
            background: #ffffff;
        }
        """
    )


def style_combo_box(combo: QComboBox, width: int = SPINBOX_INPUT_WIDTH) -> None:
    """Apply consistent sizing to combo boxes."""
    combo.setMinimumWidth(width)
    combo.setMaximumWidth(width)
    combo.setMinimumHeight(TEXT_INPUT_HEIGHT)
    combo.setMaximumHeight(TEXT_INPUT_HEIGHT)


def style_form_button(button: QPushButton, height: Optional[int] = None, width: int = 280) -> None:
    """Style GlassGlowButtons in forms mit einheitlicher Größe."""
    if height is None:
        try:
            hint_h = button.sizeHint().height()
        except Exception:
            hint_h = 0
        min_h = button.minimumHeight() if hasattr(button, "minimumHeight") else 0
        height = max(hint_h, min_h, 40)

    button.setMinimumHeight(height)
    button.setMaximumHeight(height)
    button.setMinimumWidth(width)
    button.setMaximumWidth(width)


def set_uniform_field_width(widget: QWidget, width: int = SPINBOX_INPUT_WIDTH) -> None:
    """Force consistent width for all spin boxes."""
    widget.setMinimumWidth(width)
    widget.setMaximumWidth(width)
    widget.setMinimumHeight(SPINBOX_HEIGHT)
    widget.setMaximumHeight(SPINBOX_HEIGHT)


def create_row_container(*widgets: QWidget, spacing: int = 10) -> QWidget:
    """Wrap widgets in a horizontal container with consistent padding."""
    container = QWidget()
    container.setStyleSheet("QWidget { background-color: transparent; }")
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(spacing)
    max_height = TEXT_INPUT_HEIGHT
    for widget in widgets:
        layout.addWidget(widget)
        if hasattr(widget, 'minimumHeight'):
            hint = widget.minimumHeight()
            max_height = max(max_height, hint)
        else:
            max_height = max(max_height, widget.sizeHint().height())

    target_height = max(max_height, TEXT_INPUT_HEIGHT)
    container.setMinimumHeight(target_height)
    container.setMaximumHeight(target_height)
    return container


def create_form_row(
    label_text: str,
    field_widget: QWidget,
    unit_text: Optional[str] = None,
    label_width: int = 150,
    enforce_field_width: bool = True,
) -> QWidget:
    """Create a complete form row with label, field, and optional unit."""
    row_container = QWidget()
    row_container.setStyleSheet("QWidget { background-color: transparent; }")
    row_layout = QHBoxLayout(row_container)
    row_layout.setContentsMargins(0, 8, 0, 8)
    row_layout.setSpacing(28)
    row_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    
    # Label container for vertical centering
    label_container = QWidget()
    label_container.setStyleSheet("QWidget { background-color: transparent; }")
    label_container_layout = QVBoxLayout(label_container)
    label_container_layout.setContentsMargins(0, 0, 0, 0)
    label_container_layout.setSpacing(0)
    
    label = QLabel(label_text)
    label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    label.setFixedWidth(label_width)
    label.setStyleSheet("color: #2c3e50; font-weight: 500;")
    
    label_container_layout.addWidget(label, 0, Qt.AlignmentFlag.AlignVCenter)
    row_layout.addWidget(label_container, 0, Qt.AlignmentFlag.AlignVCenter)
    
    # Field
    if enforce_field_width:
        field_widget.setFixedWidth(SPINBOX_INPUT_WIDTH)
    row_layout.addWidget(field_widget, 0, Qt.AlignmentFlag.AlignVCenter)
    
    # Unit label (optional)
    if unit_text:
        unit_container = QWidget()
        unit_container.setStyleSheet("QWidget { background-color: transparent; }")
        unit_container_layout = QVBoxLayout(unit_container)
        unit_container_layout.setContentsMargins(0, 0, 0, 0)
        unit_container_layout.setSpacing(0)
        
        unit_label = QLabel(unit_text)
        unit_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        unit_label.setFixedWidth(UNIT_LABEL_WIDTH)
        unit_label.setStyleSheet("color: #2c3e50; font-weight: 500;")
        
        unit_container_layout.addWidget(unit_label, 0, Qt.AlignmentFlag.AlignVCenter)
        row_layout.addWidget(unit_container, 0, Qt.AlignmentFlag.AlignVCenter)
    else:
        spacer = QLabel("")
        spacer.setFixedWidth(UNIT_LABEL_WIDTH)
        row_layout.addWidget(spacer, 0, Qt.AlignmentFlag.AlignVCenter)
    
    row_layout.addStretch()
    
    # Calculate proper height
    field_min_height = 26
    if hasattr(field_widget, 'minimumHeight'):
        field_min_height = max(field_min_height, field_widget.minimumHeight())
    if hasattr(field_widget, 'sizeHint'):
        field_min_height = max(field_min_height, field_widget.sizeHint().height())
    
    row_container.setFixedHeight(field_min_height + 16)
    
    return row_container
