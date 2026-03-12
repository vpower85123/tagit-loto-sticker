"""Export-Tab UI Builder.

Enthält:
- build_export_tab: Export-Einstellungen-Tab
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QAbstractSpinBox,
    QGridLayout, QScrollArea, QFrame
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

from ui.theme import Theme, get_theme_colors
from ui.components import ModernComboBox
from ui.spinboxes import StyledDoubleSpinBox, StyledSpinBox
from ui.builder_utils import add_depth_shadow, _create_glass_button


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
    self.format_combo.setMinimumWidth(180)
    self.format_combo.setMaximumWidth(300)
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
            self.format_combo.setCurrentText("DIN A4 (210 x 297 mm)")
    
    self.format_combo.currentTextChanged.connect(self._on_format_preset_changed)
    
    # Label-Style für dunkle, gut lesbare Schrift
    accent_label_style = "color: #5f6c80; font-weight: 600; font-size: 11pt; background-color: transparent;"

    label_preset = QLabel("Format-Preset:")
    label_preset.setStyleSheet(accent_label_style)
    label_preset.setFixedWidth(LABEL_WIDTH)
    format_layout.addWidget(label_preset, 0, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    format_layout.addWidget(self.format_combo, 0, 1)

    # Helper für SpinBox-Container
    def create_spinbox(value, min_val, max_val, step, suffix, callback, is_integer=False):
        from ui.form_helpers import SPINBOX_INPUT_WIDTH, UNIT_LABEL_WIDTH
        
        container = QWidget()
        container.setStyleSheet("QWidget { background-color: transparent; }")
        sb_layout = QHBoxLayout(container)
        sb_layout.setContentsMargins(0, 0, 0, 0)
        sb_layout.setSpacing(12)
        sb_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
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
        
        def on_spin_change(val):
            callback()
        
        spin.valueChanged.connect(on_spin_change)
        
        sb_layout.addWidget(spin, 0, Qt.AlignmentFlag.AlignVCenter)
        
        if suffix:
            unit_label = QLabel(suffix.strip())
            unit_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            unit_label.setFixedWidth(UNIT_LABEL_WIDTH)
            unit_label.setStyleSheet("color: #7a8597; font-size: 11pt; font-weight: 500;")
            sb_layout.addWidget(unit_label, 0, Qt.AlignmentFlag.AlignVCenter)
        
        sb_layout.addStretch()
        
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
    zip_btn.clicked.connect(lambda: None)  # TODO: ZIP Export implementieren
    buttons_layout.addWidget(zip_btn)

    right_card_layout.addWidget(buttons_container)

    right_card_layout.addStretch()

    # Karten zum Hauptlayout hinzufügen
    layout.addWidget(left_card_outer, stretch=3)
    layout.addWidget(right_card, stretch=2)

    self.tab_widget.addTab(export_widget, "Export")
