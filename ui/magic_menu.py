"""
Magic Menu Button & Bar — Pill-styled navigation tabs.
"""

from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
                              QButtonGroup, QProgressBar, QLabel, QSizePolicy)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont, QIcon
from PyQt6.QtSvg import QSvgRenderer
from pathlib import Path
import qtawesome as qta


# ── Tab-specific accent colours ──────────────────────────────────────
_TAB_SCHEMES = [
    {"primary": "#FACC15", "secondary": "#EAB308", "text": "#1f2937"},  # Sticker / Yellow
    {"primary": "#a855f7", "secondary": "#9333ea", "text": "#ffffff"},  # Equipment / Purple
    {"primary": "#3b82f6", "secondary": "#2563eb", "text": "#ffffff"},  # Export / Blue
]


def _menu_pill_css(primary: str, secondary: str, text_clr: str) -> str:
    """Return pill CSS for one MagicMenuButton."""
    return f"""
    MagicMenuButton {{
        background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                     stop:0 #f6f8fb, stop:1 #eef1f6);
        color: #6b7280;
        border: 1.5px solid #e0e3e8;
        border-radius: 20px;
        font: 13px 'Segoe UI DemiBold';
        padding: 4px 10px;
        min-height: 24px;
        text-align: left;
    }}
    MagicMenuButton:hover {{
        background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                     stop:0 #dbe8ff, stop:1 #c7d9f9);
        border-color: {primary};
        color: #374151;
    }}
    MagicMenuButton:checked {{
        background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                     stop:0 {primary}, stop:1 {secondary});
        border: 1.5px solid {secondary};
        color: {text_clr};
    }}
    MagicMenuButton:pressed {{
        background: {secondary};
    }}
    """


class MagicMenuButton(QPushButton):
    """Pill-shaped tab button for the sidebar navigation."""

    def __init__(self, icon_text: str, label_text: str, parent=None, tab_index: int = 0):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(120, 42)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self._tab_index = tab_index
        scheme = _TAB_SCHEMES[min(tab_index, len(_TAB_SCHEMES) - 1)]

        # --- Icon ---
        icon_name = icon_text
        if icon_text == "CUSTOM_LOTO":
            icon_name = "ph.lightning-fill"
        ico = qta.icon(icon_name, color="#6b7280")
        self.setIcon(ico)
        self.setIconSize(QSize(20, 20))

        # Store icon names for state-aware recolour
        self._icon_name = icon_name
        self._scheme = scheme

        # --- Text ---
        self.setText(f"  {label_text}")

        # --- CSS ---
        self.setStyleSheet(_menu_pill_css(scheme["primary"], scheme["secondary"], scheme["text"]))

    # Recolour icon on check-state change
    def checkStateSet(self):
        super().checkStateSet()
        self._refresh_icon()

    def _refresh_icon(self):
        if self.isChecked():
            clr = self._scheme["text"]
        else:
            clr = "#6b7280"
        ico = qta.icon(self._icon_name, color=clr)
        self.setIcon(ico)

class MagicMenuBar(QWidget):
    """Container for MagicMenuButtons - arranged vertically on the left."""
    
    tabSelected = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # Vertikales Layout - genug Breite für Icons
        self.setFixedWidth(140)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        # Use light background to match app theme
        self.setStyleSheet("background: #f8f9fb; border-right: 1px solid #e5e7eb;")
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(0)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self.main_layout.setContentsMargins(10, 12, 10, 12)
        
        # Logo oben
        self._add_logo()
        # Erstes Icon deutlich tiefer setzen
        self.main_layout.addSpacing(20)
        
        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)
        self.btn_group.idClicked.connect(self.tabSelected.emit)
        
        # Define Tabs
        self.add_tab(0, "CUSTOM_LOTO", "Sticker")
        self.add_tab(1, "ph.buildings", "Equipment")
        self.add_tab(2, "ph.export", "Export")
        
        self.main_layout.addStretch()
        
        # Vertical Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setOrientation(Qt.Orientation.Vertical)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedWidth(6)
        self.progress_bar.setFixedHeight(120)
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background-color: rgba(0,0,0,0.05);
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FACC15, stop:1 #EAB308);
                border-radius: 3px;
            }
        """)
        self.main_layout.addWidget(self.progress_bar, 0, Qt.AlignmentFlag.AlignHCenter)
        self.main_layout.addSpacing(20)
        
        # Select first by default
        first_btn = self.btn_group.button(0)
        if first_btn:
            first_btn.setChecked(True)

    def add_tab(self, id, icon, text):
        # Gleicher Abstand zwischen allen Tabs
        if self.btn_group.buttons():
            self.main_layout.addSpacing(8)
        btn = MagicMenuButton(icon, text, tab_index=id)
        self.main_layout.addWidget(btn, 0, Qt.AlignmentFlag.AlignHCenter)
        self.btn_group.addButton(btn, id)

    def set_current_index(self, index):
        btn = self.btn_group.button(index)
        if btn:
            btn.setChecked(True)

    def _add_logo(self):
        """Logo über den Tabs hinzufügen mit Farbwechsel-Effekt"""
        from PyQt6.QtCore import QTimer
        from PyQt6.QtWidgets import QGraphicsColorizeEffect
        import sys
        
        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_label.setFixedSize(130, 90)
        self.logo_label.setStyleSheet("background: transparent; border: none;")
        
        # SVG Logo laden - EXE-kompatible Pfade
        if getattr(sys, 'frozen', False):
            # EXE-Modus
            base_path = Path(sys._MEIPASS)
        else:
            # Entwicklungsmodus
            base_path = Path(__file__).parent.parent.parent
        
        svg_path = base_path / "TAG!T Logo.svg"
        pdf_path = base_path / "TAG!T Logo.pdf"
        
        # Fallback-Pfade
        if not svg_path.exists():
            svg_path = base_path / "LOGO Tag!T.svg"
        if not pdf_path.exists():
            pdf_path = base_path / "LOGO Tag!T.pdf"
        
        pixmap = None
        
        if svg_path.exists():
            try:
                renderer = QSvgRenderer(str(svg_path))
                if renderer.isValid():
                    # Originalgröße des SVG ermitteln
                    svg_size = renderer.defaultSize()
                    # Skalieren mit Beibehaltung des Seitenverhältnisses
                    target_width = 130
                    target_height = 90
                    scale_x = target_width / svg_size.width()
                    scale_y = target_height / svg_size.height()
                    scale = min(scale_x, scale_y)  # Kleinerer Faktor für Aspect Ratio
                    
                    final_width = int(svg_size.width() * scale)
                    final_height = int(svg_size.height() * scale)
                    
                    pixmap = QPixmap(final_width, final_height)
                    pixmap.fill(Qt.GlobalColor.transparent)
                    painter = QPainter(pixmap)
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                    renderer.render(painter)
                    painter.end()
            except Exception:
                pass
        
        if pixmap is None and pdf_path.exists():
            try:
                import fitz
                pdf_doc = fitz.open(str(pdf_path))
                page = pdf_doc[0]
                mat = fitz.Matrix(0.5, 0.5)
                pix = page.get_pixmap(matrix=mat, alpha=True)
                img_data = pix.tobytes("png")
                pixmap = QPixmap()
                pixmap.loadFromData(img_data)
                pixmap = pixmap.scaled(130, 90, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                pdf_doc.close()
            except Exception:
                pass
        
        if pixmap and not pixmap.isNull():
            self.logo_label.setPixmap(pixmap)
            
            # Farbwechsel-Animation
            self.logo_color_effect = QGraphicsColorizeEffect()
            self.logo_color_effect.setStrength(0.40)
            self.logo_label.setGraphicsEffect(self.logo_color_effect)

            # Sanfte Markenfarben statt aggressivem Rainbow
            self.logo_phase = 0.0
            self.logo_palette = [
                QColor("#d946ef"),  # Magenta
                QColor("#a855f7"),  # Purple
                QColor("#3b82f6"),  # Blue
            ]
            self.logo_timer = QTimer(self)
            self.logo_timer.timeout.connect(self._change_logo_color)
            self.logo_timer.start(30)
            self._change_logo_color()
        
        self.main_layout.addWidget(self.logo_label)
        self.main_layout.addSpacing(10)
    
    def _change_logo_color(self):
        """Sanfter Logo-Glow mit weichem Farbverlauf."""
        import math

        if not hasattr(self, "logo_palette") or not self.logo_palette:
            return

        # Sichtbare, aber weiterhin weiche Animation
        self.logo_phase += 0.06

        # Palette-Interpolation (Magenta -> Purple -> Blue -> ...)
        palette_len = len(self.logo_palette)
        pos = (self.logo_phase * 0.90) % palette_len
        idx = int(pos)
        next_idx = (idx + 1) % palette_len
        t = pos - idx

        c1 = self.logo_palette[idx]
        c2 = self.logo_palette[next_idx]
        r = int(c1.red() + (c2.red() - c1.red()) * t)
        g = int(c1.green() + (c2.green() - c1.green()) * t)
        b = int(c1.blue() + (c2.blue() - c1.blue()) * t)

        color = QColor(r, g, b)
        self.logo_color_effect.setColor(color)

        # Deutlich sichtbarer, aber nicht hektischer Glow
        shimmer = 0.34 + 0.22 * (0.5 + 0.5 * math.sin(self.logo_phase * 1.6))
        self.logo_color_effect.setStrength(shimmer)
