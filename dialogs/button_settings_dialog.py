"""
Button Settings Dialog
Konfiguration der GlassGlowButton-Darstellung
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QGroupBox, QScrollArea, QWidget, QColorDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from ui.glass_button import GlassGlowButton, ButtonSettings
from ui.spinboxes import StyledSpinBox, StyledDoubleSpinBox
from ui.form_helpers import (
    style_text_input, style_form_button, create_form_row, create_row_container
)
from core.constants import SETTINGS_DIALOG_WIDTH


class ButtonSettingsDialog(QDialog):
    """Dialog für Button-Einstellungen (GlassGlowButton)"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Button-Einstellungen")
        self.setModal(True)
        self.setMinimumWidth(SETTINGS_DIALOG_WIDTH)
        self.setMinimumHeight(700)
        self.resize(SETTINGS_DIALOG_WIDTH, 700)
        self.init_ui()
    
    def resizeEvent(self, event):
        """Sicherstelle dass ScrollArea die Buttons nicht überlagert"""
        super().resizeEvent(event)
        # Wenn Höhe unter 700px, skaliere ScrollArea kleiner
        if self.height() < 700:
            pass  # Qt handelt das automatisch mit layout
    
    def _create_button(self, text: str) -> GlassGlowButton:
        """Erstellt einen GlassGlowButton."""
        btn = GlassGlowButton(text, dark_mode=False)
        # Einheitliche Größe für alle Dialog-Buttons
        style_form_button(btn)
        return btn
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Vorschau-Button
        preview_group = QGroupBox("Vorschau")
        preview_layout = QVBoxLayout(preview_group)
        self.preview_btn = GlassGlowButton("Vorschau Button", dark_mode=False)
        self.preview_btn.setMinimumHeight(60)
        preview_layout.addWidget(self.preview_btn)
        layout.addWidget(preview_group, 0)  # 0 = kein Stretch
        
        # Scroll-Area für Einstellungen
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollBar { }")
        scroll_widget = QWidget()
        main_layout = QVBoxLayout(scroll_widget)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(12)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # === Allgemeine Einstellungen ===
        general_label = QLabel("Allgemein")
        general_label.setStyleSheet("font-weight: bold; font-size: 12pt; margin-top: 10px;")
        main_layout.addWidget(general_label)

        # Border-Radius
        self.radius_spin = StyledDoubleSpinBox()
        self.radius_spin.setRange(0, 50)
        self.radius_spin.setSuffix(" px")
        self.radius_spin.setValue(float(ButtonSettings.get("border_radius") or 0))
        self.radius_spin.valueChanged.connect(self._update_preview)
        main_layout.addWidget(create_form_row("Eckenradius:", self.radius_spin))

        # Border-Breite
        self.border_spin = StyledDoubleSpinBox()
        self.border_spin.setRange(0, 10)
        self.border_spin.setSuffix(" px")
        self.border_spin.setValue(float(ButtonSettings.get("border_width") or 0))
        self.border_spin.valueChanged.connect(self._update_preview)
        main_layout.addWidget(create_form_row("Rahmenbreite:", self.border_spin))

        # Glow-Intensität
        self.glow_spin = StyledDoubleSpinBox()
        self.glow_spin.setRange(0, 2)
        self.glow_spin.setSingleStep(0.1)
        self.glow_spin.setValue(float(ButtonSettings.get("glow_intensity") or 0))
        self.glow_spin.valueChanged.connect(self._update_preview)
        main_layout.addWidget(create_form_row("Glow-Intensität:", self.glow_spin))

        # Hover-Lift
        # self.hover_spin = StyledDoubleSpinBox()
        # self.hover_spin.setRange(0, 10)
        # self.hover_spin.setSuffix(" px")
        # self.hover_spin.setValue(float(ButtonSettings.get("hover_lift") or 0))
        # self.hover_spin.valueChanged.connect(self._update_preview)
        # main_layout.addWidget(create_form_row("Hover-Anhebung:", self.hover_spin))

        # Press-Offset
        # self.press_spin = StyledDoubleSpinBox()
        # self.press_spin.setRange(0, 10)
        # self.press_spin.setSuffix(" px")
        # self.press_spin.setValue(float(ButtonSettings.get("press_offset") or 0))
        # self.press_spin.valueChanged.connect(self._update_preview)
        # main_layout.addWidget(create_form_row("Press-Versatz:", self.press_spin))

        # Animation
        self.anim_spin = StyledSpinBox()
        self.anim_spin.setRange(50, 1000)
        self.anim_spin.setSuffix(" ms")
        self.anim_spin.setValue(int(ButtonSettings.get("animation_duration") or 0))
        self.anim_spin.valueChanged.connect(self._update_preview)
        main_layout.addWidget(create_form_row("Animation-Dauer:", self.anim_spin))

        # Mindesthöhe
        self.height_spin = StyledSpinBox()
        self.height_spin.setRange(20, 100)
        self.height_spin.setSuffix(" px")
        self.height_spin.setValue(int(ButtonSettings.get("min_height") or 0))
        self.height_spin.valueChanged.connect(self._update_preview)
        main_layout.addWidget(create_form_row("Mindesthöhe:", self.height_spin))

        # Schriftgröße
        self.font_spin = StyledSpinBox()
        self.font_spin.setRange(8, 24)
        self.font_spin.setSuffix(" pt")
        self.font_spin.setValue(int(ButtonSettings.get("font_size") or 0))
        self.font_spin.valueChanged.connect(self._update_preview)
        main_layout.addWidget(create_form_row("Schriftgröße:", self.font_spin))

        # Spacer zwischen Allgemein und Farb-Einstellungen
        spacer_light = QWidget()
        spacer_light.setFixedHeight(24)
        main_layout.addWidget(spacer_light)

        # === Button Farben ===
        light_label = QLabel("Button-Farben")
        light_label.setStyleSheet("font-weight: bold; font-size: 12pt; margin-top: 10px;")
        main_layout.addWidget(light_label)

        # Light Glow Farbe
        self.light_glow_input = QLineEdit()
        self.light_glow_input.setText(str(ButtonSettings.get("light_glow_color") or ""))
        self.light_glow_input.textChanged.connect(self._update_preview)
        style_text_input(self.light_glow_input)
        light_glow_btn = self._create_button("Wählen")
        light_glow_btn.clicked.connect(lambda: self._choose_color(self.light_glow_input))
        light_glow_row = create_row_container(self.light_glow_input, light_glow_btn)
        main_layout.addWidget(create_form_row("Gradient Start (Pink):", light_glow_row, enforce_field_width=False))

        # Light Border Farbe
        self.light_border_input = QLineEdit()
        self.light_border_input.setText(str(ButtonSettings.get("light_border_color") or ""))
        self.light_border_input.textChanged.connect(self._update_preview)
        style_text_input(self.light_border_input)
        light_border_btn = self._create_button("Wählen")
        light_border_btn.clicked.connect(lambda: self._choose_color(self.light_border_input))
        light_border_row = create_row_container(self.light_border_input, light_border_btn)
        main_layout.addWidget(create_form_row("Gradient End (Purple):", light_border_row, enforce_field_width=False))

        # Light Text Farbe
        self.light_text_input = QLineEdit()
        self.light_text_input.setText(str(ButtonSettings.get("light_text_color") or ""))
        self.light_text_input.textChanged.connect(self._update_preview)
        style_text_input(self.light_text_input)
        light_text_btn = self._create_button("Wählen")
        light_text_btn.clicked.connect(lambda: self._choose_color(self.light_text_input))
        light_text_row = create_row_container(self.light_text_input, light_text_btn)
        main_layout.addWidget(create_form_row("Text-Farbe:", light_text_row, enforce_field_width=False))

        # Light BG Alpha
        # self.light_alpha_spin = StyledSpinBox()
        # self.light_alpha_spin.setRange(0, 255)
        # self.light_alpha_spin.setValue(int(ButtonSettings.get("light_bg_alpha") or 0))
        # self.light_alpha_spin.valueChanged.connect(self._update_preview)
        # main_layout.addWidget(create_form_row("Hintergrund-Alpha:", self.light_alpha_spin))

        main_layout.addStretch()

        scroll.setWidget(scroll_widget)
        
        # Buttons ZUERST ins Layout (damit ScrollArea nur übrigen Platz bekommt)
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(12, 10, 12, 14)
        button_layout.setSpacing(12)
        
        reset_btn = self._create_button("Zurücksetzen")
        reset_btn.clicked.connect(self._reset_settings)
        button_layout.addWidget(reset_btn)
        
        button_layout.addStretch()
        
        cancel_btn = self._create_button("Abbrechen")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        save_btn = self._create_button("Speichern")
        save_btn.clicked.connect(self._save_settings)
        save_btn.setDefault(True)
        button_layout.addWidget(save_btn)
        
        # Button Container mit fester Höhe
        button_container = QWidget()
        button_container.setLayout(button_layout)
        button_container.setContentsMargins(0, 0, 0, 0)
        
        # WICHTIG: ScrollArea ZUERST, dann Buttons am Ende
        # Damit die Buttons unten bleiben
        layout.addWidget(scroll, 1)  # Stretch für ScrollArea
        layout.addWidget(button_container)
    
    def _choose_color(self, input_field: QLineEdit):
        """Farbauswahl-Dialog öffnen"""
        current_color = QColor(input_field.text())
        color = QColorDialog.getColor(current_color, self, "Farbe wählen")
        if color.isValid():
            input_field.setText(color.name().upper())
    
    def _update_preview(self):
        """Aktualisiere Einstellungen und Vorschau in Echtzeit"""
        settings = {
            "border_radius": self.radius_spin.value(),
            "border_width": self.border_spin.value(),
            "glow_intensity": self.glow_spin.value(),
            # "hover_lift": self.hover_spin.value(),
            # "press_offset": self.press_spin.value(),
            "animation_duration": self.anim_spin.value(),
            "min_height": self.height_spin.value(),
            "font_size": self.font_spin.value(),
            "light_glow_color": self.light_glow_input.text(),
            "light_border_color": self.light_border_input.text(),
            "light_text_color": self.light_text_input.text(),
            # "light_bg_alpha": self.light_alpha_spin.value(),
        }
        # set_all ruft automatisch refresh_settings() für alle Buttons auf
        ButtonSettings.set_all(settings)
    
    def _reset_settings(self):
        """Setze alle Einstellungen auf Standard zurück"""
        ButtonSettings.reset()
        self.radius_spin.setValue(float(ButtonSettings.get("border_radius") or 0))
        self.border_spin.setValue(float(ButtonSettings.get("border_width") or 0))
        self.glow_spin.setValue(float(ButtonSettings.get("glow_intensity") or 0))
        # self.hover_spin.setValue(float(ButtonSettings.get("hover_lift") or 0))
        # self.press_spin.setValue(float(ButtonSettings.get("press_offset") or 0))
        self.anim_spin.setValue(int(ButtonSettings.get("animation_duration") or 0))
        self.height_spin.setValue(int(ButtonSettings.get("min_height") or 0))
        self.font_spin.setValue(int(ButtonSettings.get("font_size") or 0))
        self.light_glow_input.setText(str(ButtonSettings.get("light_glow_color") or ""))
        self.light_border_input.setText(str(ButtonSettings.get("light_border_color") or ""))
        self.light_text_input.setText(str(ButtonSettings.get("light_text_color") or ""))
        # self.light_alpha_spin.setValue(int(ButtonSettings.get("light_bg_alpha") or 0))
    
    def _save_settings(self):
        """Speichere Einstellungen in Datei"""
        self._update_preview()
        ButtonSettings.save_to_file()
        self.accept()
