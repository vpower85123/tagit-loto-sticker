"""Pfad- und Verzeichnis-Management.

Ausgelagert, damit andere Module (Config, Generatoren, UI) konsistent darauf zugreifen können.
"""
from pathlib import Path
from typing import ClassVar


class PathManager:
    BASE_DIR: ClassVar[Path] = Path(__file__).parent.parent  # Gehe eine Ebene höher (aus core/)
    CONFIG_DIR: ClassVar[Path] = BASE_DIR / "config"
    CONFIG_PATH: ClassVar[Path] = CONFIG_DIR / "config.json"
    EXPORT_CONFIG_PATH: ClassVar[Path] = CONFIG_DIR / "export_config.json"
    BUTTON_SETTINGS_PATH: ClassVar[Path] = CONFIG_DIR / "button_settings.json"
    EQUIPMENT_PATH: ClassVar[Path] = CONFIG_DIR / "equipment.json"
    FONTS_DIR: ClassVar[Path] = BASE_DIR / "fonts"
    SYMBOLS_DIR: ClassVar[Path] = BASE_DIR / "symbols"
    PROJECTS_DIR: ClassVar[Path] = BASE_DIR / "projects"
    DEFAULT_FONT: ClassVar[Path] = FONTS_DIR / "arialbd.ttf"  # Fallback / kann ersetzt werden

    @classmethod
    def initialize(cls):
        cls.CONFIG_DIR.mkdir(exist_ok=True)
        cls.FONTS_DIR.mkdir(exist_ok=True)
        cls.SYMBOLS_DIR.mkdir(exist_ok=True)
        cls.PROJECTS_DIR.mkdir(exist_ok=True)

__all__ = ["PathManager"]
