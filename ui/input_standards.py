"""
UI Input Standards - Richtlinien für Eingabefelder
===================================================

WICHTIG: Diese Parameter MÜSSEN vor dem Erstellen von Eingabefeldern geprüft werden!

Checkliste für neue Eingabefelder:
----------------------------------
☐ Mindesthoehe gesetzt? (MIN_INPUT_HEIGHT)
☐ Textfarbe dunkel genug? (INPUT_TEXT_COLOR)
☐ Schriftgroesse lesbar? (INPUT_FONT_SIZE)
☐ Ausreichend Padding? (INPUT_PADDING)
☐ Focus-State definiert? (FOCUS_BORDER_COLOR)
☐ Bei Tabellen: Zeilenhoehe >= MIN_TABLE_ROW_HEIGHT?
"""

import logging
from PyQt6.QtGui import QColor

logger = logging.getLogger(__name__)

# ============================================================
# EINGABEFELD STANDARDS
# ============================================================

# Mindesthöhe für Eingabefelder (verhindert abgeschnittenen Text)
MIN_INPUT_HEIGHT = 40  # px - NIEMALS kleiner!

# Textfarbe - muss dunkel sein für Lesbarkeit auf weißem Hintergrund
INPUT_TEXT_COLOR = "#1e293b"  # Dunkelgrau, gut lesbar
INPUT_TEXT_COLOR_QT = QColor(30, 41, 59)

# Schriftgröße
INPUT_FONT_SIZE = 13  # px - Minimum für Lesbarkeit
INPUT_FONT_SIZE_SMALL = 12  # px - Nur für sekundäre Felder

# Padding innerhalb der Eingabefelder
INPUT_PADDING_V = 10  # px vertikal
INPUT_PADDING_H = 12  # px horizontal
INPUT_PADDING = f"{INPUT_PADDING_V}px {INPUT_PADDING_H}px"

# Hintergrund
INPUT_BG_COLOR = "#ffffff"
INPUT_BG_DISABLED = "#f1f5f9"

# Border
INPUT_BORDER_COLOR = "#e2e8f0"
INPUT_BORDER_RADIUS = 8  # px
FOCUS_BORDER_COLOR = "#3b82f6"  # Blau bei Fokus
FOCUS_BORDER_WIDTH = 2  # px

# ============================================================
# TABELLEN STANDARDS
# ============================================================

# Zeilenhöhe - MUSS groß genug sein für Inline-Editing!
MIN_TABLE_ROW_HEIGHT = 45  # px - NIEMALS kleiner!

# Header
TABLE_HEADER_HEIGHT = 40  # px
TABLE_HEADER_FONT_SIZE = 12  # px
TABLE_HEADER_BG = "#f1f5f9"
TABLE_HEADER_COLOR = "#475569"

# Zellen
TABLE_CELL_PADDING = 8  # px
TABLE_GRID_COLOR = "#e2e8f0"
TABLE_ALT_ROW_COLOR = "#f8fafc"

# ============================================================
# HILFSFUNKTIONEN
# ============================================================

def get_input_stylesheet(include_focus: bool = True) -> str:
    """Generiert Standard-Stylesheet für QLineEdit."""
    style = f"""
        QLineEdit {{
            background-color: {INPUT_BG_COLOR};
            border: 1px solid {INPUT_BORDER_COLOR};
            border-radius: {INPUT_BORDER_RADIUS}px;
            padding: {INPUT_PADDING};
            font-size: {INPUT_FONT_SIZE}px;
            color: {INPUT_TEXT_COLOR};
            min-height: {MIN_INPUT_HEIGHT - 2 * INPUT_PADDING_V}px;
        }}
    """
    if include_focus:
        style += f"""
        QLineEdit:focus {{
            border: {FOCUS_BORDER_WIDTH}px solid {FOCUS_BORDER_COLOR};
            background-color: {INPUT_BG_COLOR};
        }}
        QLineEdit:disabled {{
            background-color: {INPUT_BG_DISABLED};
            color: #94a3b8;
        }}
        """
    return style


def get_combobox_stylesheet() -> str:
    """Generiert Standard-Stylesheet für QComboBox."""
    return f"""
        QComboBox {{
            background-color: {INPUT_BG_COLOR};
            border: 1px solid {INPUT_BORDER_COLOR};
            border-radius: {INPUT_BORDER_RADIUS}px;
            padding: {INPUT_PADDING};
            font-size: {INPUT_FONT_SIZE}px;
            color: {INPUT_TEXT_COLOR};
            min-height: {MIN_INPUT_HEIGHT - 2 * INPUT_PADDING_V}px;
        }}
        QComboBox:focus {{
            border: {FOCUS_BORDER_WIDTH}px solid {FOCUS_BORDER_COLOR};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 30px;
        }}
        QComboBox::down-arrow {{
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 6px solid #64748b;
            margin-right: 10px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {INPUT_BG_COLOR};
            border: 1px solid {INPUT_BORDER_COLOR};
            border-radius: {INPUT_BORDER_RADIUS}px;
            selection-background-color: {FOCUS_BORDER_COLOR};
            selection-color: #ffffff;
        }}
    """


def get_table_stylesheet() -> str:
    """Generiert Standard-Stylesheet für QTableWidget."""
    return f"""
        QTableWidget {{
            background-color: {INPUT_BG_COLOR};
            border: 1px solid {INPUT_BORDER_COLOR};
            border-radius: {INPUT_BORDER_RADIUS}px;
            gridline-color: {TABLE_GRID_COLOR};
            font-size: {INPUT_FONT_SIZE}px;
            color: {INPUT_TEXT_COLOR};
        }}
        QTableWidget::item {{
            padding: {TABLE_CELL_PADDING}px;
            border-bottom: 1px solid {TABLE_GRID_COLOR};
            color: {INPUT_TEXT_COLOR};
            background-color: {INPUT_BG_COLOR};
        }}
        QTableWidget::item:selected {{
            background-color: #dbeafe;
            color: {INPUT_TEXT_COLOR};
        }}
        QTableWidget QLineEdit {{
            color: {INPUT_TEXT_COLOR};
            background-color: {INPUT_BG_COLOR};
            border: {FOCUS_BORDER_WIDTH}px solid {FOCUS_BORDER_COLOR};
            border-radius: 4px;
            padding: 4px 8px;
            font-size: {INPUT_FONT_SIZE}px;
            font-weight: 500;
            selection-background-color: {FOCUS_BORDER_COLOR};
            selection-color: #ffffff;
        }}
        QHeaderView::section {{
            background-color: {TABLE_HEADER_BG};
            color: {TABLE_HEADER_COLOR};
            font-weight: 600;
            font-size: {TABLE_HEADER_FONT_SIZE}px;
            padding: 10px 8px;
            border: none;
            border-bottom: 2px solid {TABLE_GRID_COLOR};
            border-right: 1px solid {TABLE_GRID_COLOR};
        }}
    """


def validate_input_params(
    height: int = None,
    font_size: int = None,
    row_height: int = None
) -> list:
    """
    Validiert Eingabeparameter und gibt Warnungen zurück.
    
    Verwendung:
        warnings = validate_input_params(height=30, row_height=35)
        if warnings:
            logger.warning(" UI Standards nicht eingehalten:")
            for w in warnings:
                print(f"  - {w}")
    """
    warnings = []
    
    if height is not None and height < MIN_INPUT_HEIGHT:
        warnings.append(
            f"Höhe ({height}px) unter Minimum ({MIN_INPUT_HEIGHT}px)! "
            f"Text wird abgeschnitten."
        )
    
    if font_size is not None and font_size < INPUT_FONT_SIZE_SMALL:
        warnings.append(
            f"Schriftgröße ({font_size}px) unter Minimum ({INPUT_FONT_SIZE_SMALL}px)! "
            f"Schwer lesbar."
        )
    
    if row_height is not None and row_height < MIN_TABLE_ROW_HEIGHT:
        warnings.append(
            f"Zeilenhöhe ({row_height}px) unter Minimum ({MIN_TABLE_ROW_HEIGHT}px)! "
            f"Inline-Editing wird abgeschnitten."
        )
    
    return warnings


# ============================================================
# SCHNELLREFERENZ FÜR ENTWICKLER
# ============================================================
"""
SCHNELLREFERENZ - Kopiere diese Werte:
--------------------------------------

QLineEdit:
    min-height: 40px
    padding: 10px 12px
    font-size: 13px
    color: #1e293b
    border-radius: 8px

QTableWidget:
    row-height: 45px (setDefaultSectionSize)
    font-size: 13px
    
QTableWidget QLineEdit (Inline-Editor):
    color: #1e293b
    background: #ffffff
    border: 2px solid #3b82f6
    
FARBEN:
    Text: #1e293b (dunkelgrau)
    Border: #e2e8f0 (hellgrau)
    Focus: #3b82f6 (blau)
    Disabled BG: #f1f5f9
"""
