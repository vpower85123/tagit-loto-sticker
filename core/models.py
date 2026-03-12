"""Datenmodelle (Enums & Konfigurations-Dataclasses).

Trennen Fachlogik (Generatoren, UI) von reinen Datenstrukturen.
"""
from dataclasses import dataclass, asdict
from enum import Enum, auto
from typing import List, Tuple, Optional, Dict, Any

from core.constants import MM_PER_INCH


class SymbolType(Enum):
    ELECTRICAL = auto()
    PNEUMATIC = auto()
    HYDRAULIC = auto()
    CHEMICAL = auto()
    THERMAL = auto()
    STEAM = auto()
    GRAVITATIONAL = auto()
    KINETIC = auto()
    MECHANICAL = auto()
    RADIATION = auto()
    MIXED = auto()
    OTHER = auto()

    @classmethod
    def names(cls) -> List[str]:
        return [s.name.capitalize() for s in cls]


class Theme(Enum):
    LIGHT = {"bg": "white", "fg": "black", "accent": "#FFC000"}
    DARK = {"bg": "#333333", "fg": "white", "accent": "#FFA500"}


@dataclass
class BaseConfig:
    width_mm: float
    height_mm: float
    dpi: int
    corner_radius: int
    outline_width: int
    font_path: str
    auto_adjust: bool

    @property
    def px_per_mm(self) -> float:
        return self.dpi / MM_PER_INCH

    @property
    def size_px(self) -> Tuple[int, int]:
        return (int(self.width_mm * self.px_per_mm), int(self.height_mm * self.px_per_mm))

    @property
    def border_width(self) -> int:
        return self.outline_width


@dataclass
class StickerConfig(BaseConfig):
    sticker_color: str
    font_size_mm: float
    line_height_mm: float
    symbols_dir: str
    symbol_corner_radius: int
    symbol_size_mm: float = 0.0
    symbol_offset_x_mm: float = 0.0
    symbol_offset_y_mm: float = 0.0
    text_offset_x: int = 0
    text_offset_y: int = 0
    qr_mode_enabled: bool = False
    qr_placeholder_text: str = "QR"
    qr_placeholder_bg: str = "#FFFFFF"
    qr_image_path: Optional[str] = None
    preview_scale: float = 0.7
    export_exact_three_rows: bool = False
    export_margin_mm: float = 8.0
    export_gap_mm: float = 5.0
    export_min_scale: float = 0.8

    def __post_init__(self):
        if not self.symbol_size_mm:
            self.symbol_size_mm = self.height_mm - 2

    @property
    def font_size_px(self) -> int:
        return int(self.font_size_mm * self.px_per_mm)

    @property
    def line_height_px(self) -> int:
        return int(self.line_height_mm * self.px_per_mm)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CountConfig(BaseConfig):
    font_size_mm: float = 8.0
    line_height_mm: float = 9.0
    count_print_copies: int = 1
    header_text: str = "TOTAL COUNT OF LOTO POINTS –"
    bg_color: str = "#FFFFFF"
    stripe_color: str = "#FF0000"
    show_stripes: bool = True
    header_margin_mm: float = 3.0
    text_spacing_mm: float = 5.0

    @property
    def font_size_px(self) -> int:
        return int(self.font_size_mm * self.px_per_mm)

    @property
    def line_height_px(self) -> int:
        return int(self.line_height_mm * self.px_per_mm)


@dataclass
class ExportConfig:
    sheet_width_mm: float = 210.0
    sheet_height_mm: float = 297.0
    orientation_mode: str = 'auto'  # portrait | landscape | auto | custom
    margin_mm: float = 8.0
    gap_mm: float = 4.0
    min_scale: float = 0.8
    exact_three_rows: bool = False
    include_count_header: bool = True
    auto_height: bool = False  # NEU: dynamische Höhenberechnung für benutzerdefiniertes Format
    export_mode: str = 'multi'  # multi | single - single: jeden Sticker mit eigenem Count-Sticker
    roll_mode: bool = False  # Rollenmodus aktiv (auto_height)
    roll_width_mm: float = 500.0  # Rollenbreite in mm
    max_columns: Optional[int] = None
    max_rows: Optional[int] = None
    force_rows: Optional[int] = None
    force_cols: Optional[int] = None
    sticker_rotate_mode: str = 'auto'  # none | always | auto | locked
    sticker_rotation_locked: Optional[bool] = None  # Gespeicherte Rotation wenn locked=True (None bedeutet not yet calculated)

    def normalized_dims(self):
        w, h = self.sheet_width_mm, self.sheet_height_mm
        if self.orientation_mode == 'portrait':
            return min(w, h), max(w, h)
        if self.orientation_mode == 'landscape':
            return max(w, h), min(w, h)
        return w, h


@dataclass
class ThemeConfig:
    """Konfiguration für das UI-Theme."""
    mode: str = "light"  # "light" oder "dark"
    custom_colors: Optional[Dict[str, str]] = None  # Benutzerdefinierte Farben (Overrides)

    def __post_init__(self):
        if self.custom_colors is None:
            self.custom_colors = {}


__all__ = [
    'SymbolType', 'Theme', 'BaseConfig', 'StickerConfig', 'CountConfig', 'ExportConfig', 'ThemeConfig'
]
