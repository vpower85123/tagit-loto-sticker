"""Sticker-Tab und Start-Tab UI Builder.

Enthält:
- build_start_tab: Überblicks-Tab mit Navigations-Buttons
- build_sticker_tab: Sticker-Erstellungs-Tab (Hauptfunktionalität)
- build_pdf_import_tab: PDF Import Tab
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QComboBox,
    QListWidget, QRadioButton, QButtonGroup,
    QSizePolicy, QSlider, QFrame,
    QScrollArea
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt, QTimer, QSize
import qtawesome as qta

from ui.theme import (
    create_input_stylesheet, Theme,
    get_contrasting_text_color, get_theme_colors
)
from ui.glass_button import GlassGlowButton
from ui.components import SmoothDial, ModernComboBox, ShimmerLabel
from ui.collapsible_section import CollapsibleSection
from ui.builder_utils import add_depth_shadow, create_symbol_icon, _create_glass_button


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
