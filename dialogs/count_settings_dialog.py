"""
Count Settings Dialog
Dialog für die Konfiguration von Count-Sticker-Einstellungen
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QScrollArea,
    QLineEdit, QColorDialog, QFileDialog, QCheckBox, QPushButton
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor

from ui.glass_button import GlassGlowButton
from ui.spinboxes import StyledSpinBox, StyledDoubleSpinBox
from ui.form_helpers import (
    style_text_input, style_form_button,
    create_form_row, create_row_container, set_uniform_field_width
)

# Gemeinsame Breite für alle Einstellungsdialoge
SETTINGS_DIALOG_WIDTH = 620


class CountSettingsDialog(QDialog):
    """Dialog für Count-Sticker-Einstellungen"""
    
    def __init__(self, parent, config):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Count-Sticker-Einstellungen")
        self.setModal(True)
        self.setMinimumWidth(SETTINGS_DIALOG_WIDTH)
        self.setMinimumHeight(700)
        self.resize(SETTINGS_DIALOG_WIDTH, 700)
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(200)
        self._preview_timer.timeout.connect(self.apply_live_preview)
        self.init_ui()
    
    def _create_button(self, text: str) -> GlassGlowButton:
        """Erstellt einen GlassGlowButton."""
        btn = GlassGlowButton(text, dark_mode=False)
        style_form_button(btn)
        return btn
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Dialog Hintergrund auf Light Mode setzen
        self.setStyleSheet("QDialog { background-color: #f3f3f3; }")
        
        # Buttons oben fixiert - kompakt
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(20, 0, 20, 0)
        button_layout.setSpacing(10)
        button_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        cancel_btn = GlassGlowButton("Abbrechen", dark_mode=False)
        cancel_btn.setFixedSize(140, 44)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        
        button_layout.addStretch()
        
        # Live-Vorschau Button
        preview_btn = GlassGlowButton("Vorschau", dark_mode=False)
        preview_btn.setFixedSize(140, 44)
        preview_btn.clicked.connect(self.apply_live_preview)
        button_layout.addWidget(preview_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        
        save_btn = GlassGlowButton("Speichern", dark_mode=False)
        save_btn.setFixedSize(140, 44)
        save_btn.clicked.connect(self.save_and_accept)
        save_btn.setDefault(True)
        button_layout.addWidget(save_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        
        button_container = QWidget()
        button_container.setLayout(button_layout)
        button_container.setStyleSheet("QWidget { background: #ffffff; border-bottom: 1px solid #e0e0e0; }")
        button_container.setFixedHeight(64)
        
        layout.addWidget(button_container)
        
        # Scroll-Area für Einstellungen
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollBar { }")
        scroll_widget = QWidget()
        main_layout = QVBoxLayout(scroll_widget)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(12)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Breite
        self.width_spin = StyledDoubleSpinBox()
        self.width_spin.setRange(10, 500)
        self.width_spin.setValue(self.config.width_mm)
        set_uniform_field_width(self.width_spin)
        main_layout.addWidget(create_form_row("Breite:", self.width_spin, "mm"))
        
        # Höhe
        self.height_spin = StyledDoubleSpinBox()
        self.height_spin.setRange(10, 500)
        self.height_spin.setValue(self.config.height_mm)
        set_uniform_field_width(self.height_spin)
        main_layout.addWidget(create_form_row("Höhe:", self.height_spin, "mm"))
        
        # DPI
        self.dpi_spin = StyledSpinBox()
        self.dpi_spin.setRange(72, 600)
        self.dpi_spin.setValue(self.config.dpi)
        set_uniform_field_width(self.dpi_spin)
        main_layout.addWidget(create_form_row("DPI:", self.dpi_spin))
        
        # Eckenradius
        self.corner_radius_spin = StyledDoubleSpinBox()
        self.corner_radius_spin.setRange(0, 100)
        self.corner_radius_spin.setValue(self.config.corner_radius)
        set_uniform_field_width(self.corner_radius_spin)
        main_layout.addWidget(create_form_row("Eckenradius:", self.corner_radius_spin, "mm"))
        
        # Rahmenbreite
        self.outline_spin = StyledDoubleSpinBox()
        self.outline_spin.setRange(0, 10)
        self.outline_spin.setValue(self.config.outline_width)
        set_uniform_field_width(self.outline_spin)
        main_layout.addWidget(create_form_row("Rahmenbreite:", self.outline_spin, "mm"))
        
        # Schriftgröße
        self.font_size_spin = StyledDoubleSpinBox()
        self.font_size_spin.setRange(1, 50)
        self.font_size_spin.setValue(self.config.font_size_mm)
        set_uniform_field_width(self.font_size_spin)
        main_layout.addWidget(create_form_row("Schriftgröße:", self.font_size_spin, "mm"))
        
        # Zeilenhöhe
        self.line_height_spin = StyledDoubleSpinBox()
        self.line_height_spin.setRange(1, 50)
        self.line_height_spin.setValue(self.config.line_height_mm)
        set_uniform_field_width(self.line_height_spin)
        main_layout.addWidget(create_form_row("Zeilenhöhe:", self.line_height_spin, "mm"))

        # Anzahl Druckkopien für Count-Sticker
        self.count_copies_spin = StyledSpinBox()
        self.count_copies_spin.setRange(1, 50)
        self.count_copies_spin.setValue(max(1, int(getattr(self.config, 'count_print_copies', 1))))
        set_uniform_field_width(self.count_copies_spin)
        main_layout.addWidget(create_form_row("Anzahl Count-Sticker:", self.count_copies_spin, "x"))

        # Abschnittstrenner
        spacer_section = QWidget()
        spacer_section.setFixedHeight(24)
        main_layout.addWidget(spacer_section)
        
        # Header-Text
        self.header_text_edit = QLineEdit()
        self.header_text_edit.setText(self.config.header_text)
        style_text_input(self.header_text_edit)
        main_layout.addWidget(create_form_row("Header-Text:", self.header_text_edit))

        spacer_normal1 = QWidget()
        spacer_normal1.setFixedHeight(12)
        main_layout.addWidget(spacer_normal1)
        
        # Hintergrundfarbe
        self.bg_color_input = QLineEdit()
        self.bg_color_input.setText(self.config.bg_color)
        style_text_input(self.bg_color_input)
        main_layout.addWidget(create_form_row("Hintergrundfarbe:", self.bg_color_input))
        
        bg_color_btn = self._create_button("Farbe wählen")
        bg_color_btn.clicked.connect(self.choose_bg_color)
        main_layout.addWidget(create_form_row("", bg_color_btn))
        
        # Streifenfarbe
        self.stripe_color_input = QLineEdit()
        self.stripe_color_input.setText(self.config.stripe_color)
        style_text_input(self.stripe_color_input)
        main_layout.addWidget(create_form_row("Streifenfarbe:", self.stripe_color_input))
        
        stripe_color_btn = self._create_button("Farbe wählen")
        stripe_color_btn.clicked.connect(self.choose_stripe_color)
        main_layout.addWidget(create_form_row("", stripe_color_btn))

        spacer_normal2 = QWidget()
        spacer_normal2.setFixedHeight(12)
        main_layout.addWidget(spacer_normal2)
        
        # Schriftart
        self.font_path_input = QLineEdit()
        self.font_path_input.setText(self.config.font_path)
        self.font_path_input.setReadOnly(True)
        style_text_input(self.font_path_input)
        main_layout.addWidget(create_form_row("Schriftart:", self.font_path_input))
        
        font_btn = self._create_button("Schrift wählen")
        font_btn.clicked.connect(self.choose_font)
        main_layout.addWidget(create_form_row("", font_btn))
        
        # Streifen anzeigen
        self.show_stripes_check = QCheckBox("Streifen anzeigen")
        self.show_stripes_check.setChecked(self.config.show_stripes)
        main_layout.addWidget(create_form_row("", self.show_stripes_check, enforce_field_width=False))

        # Live-Preview: Änderungen automatisch anwenden
        self._connect_live_preview_signals()

        main_layout.addStretch()

        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll, 1)

    def _schedule_live_preview(self):
        """Debounced Live-Preview Trigger"""
        self._preview_timer.stop()
        self._preview_timer.start()

    def _connect_live_preview_signals(self):
        """Verbinde UI-Änderungen mit Live-Preview"""
        spins = [
            self.width_spin,
            self.height_spin,
            self.dpi_spin,
            self.corner_radius_spin,
            self.outline_spin,
            self.font_size_spin,
            self.line_height_spin,
            self.count_copies_spin,
        ]
        for spin in spins:
            spin.valueChanged.connect(self._schedule_live_preview)

        self.header_text_edit.textChanged.connect(self._schedule_live_preview)
        self.bg_color_input.textChanged.connect(self._schedule_live_preview)
        self.stripe_color_input.textChanged.connect(self._schedule_live_preview)
        self.font_path_input.textChanged.connect(self._schedule_live_preview)
        self.show_stripes_check.stateChanged.connect(self._schedule_live_preview)
    
    def choose_bg_color(self):
        """Hintergrundfarbe-Dialog öffnen"""
        current_color = QColor(self.bg_color_input.text())
        color = QColorDialog.getColor(current_color, self, "Hintergrundfarbe wählen")
        if color.isValid():
            self.bg_color_input.setText(color.name())
    
    def choose_stripe_color(self):
        """Streifenfarbe-Dialog öffnen"""
        current_color = QColor(self.stripe_color_input.text())
        color = QColorDialog.getColor(current_color, self, "Streifenfarbe wählen")
        if color.isValid():
            self.stripe_color_input.setText(color.name())
    
    def choose_font(self):
        """Schriftart-Auswahl-Dialog öffnen"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Schriftart wählen",
            str(Path(self.config.font_path).parent),
            "TrueType Fonts (*.ttf);;All Files (*.*)"
        )
        if file_path:
            self.font_path_input.setText(file_path)
    
    def apply_live_preview(self):
        """Wende Änderungen live an ohne den Dialog zu schließen"""
        from generators.count_manager import CountStickerGenerator
        
        # Werte aus UI übernehmen
        self.config.width_mm = self.width_spin.value()
        self.config.height_mm = self.height_spin.value()
        self.config.dpi = self.dpi_spin.value()
        self.config.corner_radius = int(self.corner_radius_spin.value())
        self.config.outline_width = int(self.outline_spin.value())
        self.config.font_size_mm = self.font_size_spin.value()
        self.config.line_height_mm = self.line_height_spin.value()
        self.config.count_print_copies = max(1, self.count_copies_spin.value())
        self.config.header_text = self.header_text_edit.text()
        self.config.bg_color = self.bg_color_input.text()
        self.config.stripe_color = self.stripe_color_input.text()
        self.config.font_path = self.font_path_input.text()
        self.config.show_stripes = self.show_stripes_check.isChecked()
        
        # Aktualisiere Parent-Komponenten
        parent = self.parent()
        if parent:
            # Generator neu initialisieren
            if hasattr(parent, 'count_generator'):
                parent.count_generator = CountStickerGenerator(self.config)
            
            # Count-Sticker in Sammlung regenerieren
            loto_mode = getattr(parent, 'current_loto_mode', 'multi')
            count_item_idx = -1
            
            if loto_mode == 'multi':
                if hasattr(parent, '_regenerate_multi_count_sticker'):
                    parent._regenerate_multi_count_sticker()
                    # Finde Count-Sticker Index
                    for i, item in enumerate(getattr(parent, 'collection', [])):
                        if len(item) > 5 and isinstance(item[5], dict) and item[5].get("type") == "count_multi":
                            count_item_idx = i
                            # Cache für diesen Item löschen (Index 7)
                            if len(item) > 7:
                                item[7] = None
                            break
            elif loto_mode == 'single':
                # Regenerate all single count stickers
                try:
                    updated = False
                    for i, item in enumerate(getattr(parent, 'collection', [])):
                        if len(item) > 5 and isinstance(item[5], dict) and item[5].get("type") == "count_single":
                            # Regeneriere diesen Count-Sticker
                            # Detail-Text aus item[4] (description) holen, Fallback auf marker
                            detail_text = item[4] if len(item) > 4 and item[4] else item[5].get("details", "")
                            count_img = parent.count_generator.generate(detail_text, 1)
                            item[0] = count_img
                            if len(item) > 6:
                                item[6] = count_img
                            # Cache löschen
                            if len(item) > 7:
                                item[7] = None
                            updated = True
                            if count_item_idx < 0:
                                count_item_idx = i
                    if updated:
                        if hasattr(parent, 'update_collection_list'):
                            parent.update_collection_list()
                except Exception as e:
                    print(f"Count single preview update failed: {e}")
            
            # Wähle Count-Sticker aus und aktualisiere Vorschau direkt
            if count_item_idx >= 0:
                parent.collection_list.setCurrentRow(count_item_idx)
                # Direkt _on_collection_item_selected aufrufen um Debounce zu umgehen
                if hasattr(parent, '_on_collection_item_selected'):
                    parent._on_collection_item_selected()
            
            # Collection Count Preview auch aktualisieren (für Dimensions-Widget)
            if hasattr(parent, 'update_collection_count_preview'):
                parent.update_collection_count_preview()
    
    def save_and_accept(self):
        """Werte speichern und Dialog schließen"""
        self.config.width_mm = self.width_spin.value()
        self.config.height_mm = self.height_spin.value()
        self.config.dpi = self.dpi_spin.value()
        self.config.corner_radius = int(self.corner_radius_spin.value())
        self.config.outline_width = int(self.outline_spin.value())
        self.config.font_size_mm = self.font_size_spin.value()
        self.config.line_height_mm = self.line_height_spin.value()
        self.config.count_print_copies = max(1, self.count_copies_spin.value())
        self.config.header_text = self.header_text_edit.text()
        self.config.bg_color = self.bg_color_input.text()
        self.config.stripe_color = self.stripe_color_input.text()
        self.config.font_path = self.font_path_input.text()
        self.config.show_stripes = self.show_stripes_check.isChecked()
        self.accept()
