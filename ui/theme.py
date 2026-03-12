"""Theme und Styling für die Anwendung."""

from enum import Enum
from typing import cast
from PyQt6.QtGui import QFont, QPalette, QColor
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt


class Theme(Enum):
    """Theme Enum: DARK oder LIGHT"""
    DARK = "dark"
    LIGHT = "light"


# HIER DIE FARBE ÄNDERN
# Standard Akzent-Farbe (für Überschriften, Fokus-Rahmen etc.)
ACCENT_COLOR = "#1E90FF" 


def detect_system_dark_mode() -> bool:
    """Erkennt, ob das System im Dark Mode ist."""
    try:
        # Windows Registry Check
        import winreg
        registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
        key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return value == 0
    except Exception:
        # Fallback: Qt Palette prüfen
        app = cast(QApplication, QApplication.instance())
        if app:
            palette = app.palette()
            bg = palette.color(QPalette.ColorRole.Window)
            text = palette.color(QPalette.ColorRole.WindowText)
            # Wenn Text heller als Hintergrund -> Dark Mode
            return text.lightness() > bg.lightness()
        return False



def get_theme_colors(theme: Theme, custom_colors: dict | None = None) -> dict:
    """Gibt Theme-Farben basierend auf Theme zurück."""
    colors = {}
    if theme == Theme.DARK:
        colors = {
            "bg": "#1e1e1e",              # VS Code Dark - Haupthintergrund
            "fg": "#cccccc",              # Weicher Text statt reines Weiß
            "input_bg": "#2d2d30",        # Erhöhte Elemente
            "input_fg": "#e0e0e0",        # Leicht hellerer Text für Inputs
            "border": "#3e3e42",          # Subtile Borders
            "accent": "#569cd6",          # VS Code Blue - entsättigt
            "preview_bg": "#252526",      # Leicht heller als Haupthintergrund
            "hover": "#2a2d2e",           # Hover-Zustand
            "selection": "#264f78",       # Auswahl-Hintergrund
            "shadow": "rgba(0, 0, 0, 0.4)",  # Weiche Schatten auch im Dark Mode
        }
    else:
        colors = {
            "bg": "#f3f3f3",
            "fg": "#1f2a37",
            "input_bg": "#ffffff",
            "input_fg": "#1f2a37",
            "border": "#d9e0ec",
            "accent": "#3498db",
            "preview_bg": "#e8e8e8",
            "hover": "#e8e8e8",
            "selection": "#b3d7ff",
            "shadow": "rgba(0, 0, 0, 0.1)",
        }
    
    if custom_colors:
        colors.update(custom_colors)
        
    return colors


def create_input_stylesheet(theme: Theme, custom_colors: dict | None = None) -> str:
    """Erstellt Stylesheet für Input-Widgets."""
    colors = get_theme_colors(theme, custom_colors)
    shadow = colors.get('shadow', 'rgba(0, 0, 0, 0.1)')
    hover = colors.get('hover', colors['input_bg'])
    
    return f"""
        QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
            background-color: {colors['input_bg']};
            color: {colors['input_fg']};
            border: 1px solid {colors['border']};
            border-radius: 6px;
            padding: 6px 8px;
            selection-background-color: {colors.get('selection', '#3498db')};
        }}
        QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover {{
            background-color: {hover};
            border: 1px solid {colors['accent']};
        }}
        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
            border: 1.5px solid {colors['accent']};
            background-color: {colors['input_bg']};
        }}
        QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {{
            opacity: 0.5;
        }}
    """


def create_dialog_stylesheet(theme: Theme, custom_colors: dict | None = None) -> str:
    """Erstellt Stylesheet für Dialog-Widgets."""
    colors = get_theme_colors(theme, custom_colors)
    
    # Always use light theme styling
    colors = get_theme_colors(Theme.LIGHT, custom_colors)
    return f"""
        QDialog {{
            background-color: {colors['bg']};
            color: {colors['fg']};
        }}
        QLabel {{
            color: {colors['fg']};
        }}
    """ + get_unified_button_style()


def create_groupbox_stylesheet(theme: Theme, custom_colors: dict | None = None) -> str:
    """Erstellt Stylesheet für GroupBoxen - adaptiv für Light/Dark Mode."""
    colors = get_theme_colors(theme, custom_colors)
    
    # Always use light theme styling
    return f"""
        QGroupBox {{
            background: #ffffff;
            border: 1px solid #d9e0ec;
            border-radius: 20px;
            margin-top: 12px;
            padding: 20px;
            font-family: 'Bahnschrift';
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 6px 16px;
            background-color: #f8f9fb;
            color: #1f2a37;
            font-weight: 600;
            font-size: 13px;
            border: 1px solid #d9e0ec;
            border-radius: 12px;
            margin-left: 12px;
        }}
    """


def get_contrasting_text_color(hex_color: str) -> str:
    """
    Berechnet basierend auf der Helligkeit der Hintergrundfarbe
    eine gut lesbare Textfarbe (Schwarz oder Weiß).
    """
    try:
        c = QColor(hex_color)
        # Helligkeit nach Formel: 0.299*R + 0.587*G + 0.114*B
        # Qt's lightness() ist HSL lightness, wir nehmen eine einfache Annäherung
        brightness = (c.red() * 299 + c.green() * 587 + c.blue() * 114) / 1000
        
        # Schwellenwert 128 (0-255)
        if brightness > 128:
            return "#000000" # Dunkler Text auf hellem Grund
        else:
            return "#ffffff" # Heller Text auf dunklem Grund
    except Exception:
        return "#000000" # Fallback


def get_unified_button_style() -> str:
    """Einheitlicher Modern-Pill-Stil für ALLE QPushButtons in der App."""
    return """
        QMessageBox QPushButton, QDialogButtonBox QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #f6f8fb, stop:1 #eef1f6);
            color: #1e293b;
            border: 1.5px solid #cfd8e6;
            border-radius: 20px;
            padding: 4px 16px;
            min-height: 24px;
            min-width: 80px;
            font-family: 'Segoe UI', 'Bahnschrift';
            font-size: 13px;
            font-weight: 600;
        }
        QMessageBox QPushButton:hover, QDialogButtonBox QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #dbe8ff, stop:1 #c7d9f9);
            border: 1.5px solid #1d4ed8;
            color: #1d4ed8;
        }
        QMessageBox QPushButton:pressed, QDialogButtonBox QPushButton:pressed {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #c7d9f9, stop:1 #b0c9f5);
        }
        QMessageBox QPushButton:disabled, QDialogButtonBox QPushButton:disabled {
            background: #f3f5f9;
            border: 1.5px solid #e0e4ef;
            color: #a0a8b8;
        }
    """


def style_button(btn) -> None:
    """Wendet einheitlichen Button-Stil auf einen Button an."""
    btn.setStyleSheet(get_unified_button_style())
    from PyQt6.QtCore import Qt
    btn.setCursor(Qt.CursorShape.PointingHandCursor)


def get_shimmer_effect_css() -> str:
    """
    Gibt CSS für einen Shimmer-Effekt zurück, der auf Text angewendet werden kann.
    Dieser Effekt simuliert den angeforderten CSS-Effekt für Qt Stylesheets.
    Hinweis: Qt Stylesheets unterstützen keine @keyframes oder komplexe Animationen wie CSS3.
    Wir können jedoch einen statischen Gradienten oder eine einfache Farbe verwenden,
    die dem Look nahe kommt, oder wir müssen QGraphicsEffect verwenden (was komplexer ist).
    
    Da der User explizit nach dem Effekt für die Vorschau gefragt hat, und die Vorschau
    ein QLabel mit Pixmap ist, können wir den Effekt nicht direkt per CSS auf das Bild anwenden.
    
    Wenn der User den Text "Vorschau wird geladen..." meint:
    """
    return """
        /* Shimmer Effect Simulation */
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #a960ee, stop:0.25 #ff333d, stop:0.5 #ffcb57, stop:0.75 #90e0ff, stop:1 #a960ee);
        color: transparent;
        -webkit-background-clip: text;
        background-clip: text;
    """

