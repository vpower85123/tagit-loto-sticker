"""
Sticker Settings Dialog
Dialog für die Konfiguration von LOTO-Sticker-Einstellungen
"""

from pathlib import Path
from typing import List, Dict, Any
import json
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QScrollArea,
    QLineEdit, QColorDialog, QFileDialog, QMessageBox, QPushButton, QLabel
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from ui.glass_button import GlassGlowButton
from ui.components import ModernComboBox
from ui.spinboxes import StyledSpinBox, StyledDoubleSpinBox
from ui.form_helpers import (
    style_text_input, style_combo_box, style_form_button,
    create_form_row, create_row_container, set_uniform_field_width
)
from core.paths import PathManager

# Gemeinsame Breite für alle Einstellungsdialoge
SETTINGS_DIALOG_WIDTH = 620


class StickerSettingsDialog(QDialog):
    """Dialog für Sticker-Einstellungen"""
    
    def __init__(self, parent, config):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Sticker-Einstellungen")
        self.setModal(True)
        self.setMinimumWidth(SETTINGS_DIALOG_WIDTH)
        self.setMinimumHeight(700)
        self.resize(SETTINGS_DIALOG_WIDTH, 700)
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

        # Presets (zentriert über den Eingabefeldern)
        preset_title = QLabel("Presets")
        preset_title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        preset_title.setStyleSheet("color: #2c3e50; font-weight: 600;")
        main_layout.addWidget(preset_title)

        self.preset_combo = ModernComboBox(dark_mode=False)
        self.preset_combo.addItems(["Preset 1", "Preset 2", "Preset 3"])
        style_combo_box(self.preset_combo)

        preset_load_btn = self._create_button("Preset laden")
        preset_save_btn = self._create_button("Preset speichern")
        preset_load_btn.clicked.connect(self._load_selected_preset)
        preset_save_btn.clicked.connect(self._save_selected_preset)

        preset_container = QWidget()
        preset_layout = QVBoxLayout(preset_container)
        preset_layout.setContentsMargins(0, 0, 0, 0)
        preset_layout.setSpacing(10)
        preset_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        preset_layout.addWidget(self.preset_combo, 0, Qt.AlignmentFlag.AlignHCenter)
        preset_layout.addWidget(preset_load_btn, 0, Qt.AlignmentFlag.AlignHCenter)
        preset_layout.addWidget(preset_save_btn, 0, Qt.AlignmentFlag.AlignHCenter)
        main_layout.addWidget(preset_container)

        spacer_preset = QWidget()
        spacer_preset.setFixedHeight(12)
        main_layout.addWidget(spacer_preset)
        
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
        
        # Eckenradius - Maximum erlaubt sehr hohe Werte für komplett runde Formen
        self.corner_radius_spin = StyledDoubleSpinBox()
        self.corner_radius_spin.setRange(0, 500)
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
        
        # Symbol-Größe
        self.symbol_size_spin = StyledDoubleSpinBox()
        self.symbol_size_spin.setRange(5, 100)
        self.symbol_size_spin.setSingleStep(0.5)
        self.symbol_size_spin.setValue(self.config.symbol_size_mm)
        set_uniform_field_width(self.symbol_size_spin)
        main_layout.addWidget(create_form_row("Symbol-Größe:", self.symbol_size_spin, "mm"))
        
        # Symbol-Eckenradius
        self.symbol_corner_radius_spin = StyledDoubleSpinBox()
        self.symbol_corner_radius_spin.setRange(0, 50)
        self.symbol_corner_radius_spin.setValue(self.config.symbol_corner_radius)
        set_uniform_field_width(self.symbol_corner_radius_spin)
        main_layout.addWidget(create_form_row("Symbol-Eckenradius:", self.symbol_corner_radius_spin, "mm"))

        # Symbol-Position X
        self.symbol_offset_x_spin = StyledDoubleSpinBox()
        self.symbol_offset_x_spin.setRange(-200, 200)
        self.symbol_offset_x_spin.setSingleStep(0.5)
        self.symbol_offset_x_spin.setValue(self.config.symbol_offset_x_mm)
        set_uniform_field_width(self.symbol_offset_x_spin)
        main_layout.addWidget(create_form_row("Symbol-Position X:", self.symbol_offset_x_spin, "mm"))

        # Symbol-Position Y
        self.symbol_offset_y_spin = StyledDoubleSpinBox()
        self.symbol_offset_y_spin.setRange(-200, 200)
        self.symbol_offset_y_spin.setSingleStep(0.5)
        self.symbol_offset_y_spin.setValue(self.config.symbol_offset_y_mm)
        set_uniform_field_width(self.symbol_offset_y_spin)
        main_layout.addWidget(create_form_row("Symbol-Position Y:", self.symbol_offset_y_spin, "mm"))
        
        # Spacer
        spacer = QWidget()
        spacer.setFixedHeight(24)
        main_layout.addWidget(spacer)

        spacer3 = QWidget()
        spacer3.setFixedHeight(24)
        main_layout.addWidget(spacer3)
        
        # Sticker-Farbe
        self.color_input = QLineEdit()
        self.color_input.setText(self.config.sticker_color)
        style_text_input(self.color_input)
        main_layout.addWidget(create_form_row("Sticker-Farbe:", self.color_input))
        
        color_btn = self._create_button("Farbe wählen")
        color_btn.clicked.connect(self.choose_color)
        main_layout.addWidget(create_form_row("", color_btn))
        
        spacer4 = QWidget()
        spacer4.setFixedHeight(12)
        main_layout.addWidget(spacer4)
        
        # Schriftart
        self.font_path_input = QLineEdit()
        self.font_path_input.setText(self.config.font_path)
        self.font_path_input.setReadOnly(True)
        style_text_input(self.font_path_input)
        main_layout.addWidget(create_form_row("Schriftart:", self.font_path_input))
        
        font_btn = self._create_button("Schrift wählen")
        font_btn.clicked.connect(self.choose_font)
        main_layout.addWidget(create_form_row("", font_btn))
        
        main_layout.addStretch()
        
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll, 1)
    
    def choose_color(self):
        """Farbauswahl-Dialog öffnen"""
        current_color = QColor(self.color_input.text())
        color = QColorDialog.getColor(current_color, self, "Sticker-Farbe wählen")
        if color.isValid():
            self.color_input.setText(color.name())

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
        from generators.sticker_generator import StickerGenerator
        
        # Werte aus UI übernehmen
        self.config.width_mm = self.width_spin.value()
        self.config.height_mm = self.height_spin.value()
        self.config.dpi = self.dpi_spin.value()
        self.config.corner_radius = int(self.corner_radius_spin.value())
        self.config.outline_width = int(self.outline_spin.value())
        self.config.font_size_mm = self.font_size_spin.value()
        self.config.line_height_mm = self.line_height_spin.value()
        self.config.symbol_size_mm = self.symbol_size_spin.value()
        self.config.symbol_corner_radius = int(self.symbol_corner_radius_spin.value())
        self.config.symbol_offset_x_mm = self.symbol_offset_x_spin.value()
        self.config.symbol_offset_y_mm = self.symbol_offset_y_spin.value()
        self.config.sticker_color = self.color_input.text()
        self.config.font_path = self.font_path_input.text()
        # QR-Code-Einstellungen beibehalten (nicht überschreiben!)
        
        # Aktualisiere Parent-Komponenten
        parent = self.parent()
        if parent:
            # Generator neu initialisieren
            if hasattr(parent, 'sticker_generator'):
                parent.sticker_generator = StickerGenerator(self.config)
            
            # Speichere Form-Config
            if hasattr(parent, '_save_current_form_config'):
                parent._save_current_form_config()
            
            # Update Preview Controller generator reference
            if hasattr(parent, 'preview_controller') and hasattr(parent, 'sticker_generator'):
                parent.preview_controller.sticker_generator = parent.sticker_generator
            
            # Vorschau aktualisieren
            if hasattr(parent, 'update_sticker_preview'):
                parent.update_sticker_preview()
    
    def save_and_accept(self):
        """Werte speichern und Dialog schließen"""
        self.config.width_mm = self.width_spin.value()
        self.config.height_mm = self.height_spin.value()
        self.config.dpi = self.dpi_spin.value()
        self.config.corner_radius = int(self.corner_radius_spin.value())
        self.config.outline_width = int(self.outline_spin.value())
        self.config.font_size_mm = self.font_size_spin.value()
        self.config.line_height_mm = self.line_height_spin.value()
        self.config.symbol_size_mm = self.symbol_size_spin.value()
        self.config.symbol_corner_radius = int(self.symbol_corner_radius_spin.value())
        self.config.symbol_offset_x_mm = self.symbol_offset_x_spin.value()
        self.config.symbol_offset_y_mm = self.symbol_offset_y_spin.value()
        self.config.sticker_color = self.color_input.text()
        self.config.font_path = self.font_path_input.text()
        # QR-Code-Einstellungen beibehalten (nicht überschreiben!)
        self.accept()

    def _read_config_file(self) -> Dict[str, Any]:
        try:
            if PathManager.CONFIG_PATH.exists():
                return json.loads(PathManager.CONFIG_PATH.read_text("utf-8"))
        except Exception:
            pass
        return {}

    def _write_config_file(self, data: Dict[str, Any]) -> None:
        try:
            PathManager.CONFIG_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            QMessageBox.warning(self, "Fehler", f"Preset konnte nicht gespeichert werden:\n{e}")

    def _get_presets(self) -> List[Dict[str, Any] | None]:
        data = self._read_config_file()
        presets = data.get("sticker_presets", []) or []
        if not isinstance(presets, list):
            presets = []
        while len(presets) < 3:
            presets.append(None)
        return presets[:3]

    def _save_presets(self, presets: List[Dict[str, Any] | None]) -> None:
        data = self._read_config_file()
        data["sticker_presets"] = presets[:3]
        self._write_config_file(data)

    def _collect_current_settings(self) -> Dict[str, Any]:
        return {
            "width_mm": self.width_spin.value(),
            "height_mm": self.height_spin.value(),
            "dpi": self.dpi_spin.value(),
            "corner_radius": int(self.corner_radius_spin.value()),
            "outline_width": int(self.outline_spin.value()),
            "font_size_mm": self.font_size_spin.value(),
            "line_height_mm": self.line_height_spin.value(),
            "symbol_size_mm": self.symbol_size_spin.value(),
            "symbol_corner_radius": int(self.symbol_corner_radius_spin.value()),
            "symbol_offset_x_mm": self.symbol_offset_x_spin.value(),
            "symbol_offset_y_mm": self.symbol_offset_y_spin.value(),
            "sticker_color": self.color_input.text(),
            "font_path": self.font_path_input.text(),
            # QR-Einstellungen aus aktueller Config übernehmen
            "qr_mode_enabled": getattr(self.config, 'qr_mode_enabled', False),
            "qr_image_path": getattr(self.config, 'qr_image_path', None),
            "qr_placeholder_text": getattr(self.config, 'qr_placeholder_text', "QR"),
            "qr_placeholder_bg": getattr(self.config, 'qr_placeholder_bg', "#FFFFFF"),
        }

    def _apply_settings_to_ui(self, settings: Dict[str, Any]) -> None:
        if not settings:
            return
        
        print(f"DEBUG: Settings to apply: {settings}")
        
        # Block signals während dem Laden um Signalkaskaden zu vermeiden
        widgets = [
            self.width_spin, self.height_spin, self.dpi_spin,
            self.corner_radius_spin, self.outline_spin, self.font_size_spin,
            self.line_height_spin, self.symbol_size_spin, self.symbol_corner_radius_spin,
            self.symbol_offset_x_spin, self.symbol_offset_y_spin
        ]
        
        for w in widgets:
            w.blockSignals(True)
        
        # Setze alle Werte explizit - UI
        width = float(settings.get("width_mm", 135.0))
        height = float(settings.get("height_mm", 35.0))
        dpi = int(settings.get("dpi", 300))
        corner_radius = float(settings.get("corner_radius", 80))
        outline_width = float(settings.get("outline_width", 10))
        font_size = float(settings.get("font_size_mm", 6.0))
        line_height = float(settings.get("line_height_mm", 6.0))
        symbol_size = float(settings.get("symbol_size_mm", 27.0))
        symbol_corner_radius = float(settings.get("symbol_corner_radius", 24))
        symbol_offset_x = float(settings.get("symbol_offset_x_mm", 4.0))
        symbol_offset_y = float(settings.get("symbol_offset_y_mm", 4.0))
        sticker_color = settings.get("sticker_color", "#ffc000")
        font_path = settings.get("font_path", "fonts/AmazonEmber_Bd.ttf")
        
        # UI Widgets setzen
        self.width_spin.setValue(width)
        self.height_spin.setValue(height)
        self.dpi_spin.setValue(dpi)
        self.corner_radius_spin.setValue(corner_radius)
        self.outline_spin.setValue(outline_width)
        self.font_size_spin.setValue(font_size)
        self.line_height_spin.setValue(line_height)
        self.symbol_size_spin.setValue(symbol_size)
        self.symbol_corner_radius_spin.setValue(symbol_corner_radius)
        self.symbol_offset_x_spin.setValue(symbol_offset_x)
        self.symbol_offset_y_spin.setValue(symbol_offset_y)
        self.color_input.setText(sticker_color)
        self.font_path_input.setText(font_path)
        
        # Config DIREKT setzen (wichtig!)
        self.config.width_mm = width
        self.config.height_mm = height
        self.config.dpi = dpi
        self.config.corner_radius = int(corner_radius)
        self.config.outline_width = int(outline_width)
        self.config.font_size_mm = font_size
        self.config.line_height_mm = line_height
        self.config.symbol_size_mm = symbol_size
        self.config.symbol_corner_radius = int(symbol_corner_radius)
        self.config.symbol_offset_x_mm = symbol_offset_x
        self.config.symbol_offset_y_mm = symbol_offset_y
        self.config.sticker_color = sticker_color
        self.config.font_path = font_path
        # QR-Code-Einstellungen beibehalten (nicht überschreiben!)
        
        # Signals wieder aktivieren
        for w in widgets:
            w.blockSignals(False)
        
        print(f"DEBUG: After apply - UI: symbol_size={self.symbol_size_spin.value()}, font_size={self.font_size_spin.value()}")
        print(f"DEBUG: After apply - Config: symbol_size={self.config.symbol_size_mm}, font_size={self.config.font_size_mm}")

    def _save_selected_preset(self) -> None:
        presets = self._get_presets()
        index = max(0, min(2, self.preset_combo.currentIndex()))
        presets[index] = self._collect_current_settings()
        self._save_presets(presets)
        QMessageBox.information(self, "Preset", f"Preset {index + 1} gespeichert.")

    def _load_selected_preset(self) -> None:
        presets = self._get_presets()
        index = max(0, min(2, self.preset_combo.currentIndex()))
        print(f"DEBUG: Loading preset {index + 1}, presets={presets}")
        preset = presets[index]
        if not preset:
            QMessageBox.information(self, "Preset", f"Preset {index + 1} ist leer.")
            return
        print(f"DEBUG: Applying preset settings: {preset}")
        self._apply_settings_to_ui(preset)
        self.apply_live_preview()
        QMessageBox.information(self, "Preset", f"Preset {index + 1} wurde geladen.")
