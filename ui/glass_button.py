"""
GlassGlowButton – Modern Pill Button (einheitlicher Stil für die gesamte App).

Verwendet ausschließlich Qt-Stylesheets (kein custom paintEvent).
Unterstützt Light- und Dark-Mode über den `dark_mode`-Parameter.
"""

from PyQt6.QtWidgets import QPushButton
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont
import json
from pathlib import Path


# ============================================================================
# Globale Button-Einstellungen (Legacy support)
# ============================================================================
class ButtonSettings:
    """Globale Einstellungen für Buttons."""

    _defaults = {
        "border_radius": 20.0,
        "font_size": 13,
        "min_height": 28,
    }
    _settings = _defaults.copy()
    _registered_buttons: list = []

    @classmethod
    def get(cls, key: str):
        return cls._settings.get(key, cls._defaults.get(key))

    @classmethod
    def set(cls, key: str, value):
        cls._settings[key] = value
        cls._notify_buttons()

    @classmethod
    def set_all(cls, settings: dict):
        cls._settings.update(settings)
        cls._notify_buttons()

    @classmethod
    def reset(cls):
        cls._settings = cls._defaults.copy()
        cls._notify_buttons()

    @classmethod
    def register_button(cls, button):
        if button not in cls._registered_buttons:
            cls._registered_buttons.append(button)

    @classmethod
    def unregister_button(cls, button):
        if button in cls._registered_buttons:
            cls._registered_buttons.remove(button)

    @classmethod
    def _notify_buttons(cls):
        for btn in cls._registered_buttons[:]:
            try:
                btn.update()
            except Exception:
                pass

    @classmethod
    def load_from_file(cls, filepath=None):
        if filepath is None:
            path = Path(__file__).parent.parent / "button_settings.json"
        else:
            path = Path(filepath)
        try:
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    cls._settings.update(json.load(f))
                    cls._notify_buttons()
        except Exception:
            pass

    @classmethod
    def save_to_file(cls, filepath=None):
        if filepath is None:
            path = Path(__file__).parent.parent / "button_settings.json"
        else:
            path = Path(filepath)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cls._settings, f, indent=2)


# ============================================================================
# Pill-Button Stylesheet-Generator
# ============================================================================

def _pill_style(dark: bool = False) -> str:
    """Gibt das vollständige Modern-Pill-Stylesheet zurück (immer Light)."""
    return """
        QPushButton {
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                        stop:0 #f6f8fb, stop:1 #eef1f6);
            color: #1e293b;
            border: 1.5px solid #cfd8e6;
            border-radius: 20px;
            padding: 4px 16px;
            min-height: 24px;
            font-family: 'Segoe UI', 'Bahnschrift';
            font-size: 13px;
            font-weight: 600;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                        stop:0 #dbe8ff, stop:1 #c7d9f9);
            border: 1.5px solid #1d4ed8;
            color: #1d4ed8;
        }
        QPushButton:pressed {
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                        stop:0 #c7d9f9, stop:1 #b0c9f5);
        }
        QPushButton:disabled {
            background: #f3f5f9;
            border: 1.5px solid #e0e4ef;
            color: #a0a8b8;
        }
    """


class GlassGlowButton(QPushButton):
    """Modern Pill Button — einheitlicher Button-Stil für die gesamte App.

    Kein custom paintEvent mehr. Nur Qt-Stylesheet: abgerundete Pillenform,
    dezenter Hover-Gradient, Dark/Light-Unterstützung.
    """

    def __init__(self, text="", parent=None, dark_mode=False):
        super().__init__(text, parent)
        self.setObjectName("GlassGlowButton")
        self._dark = dark_mode

        self.setFont(QFont("Segoe UI", 13, QFont.Weight.DemiBold))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(_pill_style(dark_mode))
        self.setMinimumHeight(28)

        ButtonSettings.register_button(self)

    # --- public helpers kept for compatibility ----------------------------

    def setDarkMode(self, dark: bool):
        self._dark = dark
        self.setStyleSheet(_pill_style(dark))

    def setAutoResize(self, enabled: bool):
        """Legacy — no-op."""
        pass

    def setBorderRadius(self, radius):
        """Legacy — ignored; pill radius is set via stylesheet."""
        pass

    def refresh_settings(self):
        self.setStyleSheet(_pill_style(self._dark))
        self.update()

    def __del__(self):
        ButtonSettings.unregister_button(self)


__all__ = ["GlassGlowButton", "ButtonSettings", "_pill_style"]
