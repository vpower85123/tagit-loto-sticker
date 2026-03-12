"""Tab UI Builders für die Sticker App.

Diese Module enthält die UI-Builder Methoden für alle Tabs:
- _build_start_tab: Überblicks-Tab mit Navigations-Buttons
- _build_sticker_tab: Sticker-Erstellungs-Tab (Hauptfunktionalität)
- _build_equipment_tab: Equipment-Verwaltungs-Tab
- _build_export_tab: Export-Einstellungs-Tab

Diese Methoden sind aus der Hauptklasse extrahiert um Code-Größe zu reduzieren.
Sie werden in StickerApp.__init__ aufgerufen.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QPushButton, QLineEdit, QComboBox, QTreeWidget,
    QListWidget, QRadioButton, QButtonGroup, QDoubleSpinBox,
    QDial, QMessageBox, QSizePolicy, QSlider, QAbstractSpinBox,
    QGridLayout, QGraphicsDropShadowEffect, QScrollArea, QFrame
)
from PyQt6.QtGui import QFont, QPalette, QColor, QPainter, QPen, QBrush, QPixmap, QIcon, QPainterPath, QLinearGradient, QTransform
from ui.theme import create_input_stylesheet, create_groupbox_stylesheet, Theme, get_contrasting_text_color, get_theme_colors
from PyQt6.QtCore import Qt, QTimer, QSize, QPoint, QRectF, QPointF
import math
import qtawesome as qta

# UI-Komponenten
from ui.glass_button import GlassGlowButton
from dialogs.equipment_dialog import EquipmentSelectionDialog
from ui.components import SmoothDial, ModernComboBox, ShimmerLabel
from ui.spinboxes import StyledDoubleSpinBox, StyledSpinBox
from ui.collapsible_section import CollapsibleSection


def add_depth_shadow(widget):
    """Fügt weichen Gradient-Schatten für subtilen Übergang hinzu."""
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(24)
    shadow.setXOffset(0)
    shadow.setYOffset(2)
    shadow.setColor(QColor(0, 0, 0, 12))
    widget.setGraphicsEffect(shadow)


def _get_card_style(self, object_name: str) -> str:
    """Erstellt den Style für Card-Container unter Berücksichtigung von Custom Colors."""
    custom_colors = getattr(self.theme_config, 'custom_colors', {}) if hasattr(self, 'theme_config') else {}
    colors = get_theme_colors(Theme.LIGHT, custom_colors)
    
    element_bg = custom_colors.get('element_bg', colors.get('input_bg'))
    border_color = colors.get('border')
    
    return (
        f"QWidget#{object_name} {{"
        f"  background: {element_bg};"
        f"  border: none;"
        "  border-radius: 0px;"
        "  padding: 0px;"
        "}"
    )


def _create_glass_button(self, text: str) -> GlassGlowButton:
    """Erstellt einen GlassGlowButton mit Theme-Anpassung."""
    btn = GlassGlowButton(text, dark_mode=False)
    # Höhe und Schriftgröße kommen aus ButtonSettings
    return btn


def create_symbol_icon(name, size=64, color="#ffffff"):
    """Erstellt ein Vektor-Icon als QIcon (Modern Gradient Style)."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    # --- Modern Gradient Style ---
    base_color = QColor(color)
    
    # Gradient: Top-Left (Light) -> Bottom-Right (Darker)
    gradient = QLinearGradient(0, 0, size, size)
    gradient.setColorAt(0.0, base_color)
    gradient.setColorAt(1.0, base_color.darker(130)) # 30% darker
    
    painter.setBrush(QBrush(gradient))
    painter.setPen(Qt.PenStyle.NoPen)
    
    # Margin
    margin = size * 0.15
    w = size - 2 * margin
    h = size - 2 * margin
    x = margin
    y = margin
    
    cx = size / 2
    cy = size / 2
    
    path = QPainterPath()
    
    if name == "plus":
        # Rounded Plus
        thickness = w * 0.22
        radius = thickness / 2
        # Vertical
        path.addRoundedRect(cx - thickness/2, y, thickness, h, radius, radius)
        # Horizontal
        path.addRoundedRect(x, cy - thickness/2, w, thickness, radius, radius)
        
    elif name == "search":
        # Modern Search
        r_outer = w * 0.38
        r_inner = r_outer * 0.65
        
        # Ring
        ring = QPainterPath()
        ring.addEllipse(QPointF(x + r_outer, y + r_outer), r_outer, r_outer)
        inner = QPainterPath()
        inner.addEllipse(QPointF(x + r_outer, y + r_outer), r_inner, r_inner)
        ring = ring.subtracted(inner)
        path.addPath(ring)
        
        # Handle (Rounded)
        handle_len = w * 0.35
        handle_w = w * 0.15
        
        rcx, rcy = x + r_outer, y + r_outer
        
        painter.translate(rcx, rcy)
        painter.rotate(45)
        # Draw handle as a separate path to add to main path? 
        # Easier to just draw it directly or add to path.
        # Let's add to path for shadow consistency.
        handle_path = QPainterPath()
        handle_path.addRoundedRect(QRectF(r_outer - 2, -handle_w/2, handle_len, handle_w), handle_w/2, handle_w/2)
        
        # Transform handle path back to world coords
        transform = QTransform()
        transform.translate(rcx, rcy)
        transform.rotate(45)
        path.addPath(transform.map(handle_path))
        
        painter.rotate(-45)
        painter.translate(-rcx, -rcy)
        
    elif name == "up":
        # Soft Arrow Up
        head_h = h * 0.45
        shaft_w = w * 0.4
        radius = 4.0
        
        # We construct a polygon and add rounded corners if possible, 
        # or just use standard path with rounded joins.
        
        p = QPainterPath()
        p.moveTo(cx, y) # Tip
        p.lineTo(x + w, y + head_h)
        p.lineTo(cx + shaft_w/2, y + head_h)
        p.lineTo(cx + shaft_w/2, y + h - radius)
        # Bottom right corner
        p.quadTo(cx + shaft_w/2, y + h, cx + shaft_w/2 - radius, y + h)
        p.lineTo(cx - shaft_w/2 + radius, y + h)
        # Bottom left corner
        p.quadTo(cx - shaft_w/2, y + h, cx - shaft_w/2, y + h - radius)
        p.lineTo(cx - shaft_w/2, y + head_h)
        p.lineTo(x, y + head_h)
        p.closeSubpath()
        
        path = p
        
    elif name == "down":
        # Soft Arrow Down
        head_h = h * 0.45
        shaft_w = w * 0.4
        radius = 4.0
        
        p = QPainterPath()
        p.moveTo(cx, y + h) # Tip
        p.lineTo(x + w, y + h - head_h)
        p.lineTo(cx + shaft_w/2, y + h - head_h)
        p.lineTo(cx + shaft_w/2, y + radius)
        # Top right corner
        p.quadTo(cx + shaft_w/2, y, cx + shaft_w/2 - radius, y)
        p.lineTo(cx - shaft_w/2 + radius, y)
        # Top left corner
        p.quadTo(cx - shaft_w/2, y, cx - shaft_w/2, y + radius)
        p.lineTo(cx - shaft_w/2, y + h - head_h)
        p.lineTo(x, y + h - head_h)
        p.closeSubpath()
        
        path = p

    elif name == "close":
        # Rounded X
        thickness = w * 0.18
        radius = thickness / 2
        
        # Center
        painter.translate(cx, cy)
        painter.rotate(45)
        
        p1 = QPainterPath()
        p1.addRoundedRect(QRectF(-w/2, -thickness/2, w, thickness), radius, radius)
        path.addPath(painter.transform().map(p1)) # Map to world
        
        painter.rotate(90)
        p2 = QPainterPath()
        p2.addRoundedRect(QRectF(-w/2, -thickness/2, w, thickness), radius, radius)
        # We need to map this correctly. 
        # Actually, let's just add rects to a local path and map it?
        # Or simpler:
        
        painter.resetTransform()
        
        # Re-do with transform mapping
        t1 = QTransform()
        t1.translate(cx, cy)
        t1.rotate(45)
        path.addPath(t1.map(p1))
        
        t2 = QTransform()
        t2.translate(cx, cy)
        t2.rotate(135) # 45 + 90
        path.addPath(t2.map(p1))
        
    elif name == "trash":
        # Modern Trash
        lid_h = h * 0.12
        lid_w = w * 1.0
        
        # Lid Handle
        handle_w = w * 0.3
        handle_h = h * 0.06
        path.addRoundedRect(cx - handle_w/2, y, handle_w, handle_h, 2, 2)
        
        # Lid (Rounded)
        path.addRoundedRect(x, y + handle_h + 2, lid_w, lid_h, 4, 4)
        
        # Body
        body_w = w * 0.75
        body_h = h * 0.7
        body_x = cx - body_w/2
        body_y = y + handle_h + lid_h + 6
        
        # Tapered body?
        body = QPainterPath()
        body.addRoundedRect(body_x, body_y, body_w, body_h, 8, 8)
        
        # Stripes
        stripe_w = body_w * 0.12
        stripe_h = body_h * 0.5
        stripe_y = body_y + body_h * 0.25
        
        s1 = QPainterPath()
        s1.addRoundedRect(cx - stripe_w*1.8, stripe_y, stripe_w, stripe_h, 2, 2)
        s1.addRoundedRect(cx - stripe_w*0.0, stripe_y, stripe_w, stripe_h, 2, 2) # Center
        s1.addRoundedRect(cx + stripe_w*1.8, stripe_y, stripe_w, stripe_h, 2, 2)
        
        path.addPath(body.subtracted(s1))

    elif name == "pdf_extractor":
        # PDF Document
        doc_w = w * 0.75
        doc_h = h * 0.9
        doc_x = cx - doc_w/2
        doc_y = cy - doc_h/2
        
        # Main Doc
        path.addRoundedRect(doc_x, doc_y, doc_w, doc_h, 6, 6)
        
        # Text Lines (Subtracted)
        line_h = doc_h * 0.08
        line_gap = doc_h * 0.18
        start_y = doc_y + doc_h * 0.3
        
        lines = QPainterPath()
        for i in range(3):
            ly = start_y + i * line_gap
            lines.addRoundedRect(doc_x + doc_w*0.2, ly, doc_w*0.6, line_h, 2, 2)
            
        path = path.subtracted(lines)

    elif name == "sort":
        # Sort Icon (Bars + A-Z)
        # Draw "A-Z" text but nicer
        font = painter.font()
        font.setBold(True)
        font.setPixelSize(int(h * 0.5))
        painter.setFont(font)
        
        # Draw Shadow for Text
        painter.setPen(QColor(0, 0, 0, 60))
        painter.drawText(QRectF(2, 2, size, size), Qt.AlignmentFlag.AlignCenter, "AZ")
        
        # Draw Main Text
        painter.setPen(base_color)
        painter.drawText(QRectF(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, "AZ")
        
        # Add a small arrow next to it?
        # Maybe too crowded.
        painter.end()
        return QIcon(pix)

    # --- Draw Shadow ---
    painter.save()
    painter.translate(3, 3)
    painter.setBrush(QColor(0, 0, 0, 60)) # Soft shadow
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawPath(path)
    painter.restore()

    # --- Draw Main Shape ---
    painter.drawPath(path)
    
    # --- Add Shine/Highlight (Top Left) ---
    # Optional: Adds a "plastic" look
    # highlight = QPainterPath()
    # highlight.addEllipse(x + w*0.2, y + h*0.2, w*0.2, h*0.1)
    # painter.setBrush(QColor(255, 255, 255, 80))
    # painter.drawPath(highlight)
    
    painter.end()
    return QIcon(pix)


def build_start_tab(self):
    """Start-Tab mit Übersicht"""
    start_widget = QWidget()
    layout = QVBoxLayout(start_widget)

    # Titel
    title = QLabel("LOTO Sticker Generator")
    title.setFont(QFont("Arial", int(48 * self.ui_scale), QFont.Weight.Bold))
    title.setAlignment(Qt.AlignmentFlag.AlignCenter)
    # Light-only styling
    title.setStyleSheet("color: #000000; font-weight: bold;")
    layout.addWidget(title)
    self.title_label = title  # Speichere für Theme-Wechsel

    subtitle = QLabel("LOTO Sticker erstellen und verwalten")
    subtitle.setFont(QFont("Arial", int(18 * self.ui_scale), QFont.Weight.Bold))
    subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
    subtitle.setStyleSheet("color: #000000; font-weight: bold;")
    layout.addWidget(subtitle)
    self.subtitle_label = subtitle  # Speichere für Theme-Wechsel

    # Buttons für schnellen Zugriff
    button_layout = QHBoxLayout()
    button_layout.addStretch()  # Zentrieren
    
    # Feste Breite für alle Buttons
    button_width = 280

    sticker_btn = self.create_wave_button("🎫 Sticker erstellen")
    sticker_btn.setFixedWidth(button_width)
    sticker_btn.clicked.connect(lambda: self.tab_widget.setCurrentIndex(1))
    button_layout.addWidget(sticker_btn)

    equipment_btn = self.create_wave_button("Equipment verwalten")
    equipment_btn.setIcon(qta.icon('ph.buildings', color='#fff'))
    equipment_btn.setFixedWidth(button_width)
    equipment_btn.clicked.connect(lambda: self.tab_widget.setCurrentIndex(2))
    button_layout.addWidget(equipment_btn)

    export_btn = self.create_wave_button("Export")
    export_btn.setIcon(qta.icon('ph.export', color='#fff'))
    export_btn.setFixedWidth(button_width)
    export_btn.clicked.connect(lambda: self.tab_widget.setCurrentIndex(3))
    button_layout.addWidget(export_btn)

    button_layout.addStretch()  # Zentrieren
    layout.addLayout(button_layout)

    # Info-Text
    info = QLabel(
        "Erstellen und verwalten Sie LOTO Sticker für Ihre Anlagen.\n"
        "Verwalten Sie Equipment und exportieren Sie als PDF oder ZIP."
    )
    info.setFont(QFont("Arial", int(12 * self.ui_scale)))
    info.setAlignment(Qt.AlignmentFlag.AlignCenter)
    info.setWordWrap(True)
    layout.addWidget(info)

    layout.addStretch()

    self.tab_widget.addTab(start_widget, "🏠 Start")


def build_sticker_tab(self):
    """Sticker-Erstellungs-Tab"""
    from core.models import SymbolType
    from PyQt6.QtWidgets import QSizePolicy
    
    scale_factor = getattr(self, 'ui_scale', 1.0)
    body_font = QFont("Bahnschrift", max(9, int(10 * scale_factor)))
    label_font = QFont("Bahnschrift", max(9, int(9 * scale_factor)))
    label_font.setWeight(QFont.Weight.DemiBold)
    heading_font = QFont("Bahnschrift", max(12, int(13 * scale_factor)))
    heading_font.setWeight(QFont.Weight.Bold)
    subheading_font = QFont("Bahnschrift", max(10, int(11 * scale_factor)))

    primary_text = "#1f2a37"
    secondary_text = "#5f6c80"
    tertiary_text = "#7a8597"

    sticker_widget = QWidget()
    # Keine eigene Hintergrundfarbe - nutze App-Hintergrund
    
    layout = QHBoxLayout(sticker_widget)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(18)

    # Input Card - Inhalt vorbereiten
    input_card_content = QWidget()
    input_card_content.setObjectName("input_card_content")
    input_card_content.setStyleSheet("QWidget { background-color: transparent; }")

    card_layout = QVBoxLayout(input_card_content)
    card_layout.setContentsMargins(12, 4, 12, 8)
    card_layout.setSpacing(6)

    # Kein extra Titel/Subtitle mehr - kommt in CollapsibleSection Header
    # card_layout.addSpacing(4)

    input_layout = QVBoxLayout()
    input_layout.setSpacing(20)
    input_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    card_layout.addLayout(input_layout)
    
    # Modern Styling
    custom_colors = getattr(self.theme_config, 'custom_colors', {}) if hasattr(self, 'theme_config') else {}
    element_bg = custom_colors.get('element_bg')
    colors = get_theme_colors(Theme.LIGHT, custom_colors)
    
    if element_bg:
        text_color = get_contrasting_text_color(element_bg)
        label_style = f"color: {text_color}; font-weight: 600; font-size: 12px;"
    else:
        label_style = f"color: {colors['fg']}; font-weight: 600; font-size: 12px; font-family: 'Bahnschrift';"
    
    bg_color = colors.get('input_bg')
    fg_color = colors.get('input_fg')
    border_color = colors.get('border')
    focus_color = colors.get('accent')
    hover_bg = colors.get('hover', bg_color)
    
    input_style = f"""
        QLineEdit {{
            border: 2px solid {border_color};
            border-radius: 14px;
            padding: 10px 16px;
            background-color: {bg_color};
            color: {fg_color};
            font-size: 13px;
            font-weight: 500;
        }}
        QLineEdit:hover {{
            border-color: {focus_color};
            background-color: {hover_bg};
        }}
        QLineEdit:focus {{
            border-color: {focus_color};
            background-color: {bg_color};
        }}
        QLineEdit:disabled {{
            opacity: 0.5;
        }}
    """

    self.energy_entry = QLineEdit()
    self.energy_entry.setPlaceholderText("WELCOME TO")
    self.energy_entry.setText("WELCOME TO")  # Default-Wert für Welcome-Sticker
    self.energy_entry.setAlignment(Qt.AlignmentFlag.AlignCenter)
    self.energy_entry.setMinimumWidth(320)
    self.energy_entry.setMaximumWidth(480)
    self.energy_entry.setStyleSheet(input_style)
    self.energy_entry.setFont(body_font)
    self.energy_label = QLabel("Energie-ID:")
    self.energy_label.setStyleSheet(label_style)
    self.energy_label.setFont(label_font)
    input_layout.addWidget(self.energy_entry)

    self.equipment_entry = QLineEdit()
    self.equipment_entry.setPlaceholderText("TAG!T")
    self.equipment_entry.setText("TAG!T")  # Default-Wert für Welcome-Sticker
    self.equipment_entry.setAlignment(Qt.AlignmentFlag.AlignCenter)
    self.equipment_entry.setMinimumWidth(320)
    self.equipment_entry.setMaximumWidth(480)
    self.equipment_entry.setStyleSheet(input_style)
    self.equipment_entry.setFont(body_font)
    self.equipment_label = QLabel("Equipment:")
    self.equipment_label.setStyleSheet(label_style)
    self.equipment_label.setFont(label_font)
    input_layout.addWidget(self.equipment_entry)

    self.description_entry = QLineEdit()
    self.description_entry.setPlaceholderText("z.B. Standort / Bereich / Zusatzinfo…")
    self.description_entry.setText("")  # Standard-Wert leer
    self.description_entry.setAlignment(Qt.AlignmentFlag.AlignCenter)
    self.description_entry.setMinimumWidth(276)
    self.description_entry.setMaximumWidth(436)
    # Spezifisches Styling für Description ohne letter-spacing
    description_input_style = f"""
        QLineEdit {{
            border: 2px solid {border_color};
            border-radius: 14px;
            padding: 10px 16px;
            background-color: {bg_color};
            color: {fg_color};
            font-size: 13px;
            font-weight: 500;
            letter-spacing: 0px;
        }}
        QLineEdit:hover {{
            border-color: {focus_color};
            background-color: {hover_bg};
        }}
        QLineEdit:focus {{
            border-color: {focus_color};
            background-color: {bg_color};
        }}
        QLineEdit:disabled {{
            opacity: 0.5;
        }}
    """
    self.description_entry.setStyleSheet(description_input_style)
    self.description_entry.setFont(body_font)
    self.description_label = QLabel("Description:")
    self.description_label.setStyleSheet(label_style)
    self.description_label.setFont(label_font)
    
    # Description mit Lock-Button - Container zentriert
    description_container = QWidget()
    description_container.setStyleSheet("QWidget { background-color: transparent; }")
    description_layout = QHBoxLayout(description_container)
    description_layout.setContentsMargins(0, 0, 0, 0)
    description_layout.setSpacing(8)
    
    description_layout.addWidget(self.description_entry)
    
    # Lock-Button für Description (Phosphor Icons)
    self.description_lock_btn = QPushButton()
    self.description_lock_btn.setFixedSize(36, 36)
    self.description_lock_btn.setIcon(qta.icon('ph.lock-open', color=fg_color))
    self.description_lock_btn.setIconSize(QSize(20, 20))
    self.description_lock_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    self.description_lock_btn.setToolTip("Description sperren/entsperren")
    self.description_lock_btn.setStyleSheet(f"""
        QPushButton {{
            border: 1px solid {border_color};
            border-radius: 18px;
            background-color: {bg_color};
        }}
        QPushButton:hover {{
            background-color: {hover_bg};
            border-color: {focus_color};
        }}
        QPushButton:pressed {{
            background-color: {border_color};
        }}
        QPushButton:checked {{
            background-color: {hover_bg};
            border-color: {focus_color};
        }}
    """)
    self.description_is_locked = False
    
    def toggle_description_lock():
        """Toggle Lock für Description-Feld"""
        self.description_is_locked = not self.description_is_locked
        if self.description_is_locked:
            self.description_lock_btn.setIcon(qta.icon('ph.lock', color=fg_color))
            locked_bg = colors.get('selection', hover_bg)
            self.description_lock_btn.setStyleSheet(f"""
                QPushButton {{
                    border: 1px solid {focus_color};
                    border-radius: 18px;
                    background-color: {locked_bg};
                }}
                QPushButton:hover {{ background-color: {hover_bg}; }}
            """)
            self.description_entry.setReadOnly(True)
            disabled_bg = colors.get('hover', bg_color)
            self.description_entry.setStyleSheet(input_style + f"QLineEdit {{ background-color: {disabled_bg}; opacity: 0.7; }}")
            # Speichere die Description wenn gelocked
            desc_text = self.description_entry.text()
            if hasattr(self, 'save_description_settings'):
                self.save_description_settings(desc_text, True)
        else:
            self.description_lock_btn.setIcon(qta.icon('ph.lock-open', color=fg_color))
            self.description_lock_btn.setStyleSheet(f"""
                QPushButton {{
                    border: 1px solid {border_color};
                    border-radius: 18px;
                    background-color: {bg_color};
                }}
                QPushButton:hover {{ background-color: {hover_bg}; border-color: {focus_color}; }}
            """)
            self.description_entry.setReadOnly(False)
            self.description_entry.setStyleSheet(input_style)
            # Speichere dass Description unlocked ist
            if hasattr(self, 'save_description_settings'):
                self.save_description_settings("", False)
    
    self.description_lock_btn.clicked.connect(toggle_description_lock)
    description_layout.addWidget(self.description_lock_btn)
    
    # Responsive Breite für Feld + Button + Spacing
    description_container.setMinimumWidth(320)
    description_container.setMaximumWidth(480)
    action_btn_width = 480
    
    self.description_label = QLabel("Description:")
    self.description_label.setStyleSheet(label_style)
    self.description_label.setFont(label_font)
    input_layout.addWidget(description_container)

    advanced_options_container = QWidget()
    advanced_options_container.setStyleSheet("QWidget { background-color: transparent; }")
    advanced_options_layout = QVBoxLayout(advanced_options_container)
    advanced_options_layout.setContentsMargins(0, 0, 0, 0)
    advanced_options_layout.setSpacing(12)

    # Symbol-Typ Auswahl - alle verfügbaren Typen aus SymbolType Enum
    self.symbol_combo = ModernComboBox(dark_mode=False)
    self.symbol_combo.setFont(body_font)
    self.symbol_combo.setMinimumWidth(320)
    self.symbol_combo.setMaximumWidth(480)
    symbol_names = [s.name.capitalize() for s in SymbolType]
    self.symbol_combo.addItems(symbol_names)
    self.symbol_combo.currentIndexChanged.connect(self._on_symbol_changed)
    self.symbol_label = QLabel("Symbol-Typ:")
    self.symbol_label.setStyleSheet(label_style)
    self.symbol_label.setFont(label_font)
    advanced_options_layout.addWidget(self.symbol_combo)

    # Multi/Single LOTO Auswahl (innerhalb Sticker-Daten)
    loto_mode_container = QWidget()
    loto_mode_container.setStyleSheet("QWidget { background-color: transparent; }")
    loto_mode_container.setMinimumWidth(320)
    loto_mode_container.setMaximumWidth(480)
    loto_mode_layout = QHBoxLayout(loto_mode_container)
    loto_mode_layout.setContentsMargins(0, 0, 0, 0)
    loto_mode_layout.setSpacing(15)

    self.single_loto_radio = QRadioButton("Single LOTO")
    self.multi_loto_radio = QRadioButton("Multi LOTO")
    self.no_count_radio = QRadioButton("Kein Count")

    self.loto_button_group = QButtonGroup(self)
    self.loto_button_group.addButton(self.single_loto_radio, 0)
    self.loto_button_group.addButton(self.multi_loto_radio, 1)
    self.loto_button_group.addButton(self.no_count_radio, 2)

    radio_text_color = "#2c3e50"
    radio_accent = "#3498db"
    if element_bg:
        radio_text_color = get_contrasting_text_color(element_bg)
        radio_accent = "#3498db"

    radio_style = f"""
        QRadioButton {{
            color: {radio_text_color};
            font-size: 13px;
            font-weight: 400;
            spacing: 10px;
            padding: 6px 12px;
        }}
        QRadioButton::indicator {{
            width: 16px;
            height: 16px;
            border-radius: 8px;
            border: 1.5px solid rgba(128, 128, 128, 0.3);
            background: transparent;
        }}
        QRadioButton::indicator:hover {{
            border: 1.5px solid {radio_accent};
        }}
        QRadioButton::indicator:checked {{
            border: 1.5px solid {radio_accent};
            background: qradialgradient(cx:0.5, cy:0.5, radius:0.5,
                fx:0.5, fy:0.5,
                stop:0 {radio_accent},
                stop:0.4 {radio_accent},
                stop:0.5 transparent,
                stop:1 transparent);
        }}
    """

    self.single_loto_radio.setStyleSheet(radio_style)
    self.multi_loto_radio.setStyleSheet(radio_style)
    self.no_count_radio.setStyleSheet(radio_style)

    initial_mode = 'multi'
    if hasattr(self, 'export_config'):
        initial_mode = getattr(self.export_config, 'export_mode', 'multi')

    if initial_mode == 'single':
        self.single_loto_radio.setChecked(True)
    elif initial_mode == 'none':
        self.no_count_radio.setChecked(True)
    else:
        self.multi_loto_radio.setChecked(True)

    def _on_single_loto_selected():
        if hasattr(self, '_on_loto_mode_changed'):
            self._on_loto_mode_changed('single')

    def _on_multi_loto_selected():
        if hasattr(self, '_on_loto_mode_changed'):
            self._on_loto_mode_changed('multi')

    def _on_no_count_selected():
        if hasattr(self, '_on_loto_mode_changed'):
            self._on_loto_mode_changed('none')

    self.single_loto_radio.clicked.connect(_on_single_loto_selected)
    self.multi_loto_radio.clicked.connect(_on_multi_loto_selected)
    self.no_count_radio.clicked.connect(_on_no_count_selected)

    loto_mode_layout.addWidget(self.single_loto_radio)
    loto_mode_layout.addWidget(self.multi_loto_radio)
    loto_mode_layout.addWidget(self.no_count_radio)
    loto_mode_layout.addStretch()

    self.loto_label = QLabel("LOTO Modus:")
    self.loto_label.setStyleSheet(label_style)
    self.loto_label.setFont(label_font)
    advanced_options_layout.addWidget(loto_mode_container)

    pdf_import_btn = self.create_wave_button("Sticker aus PDF importieren")
    pdf_import_btn.setIcon(create_symbol_icon("pdf_extractor", size=20))
    pdf_import_btn.setMinimumHeight(52)
    pdf_import_btn.setMinimumWidth(320)
    pdf_import_btn.setMaximumWidth(480)
    pdf_import_btn.clicked.connect(self.import_stickers_from_pdf)
    advanced_options_layout.addWidget(pdf_import_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    input_layout.addWidget(advanced_options_container)

    # Button Container für engeren Abstand
    btn_container = QWidget()
    btn_container.setStyleSheet("QWidget { background-color: transparent; }")
    btn_layout = QVBoxLayout(btn_container)
    btn_layout.setContentsMargins(0, 0, 0, 0)
    btn_layout.setSpacing(8)

    add_btn = self.create_wave_button("Zur Sammlung hinzufügen")
    add_btn.setIcon(create_symbol_icon("plus", size=22))
    add_btn.setMinimumHeight(52)
    add_btn.setMinimumWidth(320)
    add_btn.setMaximumWidth(480)
    add_btn.clicked.connect(lambda: self.add_to_collection(auto_add_count=True))
    btn_layout.addWidget(add_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    card_layout.addWidget(btn_container, alignment=Qt.AlignmentFlag.AlignCenter)

    micro_hint = QLabel("Tipp: Nutze Equipment-Vorlagen, um technische Serien schneller zu erfassen.")
    micro_hint.setStyleSheet(f"color: {tertiary_text}; font-size: 9px;")
    card_layout.addWidget(micro_hint, alignment=Qt.AlignmentFlag.AlignCenter)

    # Erstelle CollapsibleSection für Input Card
    input_card = CollapsibleSection(
        title="Sticker Setup",
        content_widget=input_card_content,
        collapsed_height=40,
        animation_duration=250
    )
    input_card.setMinimumWidth(360)
    input_card.setMaximumWidth(580)
    add_depth_shadow(input_card)

    # Collection Card - Inhalt vorbereiten
    collection_card_content = QWidget()
    collection_card_content.setObjectName("collection_card_content")
    collection_card_content.setStyleSheet("QWidget { background-color: transparent; }")
    # Content soll expandieren
    collection_card_content.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

    collection_card_layout = QVBoxLayout(collection_card_content)
    collection_card_layout.setContentsMargins(12, 0, 12, 8)
    collection_card_layout.setSpacing(8)
    
    # Collection Container kommt ZUERST (nimmt den meisten Platz)
    collection_container = QWidget()
    collection_container.setStyleSheet("QWidget { background-color: transparent; }")
    # Collection Container soll expandieren
    collection_container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
    collection_layout = QHBoxLayout(collection_container)
    collection_layout.setContentsMargins(0, 0, 0, 0)
    collection_layout.setSpacing(12)

    self.collection_list = QListWidget()
    self.collection_list.setMinimumHeight(150)
    # SizePolicy - Liste expandiert vertikal
    self.collection_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    # Performance-Optimierungen für Collection List
    self.collection_list.setUniformItemSizes(True)  # Alle Items gleich groß = schneller
    # Aktiviere Mehrfachauswahl mit Strg+Klick
    self.collection_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
    
    # Frame-Shape entfernen für saubere runde Ecken
    self.collection_list.setFrameShape(QListWidget.Shape.NoFrame)
    
    # Aktiviere Kontextmenü
    self.collection_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    self.collection_list.customContextMenuRequested.connect(self._show_collection_context_menu)
    
    # Light Mode Styling für Collection List
    if False:
        collection_list_style = """
            QListWidget {
                background-color: rgba(20, 23, 31, 0.35);
                color: #f5f7fb;
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 16px;
                padding: 12px;
                outline: none;
            }
            QListWidget::item {
                padding: 6px;
                margin: 2px 0px;
                border-radius: 8px;
            }
            QListWidget::item:selected {
                background-color: rgba(43, 107, 255, 0.55);
                color: #ffffff;
            }
            QListWidget::item:hover {
                background-color: rgba(255, 255, 255, 0.08);
            }
        """
    else:
        collection_list_style = """
            QListWidget {
                background-color: transparent;
                color: #0f172a;
                border: none;
                padding: 8px;
                outline: none;
            }
            QListWidget::item {
                padding: 6px;
                margin: 2px 0px;
                border-radius: 8px;
            }
            QListWidget::item:selected {
                background-color: rgba(30, 144, 255, 0.25);
                color: #0f172a;
            }
            QListWidget::item:hover {
                background-color: rgba(15, 23, 42, 0.06);
            }
        """
    self.collection_list.setStyleSheet(collection_list_style)
    
    # Scrollbars anpassen: Horizontal aus, Vertikal styled
    self.collection_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    
    v_scrollbar = self.collection_list.verticalScrollBar()
    if v_scrollbar:
        v_scrollbar.setStyleSheet("""
            QScrollBar:vertical {
                border: none;
                background: rgba(0,0,0,0.05);
                width: 8px;
                margin: 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(0,0,0,0.2);
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

    # Click-Handler: Angewählter Sticker in Vorschau anzeigen
    # Debounce timer für Collection Item Selection - verzögert die Anzeige um 100ms
    self.collection_selection_timer = QTimer(self)
    self.collection_selection_timer.setSingleShot(True)
    self.collection_selection_timer.timeout.connect(self._on_collection_item_selected_debounced)
    self.collection_list.itemSelectionChanged.connect(self._on_collection_item_selected_trigger)
    self._collection_preview_delay_ms = 150
    self._is_collection_scrolling = False
    self._pending_collection_preview_row = None
    self.collection_scroll_cooldown_timer = QTimer(self)
    self.collection_scroll_cooldown_timer.setSingleShot(True)
    self.collection_scroll_cooldown_timer.timeout.connect(self._on_collection_scroll_finished)
    scrollbar = self.collection_list.verticalScrollBar()
    if scrollbar is not None:
        scrollbar.valueChanged.connect(self._on_collection_scroll_value_changed)
    
    # Container mit runden Ecken für die Liste
    from PyQt6.QtWidgets import QFrame
    list_container = QFrame()
    list_container.setStyleSheet("""
        QFrame {
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 16px;
        }
    """)
    list_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    list_container_layout = QVBoxLayout(list_container)
    list_container_layout.setContentsMargins(0, 0, 0, 0)
    list_container_layout.addWidget(self.collection_list)
    
    collection_layout.addWidget(list_container)

    # Ablage-Verwaltung Buttons (Vertikal rechts)
    button_container = QWidget()
    button_container.setFixedWidth(72)
    button_container.setStyleSheet("""
        QWidget {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #e8edf5, stop:1 #dce3ed);
            border-radius: 14px;
        }
    """)
    coll_btn_layout = QVBoxLayout(button_container)
    coll_btn_layout.setContentsMargins(8, 10, 8, 10)
    coll_btn_layout.setSpacing(8)
    coll_btn_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

    # Helper für Keyboard-Style Buttons mit Phosphor Icons (kbd.css Style)
    def create_keyboard_btn(icon_name, tooltip, slot, color="#64748b"):
        btn = QPushButton()
        btn.setFixedSize(56, 56)
        btn.setToolTip(tooltip)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setIcon(qta.icon(icon_name, color=color))
        btn.setIconSize(QSize(26, 26))

        btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 #fcfcfd, stop:0.6 #f0f2f5, stop:1 #e8ebef);
                border: 1px solid #b8bcc4;
                border-radius: 7px;
                border-bottom: 3px solid #a0a4ac;
                padding-bottom: 2px;
                /* kbd.css inset shadow simulation */
                border-top: 1px solid #d4d7dd;
                border-left: 1px solid #c8ccd4;
                border-right: 1px solid #c0c4cc;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 #ffffff, stop:0.6 #f5f7fa, stop:1 #eef0f4);
                border-bottom: 3px solid #9098a4;
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 #e8ebef, stop:0.4 #eceef2, stop:1 #f0f2f5);
                border-bottom: 1px solid #b8bcc4;
                border-top: 2px solid #a0a4ac;
                padding-top: 3px;
                padding-bottom: 0px;
                margin-top: 2px;
            }}
        """)
        btn.clicked.connect(slot)
        return btn

    # Navigation Keys (Phosphor Icons)
    up_btn = create_keyboard_btn("ph.arrow-up-bold", "Nach oben", self.move_item_up, "#334155")
    coll_btn_layout.addWidget(up_btn)
    
    down_btn = create_keyboard_btn("ph.arrow-down-bold", "Nach unten", self.move_item_down, "#334155")
    coll_btn_layout.addWidget(down_btn)
    
    # Delete Key
    delete_btn = create_keyboard_btn("ph.x-bold", "Löschen", self.delete_selected_items, "#334155")
    coll_btn_layout.addWidget(delete_btn)
    
    coll_btn_layout.addSpacing(4)

    # Action Keys
    sort_btn = create_keyboard_btn("ph.arrows-down-up-bold", "Sortieren", self.sort_collection_by_energy_id, "#334155")
    coll_btn_layout.addWidget(sort_btn)

    clear_btn = create_keyboard_btn("ph.trash-bold", "Leeren", self.clear_collection, "#334155")
    coll_btn_layout.addWidget(clear_btn)
    
    coll_btn_layout.addStretch()
    
    collection_layout.addWidget(button_container, alignment=Qt.AlignmentFlag.AlignTop)
    
    # Collection Container nimmt den meisten Platz ein (stretch=1)
    collection_card_layout.addWidget(collection_container, 1)
    
    # Button kommt VOR der Liste (oben)
    import_equipment_btn = self.create_wave_button("Ablage in Equipment übernehmen")
    import_equipment_btn.setIcon(create_symbol_icon("plus", size=20))
    import_equipment_btn.setMinimumHeight(52)
    import_equipment_btn.setFixedWidth(action_btn_width)
    import_equipment_btn.clicked.connect(self.import_collection_to_equipment_manager)
    collection_card_layout.insertWidget(0, import_equipment_btn, alignment=Qt.AlignmentFlag.AlignCenter)
    
    # Erstelle CollapsibleSection für Collection Card
    collection_card = CollapsibleSection(
        title="Sticker-Sammlung",
        content_widget=collection_card_content,
        collapsed_height=40,
        animation_duration=250
    )
    collection_card.setMinimumWidth(360)
    collection_card.setMaximumWidth(580)
    add_depth_shadow(collection_card)
    
    # Linker Bereich mit ScrollArea
    left_area = QWidget()
    left_area.setStyleSheet("QWidget { background-color: transparent; }")
    left_area_layout = QVBoxLayout(left_area)
    left_area_layout.setContentsMargins(0, 0, 0, 0)
    left_area_layout.setSpacing(18)
    left_area_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    left_area_layout.addWidget(input_card)
    left_area_layout.addWidget(collection_card, 1)  # Stretch factor 1 - nimmt verfügbaren Platz
    
    left_scroll = QScrollArea()
    left_scroll.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")
    left_scroll.setMinimumWidth(380)
    left_scroll.setMaximumWidth(640)
    left_scroll.setAlignment(Qt.AlignmentFlag.AlignTop)
    left_scroll.setWidget(left_area)
    left_scroll.setWidgetResizable(True)
    left_scroll.setFrameShape(QFrame.Shape.NoFrame)
    left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    left_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    
    viewport = left_scroll.viewport()
    if viewport:
        viewport.setStyleSheet("background-color: transparent;")
    
    layout.addWidget(left_scroll, stretch=2)

    # Rechter Bereich für Preview
    right_widget = QWidget()
    right_widget.setStyleSheet("background-color: transparent;")
    right_layout = QVBoxLayout(right_widget)
    right_layout.setContentsMargins(0, 0, 0, 0)
    right_layout.setSpacing(24)

    preview_card = QWidget()
    preview_card.setObjectName("preview_card")
    preview_card.setStyleSheet("""
        QWidget#preview_card {
            background-color: #ffffff;
            border-radius: 20px;
            border: none;
        }
        QWidget#preview_shell {
            background-color: #f6f8fb;
            border-radius: 16px;
            border: 1px dashed #e3e8f4;
        }
    """)
    add_depth_shadow(preview_card)

    preview_layout = QVBoxLayout(preview_card)
    preview_layout.setContentsMargins(22, 20, 22, 20)
    preview_layout.setSpacing(18)

    preview_title = QLabel("Live Sticker Vorschau")
    preview_title.setFont(heading_font)
    preview_title.setStyleSheet(f"color: {primary_text}; background-color: transparent;")
    preview_layout.addWidget(preview_title)

    preview_caption = QLabel("Kontrastreiche Darstellung mit großzügigem Weißraum – ideal für technische Reviews.")
    preview_caption.setFont(subheading_font)
    preview_caption.setStyleSheet(f"color: {secondary_text}; background-color: transparent;")
    preview_caption.setWordWrap(True)
    preview_layout.addWidget(preview_caption)

    preview_shell = QWidget()
    preview_shell.setObjectName("preview_shell")
    shell_layout = QVBoxLayout(preview_shell)
    shell_layout.setContentsMargins(16, 32, 16, 32)
    shell_layout.setSpacing(12)

    self.preview_label = ShimmerLabel("Vorschau wird geladen...")
    self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    self.preview_label.setStyleSheet("border: none; background: transparent;")
    shell_layout.addWidget(self.preview_label, stretch=1)

    preview_layout.addWidget(preview_shell, stretch=1)

    zoom_container = QWidget()
    zoom_container.setStyleSheet("QWidget { background-color: transparent; }")
    zoom_layout = QHBoxLayout(zoom_container)
    zoom_layout.setContentsMargins(0, 0, 0, 0)
    zoom_layout.setSpacing(12)
    
    zoom_label = QLabel("Zoom")
    zoom_label.setFont(label_font)
    zoom_label.setStyleSheet(f"color: {primary_text};")
    zoom_layout.addWidget(zoom_label)

    self.scale_slider = QSlider(Qt.Orientation.Horizontal)
    self.scale_slider.setRange(20, 400)
    self.scale_slider.setValue(int(self.sticker_config.preview_scale * 200))
    self.scale_slider.setStyleSheet("""
        QSlider::groove:horizontal {
            background: #e5e7eb;
            height: 6px;
            border-radius: 3px;
        }
        QSlider::handle:horizontal {
            background: #2563eb;
            width: 20px;
            height: 20px;
            margin: -7px 0;
            border-radius: 10px;
        }
        QSlider::handle:horizontal:hover {
            background: #1d4ed8;
        }
    """)
    self.scale_slider.valueChanged.connect(self._safe_update_sticker_scale_from_dial)
    zoom_layout.addWidget(self.scale_slider)

    self.scale_value_label = QLabel(f"{self.sticker_config.preview_scale:.1f}")
    self.scale_value_label.setFixedWidth(44)
    self.scale_value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    self.scale_value_label.setStyleSheet(f"font-weight: bold; color: {primary_text};")
    zoom_layout.addWidget(self.scale_value_label)

    preview_layout.addWidget(zoom_container)

    right_layout.addWidget(preview_card, stretch=1)
    right_layout.addStretch()
    right_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    layout.addWidget(right_widget, stretch=2)

    # Vorschau-Update Timer (Debounce)
    self.preview_update_delay_ms = 180
    self.preview_update_timer = QTimer(self)
    self.preview_update_timer.setSingleShot(True)
    self.preview_update_timer.timeout.connect(self.update_sticker_preview)

    # Live-Update für Vorschau via Debounce
    self.energy_entry.textChanged.connect(self._on_preview_text_changed)
    self.equipment_entry.textChanged.connect(self._on_preview_text_changed)
    self.description_entry.textChanged.connect(self._on_preview_text_changed)
    
    self.tab_widget.addTab(sticker_widget, "🎫 LOTO Sticker")
    
    # Initial Welcome-Sticker Update mit Verzögerung (damit Layout vollständig gerendert ist)
    QTimer.singleShot(500, self._show_startup_welcome_sticker)


def build_equipment_tab(self):
    """Equipment-Verwaltungs-Tab (modernes Layout analog Generator)"""
    equipment_widget = QWidget()
    
    content_layout = QHBoxLayout(equipment_widget)
    content_layout.setSpacing(20)
    content_layout.setContentsMargins(16, 16, 16, 16)

    if self.equipment_manager is None:
        error_label = QLabel("Equipment Management nicht verfügbar aufgrund eines Fehlers beim Laden.")
        error_label.setStyleSheet("color: red; font-weight: bold; padding: 20px;")
        content_layout.addWidget(error_label)
        self.tab_widget.addTab(equipment_widget, "Equipment")
        return

    # Equipment Tree (Links)
    tree_card = QWidget()
    tree_card.setObjectName("tree_card")
    tree_card.setStyleSheet("""
        QWidget#tree_card {
            background-color: #ffffff;
            border-radius: 20px;
            border: none;
        }
    """)
    tree_card_layout = QVBoxLayout(tree_card)
    tree_card_layout.setContentsMargins(18, 16, 18, 16)
    tree_card_layout.setSpacing(14)

    heading_font = QFont("Bahnschrift", 13)
    heading_font.setWeight(QFont.Weight.Bold)
    subheading_font = QFont("Bahnschrift", 11)
    primary_text = "#1f2a37"
    secondary_text = "#5f6c80"

    tree_title = QLabel("Equipment-Verwaltung")
    tree_title.setFont(heading_font)
    tree_title.setStyleSheet(f"color: {primary_text}; letter-spacing: 0.6px; background-color: transparent;")
    tree_card_layout.addWidget(tree_title)

    tree_subtitle = QLabel("Standorte, Systeme und Betriebsmittel organisieren")
    tree_subtitle.setFont(subheading_font)
    tree_subtitle.setStyleSheet(f"color: {secondary_text}; background-color: transparent;")
    tree_subtitle.setWordWrap(True)
    tree_card_layout.addWidget(tree_subtitle)

    tree_card_layout.addSpacing(6)

    self.equipment_tree = QTreeWidget()
    self.equipment_tree.setHeaderHidden(True)
    self.equipment_tree.setMinimumHeight(450)
    self.equipment_tree.setAlternatingRowColors(True)
    self.equipment_tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
    self.equipment_tree.setStyleSheet(
        "QTreeWidget{border:1px solid #ddd; border-radius:4px; background:white;}"
        "QTreeWidget::item{padding:6px; font-size:11pt;}"
        "QTreeWidget::item:selected{background:#e0e0e0; color:black;}"
        "QTreeWidget::item:hover{background:#f5f5f5;}"
    )
    font = QFont("Bahnschrift", 11)
    self.equipment_tree.setFont(font)

    tree_card_layout.addWidget(self.equipment_tree)
    add_depth_shadow(tree_card)
    content_layout.addWidget(tree_card, stretch=1)
    
    # Aktionsbereich (Rechts)
    actions_card = QWidget()
    actions_card.setObjectName("actions_card")
    actions_card.setStyleSheet("""
        QWidget#actions_card {
            background-color: #ffffff;
            border-radius: 20px;
            border: none;
        }
    """)
    actions_card_layout = QVBoxLayout(actions_card)
    actions_card_layout.setContentsMargins(18, 16, 18, 16)
    actions_card_layout.setSpacing(14)

    actions_title = QLabel("Aktionen")
    actions_title.setFont(heading_font)
    actions_title.setStyleSheet(f"color: {primary_text}; letter-spacing: 0.6px; background-color: transparent;")
    actions_card_layout.addWidget(actions_title)

    actions_subtitle = QLabel("Equipment hinzufügen, bearbeiten oder löschen")
    actions_subtitle.setFont(subheading_font)
    actions_subtitle.setStyleSheet(f"color: {secondary_text}; background-color: transparent;")
    actions_subtitle.setWordWrap(True)
    actions_card_layout.addWidget(actions_subtitle)

    actions_card_layout.addSpacing(6)

    add_depth_shadow(actions_card)

    actions_layout = QVBoxLayout()
    actions_layout.setSpacing(12)
    
    # Buttons
    button_frame = QWidget()
    button_frame.setStyleSheet("QWidget { background-color: transparent; }")
    button_main_layout = QVBoxLayout(button_frame)
    button_main_layout.setSpacing(20)
    button_main_layout.setContentsMargins(0, 0, 0, 0)
    
    # Erste Gruppe: Hinzufügen (Vertikal)
    add_button_layout = QVBoxLayout()
    add_button_layout.setSpacing(15)
    add_button_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
    
    self.batch_equipment_btn = _create_glass_button(self, "Batch")
    self.batch_equipment_btn.setToolTip("Mehrere Equipments auf einmal hinzufügen")
    self.batch_equipment_btn.setFixedWidth(150)
    add_button_layout.addWidget(self.batch_equipment_btn)
    
    button_main_layout.addLayout(add_button_layout)
    
    # Trenner
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFrameShadow(QFrame.Shadow.Sunken)
    line.setStyleSheet("background-color: #ddd;")
    button_main_layout.addWidget(line)
    
    # Zweite Gruppe: Datei-Aktionen (Vertikal)
    action_button_layout = QVBoxLayout()
    action_button_layout.setSpacing(15)
    action_button_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

    self.import_equipment_btn = _create_glass_button(self, "Excel-Import")
    self.import_equipment_btn.setToolTip("Equipment aus Excel importieren")
    self.import_equipment_btn.setFixedWidth(150)
    self.import_equipment_btn.clicked.connect(self._import_equipment_from_excel)
    action_button_layout.addWidget(self.import_equipment_btn)

    self.save_equipment_btn = _create_glass_button(self, "Speichern")
    self.save_equipment_btn.setToolTip("Equipment speichern")
    self.save_equipment_btn.setFixedWidth(150)
    action_button_layout.addWidget(self.save_equipment_btn)
    
    button_main_layout.addLayout(action_button_layout)
    
    # Trenner für Export/Import
    line2 = QFrame()
    line2.setFrameShape(QFrame.Shape.HLine)
    line2.setFrameShadow(QFrame.Shadow.Sunken)
    line2.setStyleSheet("background-color: #ddd;")
    button_main_layout.addWidget(line2)
    
    # Dritte Gruppe: Datenbank Export/Import
    db_button_layout = QVBoxLayout()
    db_button_layout.setSpacing(15)
    db_button_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
    
    self.export_db_btn = _create_glass_button(self, "DB Export")
    self.export_db_btn.setIcon(qta.icon('ph.export', color='#1f2937'))
    self.export_db_btn.setToolTip("Equipment-Datenbank als JSON exportieren")
    self.export_db_btn.setFixedWidth(150)
    self.export_db_btn.clicked.connect(self._export_equipment_database)
    db_button_layout.addWidget(self.export_db_btn)
    
    self.import_db_btn = _create_glass_button(self, "DB Import")
    self.import_db_btn.setIcon(qta.icon('ph.download-simple', color='#1f2937'))
    self.import_db_btn.setToolTip("Equipment-Datenbank aus JSON importieren")
    self.import_db_btn.setFixedWidth(150)
    self.import_db_btn.clicked.connect(self._import_equipment_database)
    db_button_layout.addWidget(self.import_db_btn)
    
    button_main_layout.addLayout(db_button_layout)
    button_main_layout.addStretch()
    
    actions_layout.addWidget(button_frame)
    
    # Hilfetext
    help_label = QLabel("Tipp: Rechtsklick für Optionen, Doppelklick zum Bearbeiten")
    
    # Calculate text color
    custom_colors = getattr(self.theme_config, 'custom_colors', {}) if hasattr(self, 'theme_config') else {}
    element_bg = custom_colors.get('element_bg')
    help_text_color = "#666"
    if element_bg:
        help_text_color = get_contrasting_text_color(element_bg)
        # Make it slightly transparent/dimmer if it's white/black to keep "help text" look
        if help_text_color == "#ffffff":
             help_text_color = "rgba(255, 255, 255, 0.7)"
        else:
             help_text_color = "rgba(0, 0, 0, 0.6)"

    help_label.setStyleSheet(f"""
        font-size: 10pt; 
        color: {help_text_color}; 
        font-style: italic;
        padding: 8px 4px 4px 4px;
    """)
    help_label.setWordWrap(True)
    actions_layout.addWidget(help_label)
    
    actions_card_layout.addLayout(actions_layout)
    content_layout.addWidget(actions_card)

    self.tab_widget.addTab(equipment_widget, "Equipment")


def build_export_tab(self):
    """Export-Einstellungen-Tab"""
    export_widget = QWidget()
    
    # Haupt-Layout: Horizontal geteilt (Links: Einstellungen, Rechts: Export)
    layout = QHBoxLayout(export_widget)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(20)

    heading_font = QFont("Bahnschrift", 13)
    heading_font.setWeight(QFont.Weight.Bold)
    subheading_font = QFont("Bahnschrift", 11)
    primary_text = "#1f2a37"
    secondary_text = "#5f6c80"

    # Linke Karte: Einstellungen (mit Scroll-Bereich)
    left_card_outer = QWidget()
    left_card_outer.setObjectName("export_settings_card_outer")
    left_card_outer.setStyleSheet("""
        QWidget#export_settings_card_outer {
            background-color: #ffffff;
            border-radius: 20px;
            border: none;
        }
    """)
    left_card_outer_layout = QVBoxLayout(left_card_outer)
    left_card_outer_layout.setContentsMargins(0, 0, 0, 0)
    left_card_outer_layout.setSpacing(0)
    
    # Scroll-Bereich für die Einstellungen
    scroll_area = QScrollArea()
    scroll_area.setWidgetResizable(True)
    scroll_area.setFrameShape(QFrame.Shape.NoFrame)
    scroll_area.setStyleSheet("""
        QScrollArea {
            background-color: transparent;
            border: none;
        }
        QScrollBar:vertical {
            background-color: #f0f0f0;
            width: 10px;
            border-radius: 5px;
        }
        QScrollBar::handle:vertical {
            background-color: #c0c0c0;
            border-radius: 5px;
            min-height: 20px;
        }
        QScrollBar::handle:vertical:hover {
            background-color: #a0a0a0;
        }
    """)
    
    left_card = QWidget()
    left_card.setStyleSheet("QWidget { background-color: transparent; }")
    left_card_layout = QVBoxLayout(left_card)
    left_card_layout.setContentsMargins(28, 20, 28, 28)
    left_card_layout.setSpacing(0)
    
    scroll_area.setWidget(left_card)
    left_card_outer_layout.addWidget(scroll_area)

    add_depth_shadow(left_card_outer)

    settings_title = QLabel("Export-Einstellungen")
    title_font = QFont("Bahnschrift", 15)
    title_font.setWeight(QFont.Weight.Bold)
    settings_title.setFont(title_font)
    settings_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
    settings_title.setStyleSheet(f"color: {primary_text}; letter-spacing: 0.6px; background-color: transparent;")
    left_card_layout.addWidget(settings_title)
    
    left_card_layout.addSpacing(20)

    settings_content = QVBoxLayout()
    settings_content.setSpacing(20)

    # Papierformat Section
    format_layout = QGridLayout()
    format_layout.setContentsMargins(0, 0, 0, 0)
    format_layout.setVerticalSpacing(18)
    format_layout.setHorizontalSpacing(20)
    format_layout.setColumnStretch(0, 0)
    format_layout.setColumnStretch(1, 1)
    
    # Feste Label-Breite für Ausrichtung
    LABEL_WIDTH = 120

    # Papierformat Presets
    self.format_combo = ModernComboBox(dark_mode=False)
    # Angleichen an neue Formular-Breite/Höhe aus den Settings-Dialogen
    self.format_combo.setMinimumWidth(180)
    self.format_combo.setMaximumWidth(300) # Begrenzte Breite
    self.format_combo.setMinimumHeight(40)
    self.format_combo.addItems([
        "DIN A4 (210 x 297 mm)",
        "DIN A3 (297 x 420 mm)",
        "Versandetikett (100 x 150 mm)",
        "Rollenmodus"
    ])
    
    # Initialisiere Format-Combo basierend auf gespeicherten Werten
    if self.export_config.roll_mode:
        self.format_combo.setCurrentText("Rollenmodus")
    else:
        # Versuche passendes Preset zu finden
        presets = {
            "DIN A4 (210 x 297 mm)": (210, 297),
            "DIN A3 (297 x 420 mm)": (297, 420),
            "Versandetikett (100 x 150 mm)": (100, 150),
        }
        found = False
        for preset_name, (p_w, p_h) in presets.items():
            if (abs(self.export_config.sheet_width_mm - p_w) < 0.1 and 
                abs(self.export_config.sheet_height_mm - p_h) < 0.1):
                self.format_combo.setCurrentText(preset_name)
                found = True
                break
        if not found:
            # Wenn kein Preset passt, aber roll_mode ist False, dann setze auf A4
            self.format_combo.setCurrentText("DIN A4 (210 x 297 mm)")
    
    self.format_combo.currentTextChanged.connect(self._on_format_preset_changed)
    
    # Row 0: Preset
    # Label-Style für dunkle, gut lesbare Schrift
    accent_label_style = "color: #5f6c80; font-weight: 600; font-size: 11pt; background-color: transparent;"

    label_preset = QLabel("Format-Preset:")
    label_preset.setStyleSheet(accent_label_style)
    label_preset.setFixedWidth(LABEL_WIDTH)
    format_layout.addWidget(label_preset, 0, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    format_layout.addWidget(self.format_combo, 0, 1)

    # Helper für SpinBox-Container - verwendet Form-Helper Pattern
    def create_spinbox(value, min_val, max_val, step, suffix, callback, is_integer=False):
        from ui.form_helpers import SPINBOX_INPUT_WIDTH, UNIT_LABEL_WIDTH
        
        container = QWidget()
        container.setStyleSheet("QWidget { background-color: transparent; }")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        # Spinbox ohne Suffix
        if is_integer:
            spin = StyledSpinBox()
            spin.setRange(int(min_val), int(max_val))
            spin.setValue(int(value))
        else:
            spin = StyledDoubleSpinBox()
            spin.setRange(min_val, max_val)
            spin.setValue(value)
            spin.setSingleStep(step)
        
        spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.UpDownArrows)
        spin.setFixedWidth(SPINBOX_INPUT_WIDTH)
        
        # Signal für Änderungen
        def on_spin_change(val):
            callback()
        
        spin.valueChanged.connect(on_spin_change)
        
        layout.addWidget(spin, 0, Qt.AlignmentFlag.AlignVCenter)
        
        # Unit Label wenn vorhanden
        if suffix:
            unit_label = QLabel(suffix.strip())
            unit_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            unit_label.setFixedWidth(UNIT_LABEL_WIDTH)
            unit_label.setStyleSheet("color: #7a8597; font-size: 11pt; font-weight: 500;")
            layout.addWidget(unit_label, 0, Qt.AlignmentFlag.AlignVCenter)
        
        layout.addStretch()
        
        return container, spin

    # Breite Eingabefeld (nur für Rollenmodus sichtbar)
    self.width_container, self.width_spin = create_spinbox(
        self.export_config.sheet_width_mm, 100, 500, 1.0, "mm", self._on_sheet_size_changed
    )
    self.width_label = QLabel("Breite:")
    self.width_label.setStyleSheet(accent_label_style)
    self.width_label.setFixedWidth(LABEL_WIDTH)
    format_layout.addWidget(self.width_label, 1, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    format_layout.addWidget(self.width_container, 1, 1)

    # Höhe Eingabefeld (versteckt im Rollenmodus wegen Auto-Höhe)
    self.height_container, self.height_spin = create_spinbox(
        self.export_config.sheet_height_mm, 100, 500, 1.0, "mm", self._on_sheet_size_changed
    )
    self.height_label = QLabel("Höhe:")
    self.height_label.setStyleSheet(accent_label_style)
    self.height_label.setFixedWidth(LABEL_WIDTH)
    format_layout.addWidget(self.height_label, 2, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    format_layout.addWidget(self.height_container, 2, 1)

    # Rollen-Breite (nur sichtbar wenn Rollen-Modus aktiv)
    self.roll_width_container, self.roll_width_spin = create_spinbox(
        self.export_config.roll_width_mm, 50, 500, 1.0, "mm", self._on_roll_width_changed
    )
    self.roll_width_label = QLabel("Rollenbreite:")
    self.roll_width_label.setStyleSheet(accent_label_style)
    self.roll_width_label.setFixedWidth(LABEL_WIDTH)
    format_layout.addWidget(self.roll_width_label, 3, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    format_layout.addWidget(self.roll_width_container, 3, 1)
    
    # Zeige Rollen-Breite nur wenn Rollen-Modus aktiv
    self._update_roll_mode_visibility()

    settings_content.addLayout(format_layout)
    settings_content.addSpacing(16)

    # Export-Einstellungen Section
    settings_layout = QGridLayout()
    settings_layout.setContentsMargins(0, 0, 0, 0)
    settings_layout.setVerticalSpacing(18)
    settings_layout.setHorizontalSpacing(20)
    settings_layout.setColumnStretch(0, 0)
    settings_layout.setColumnStretch(1, 1)

    margin_container, self.margin_spin = create_spinbox(
        self.export_config.margin_mm, 0, 50, 1.0, "mm", self._on_export_settings_changed
    )
    label_margin = QLabel("Rand:")
    label_margin.setStyleSheet(accent_label_style)
    label_margin.setFixedWidth(LABEL_WIDTH)
    settings_layout.addWidget(label_margin, 0, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    settings_layout.addWidget(margin_container, 0, 1)
 
    gap_container, self.gap_spin = create_spinbox(
        self.export_config.gap_mm, 0, 20, 1.0, "mm", self._on_export_settings_changed
    )
    label_gap = QLabel("Abstand:")
    label_gap.setStyleSheet(accent_label_style)
    label_gap.setFixedWidth(LABEL_WIDTH)
    settings_layout.addWidget(label_gap, 1, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    settings_layout.addWidget(gap_container, 1, 1)

    # Rotation-Einstellung entfällt: wir erzwingen automatisch immer 'auto'
    self.export_config.sticker_rotate_mode = 'auto'
    self.export_config.sticker_rotation_locked = None
    self.config_manager.save_export(self.export_config)

    settings_content.addLayout(settings_layout)
    
    # Visualisierung der Maße hinzufügen
    settings_content.addSpacing(20)
    from ui.dimensions_widget import DimensionsVisualizationWidget
    self.dimensions_widget = DimensionsVisualizationWidget()
    self.dimensions_widget.set_dimensions(
        self.export_config.sheet_width_mm,
        self.export_config.sheet_height_mm,
        self.export_config.margin_mm,
        self.export_config.gap_mm,
        self.export_config.roll_mode,
        self.sticker_config.width_mm,
        self.sticker_config.height_mm,
        self.export_config.roll_width_mm
    )
    settings_content.addWidget(self.dimensions_widget)
    
    left_card_layout.addLayout(settings_content)
    left_card_layout.addStretch()

    # Rechte Karte: Export-Aktionen
    right_card = QWidget()
    right_card.setObjectName("export_actions_card")
    right_card.setStyleSheet("""
        QWidget#export_actions_card {
            background-color: #ffffff;
            border-radius: 20px;
            border: none;
        }
    """)
    right_card_layout = QVBoxLayout(right_card)
    right_card_layout.setContentsMargins(18, 16, 18, 16)
    right_card_layout.setSpacing(14)

    add_depth_shadow(right_card)

    actions_title = QLabel("Export-Aktionen")
    title_font = QFont("Bahnschrift", 15)
    title_font.setWeight(QFont.Weight.Bold)
    actions_title.setFont(title_font)
    actions_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
    actions_title.setStyleSheet(f"color: {primary_text}; letter-spacing: 0.6px; background-color: transparent;")
    right_card_layout.addWidget(actions_title)

    actions_subtitle = QLabel("Sticker als PDF oder einzelne Bilddateien exportieren")
    actions_subtitle.setFont(subheading_font)
    actions_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
    actions_subtitle.setStyleSheet(f"color: {secondary_text}; background-color: transparent;")
    actions_subtitle.setWordWrap(True)
    right_card_layout.addWidget(actions_subtitle)

    right_card_layout.addSpacing(6)

    # Export-Buttons mit Zentrierung
    buttons_container = QWidget()
    buttons_container.setStyleSheet("QWidget { background-color: transparent; }")
    buttons_layout = QVBoxLayout(buttons_container)
    buttons_layout.setContentsMargins(0, 0, 0, 0)
    buttons_layout.setSpacing(12)
    buttons_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

    pdf_btn = _create_glass_button(self, "Als PDF exportieren")
    pdf_btn.setMinimumWidth(300)
    pdf_btn.setMaximumWidth(300)
    pdf_btn.setMinimumHeight(36)
    pdf_btn.setMaximumHeight(36)
    pdf_btn.clicked.connect(self.export_pdf)
    buttons_layout.addWidget(pdf_btn)

    zip_btn = _create_glass_button(self, "Als ZIP exportieren")
    zip_btn.setMinimumWidth(300)
    zip_btn.setMaximumWidth(300)
    zip_btn.setMinimumHeight(36)
    zip_btn.setMaximumHeight(36)
    zip_btn.clicked.connect(lambda: print("ZIP Export noch nicht implementiert"))
    buttons_layout.addWidget(zip_btn)

    right_card_layout.addWidget(buttons_container)

    right_card_layout.addStretch()

    # Karten zum Hauptlayout hinzufügen
    layout.addWidget(left_card_outer, stretch=3)
    layout.addWidget(right_card, stretch=2)

    self.tab_widget.addTab(export_widget, "Export")


def build_pdf_import_tab(self):
    """PDF Import Tab - Placeholder that allows importing."""
    import_widget = QWidget()
    layout = QVBoxLayout(import_widget)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.setSpacing(30)
    
    # Icon
    icon_label = QLabel()
    icon_label.setPixmap(create_symbol_icon("pdf_extractor", size=128).pixmap(128, 128))
    icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(icon_label)
    
    # Title
    title = QLabel("Sticker aus PDF importieren")
    title.setStyleSheet("font-size: 24px; font-weight: bold; color: #333;")
    title.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(title)
    
    # Description
    desc = QLabel(
        "Laden Sie eine PDF-Datei hoch, um automatisch Sticker-Daten zu extrahieren.\n"
        "Das System erkennt Energie-IDs, Equipment-Namen und Beschreibungen."
    )
    desc.setStyleSheet("font-size: 14px; color: #666;")
    desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
    desc.setWordWrap(True)
    layout.addWidget(desc)
    
    # Button
    btn = _create_glass_button(self, "PDF auswählen und importieren")
    btn.setFixedSize(300, 60)
    btn.clicked.connect(self.import_stickers_from_pdf)
    layout.addWidget(btn, 0, Qt.AlignmentFlag.AlignCenter)
    
    layout.addStretch()
    
    self.tab_widget.addTab(import_widget, "PDF Import")
