"""
Export Controller
Verwaltet PDF-Export und Export-Einstellungen
"""

from typing import Optional, Any
from PyQt6.QtWidgets import QMessageBox, QFileDialog, QInputDialog
from PyQt6.QtCore import QObject, pyqtSignal
import logging

from generators.pdf_exporter_new import export_pdf_new, pdf_canvas
from core.models import ExportConfig
from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class ExportController(QObject):
    """Controller für PDF-Export"""
    
    # Signals
    export_started = pyqtSignal()
    export_completed = pyqtSignal(str)  # Dateipfad
    export_failed = pyqtSignal(str)  # Fehlermeldung
    settings_changed = pyqtSignal()
    
    def __init__(self, export_config: ExportConfig, config_manager: ConfigManager, parent: Any = None):
        super().__init__(parent)
        self.export_config = export_config
        self.config_manager = config_manager
        self.parent_app = parent
        
        # UI-Elemente (werden später gesetzt)
        self.width_spin = None
        self.height_spin = None
        self.format_combo = None
    
    def set_ui_elements(self, width_spin, height_spin, format_combo):
        """Setze UI-Elemente für Export-Einstellungen"""
        self.width_spin = width_spin
        self.height_spin = height_spin
        self.format_combo = format_combo

        # Initiale Sichtbarkeit beim Start korrekt setzen (wichtig nach App-Neustart)
        self._update_roll_mode_visibility()
    
    def export_pdf(self, collection: list):
        """PDF Export der Sammlung"""
        if not collection:
            QMessageBox.information(self.parent_app, "Info", "Keine Sticker zum Exportieren")
            return
        
        if pdf_canvas is None:
            QMessageBox.warning(
                self.parent_app,
                "Fehler",
                "ReportLab nicht installiert für PDF-Export.\nInstallieren Sie: pip install reportlab"
            )
            return
        
        try:
            self.export_started.emit()
            
            # Rufe die neue export_pdf_new Funktion auf
            export_pdf_new(self.parent_app)
            
            self.export_completed.emit("")
            
        except Exception as e:
            error_msg = f"PDF-Export fehlgeschlagen:\n{e}"
            QMessageBox.critical(self.parent_app, "Fehler", error_msg)
            logger.error(f"PDF-Export Fehler: {e}", exc_info=True)
            self.export_failed.emit(str(e))
    
    def on_format_preset_changed(self, text: str):
        """Handler: Papierformat Preset gewechselt"""
        # Preset-Größen: Breite x Höhe in mm
        presets = {
            "DIN A4 (210 x 297 mm)": (210, 297),
            "DIN A3 (297 x 420 mm)": (297, 420),
            "Versandetikett (100 x 150 mm)": (100, 150),
        }
        
        if text == "Rollenmodus":
            # Aktiviere Rollen-Modus
            self.export_config.roll_mode = True
            self._update_roll_mode_visibility()
            self.config_manager.save_export(self.export_config)
            logger.info("Rollenmodus aktiviert")
            self.settings_changed.emit()
            
        elif text in presets:
            # Deaktiviere Rollen-Modus bei DIN-Formaten
            self.export_config.roll_mode = False
            self._update_roll_mode_visibility()
            
            width, height = presets[text]
            
            # Blockiere Signale um doppelte Aufrufe zu vermeiden
            if self.width_spin and self.height_spin:
                self.width_spin.blockSignals(True)
                self.height_spin.blockSignals(True)
                
                self.width_spin.setValue(width)
                self.height_spin.setValue(height)
                
                self.width_spin.blockSignals(False)
                self.height_spin.blockSignals(False)
            
            # Speichere die Einstellungen
            self.export_config.sheet_width_mm = width
            self.export_config.sheet_height_mm = height
            self.config_manager.save_export(self.export_config)
            
            logger.info(f"Papierformat gewechselt: {text}")
            self.settings_changed.emit()
    
    def on_sheet_size_changed(self):
        """Handler: Papierbreite oder -höhe geändert"""
        if not self.width_spin or not self.height_spin:
            return
        
        try:
            width = self.width_spin.value()
            height = self.height_spin.value()
            
            # Aktualisiere Export-Config
            self.export_config.sheet_width_mm = width
            self.export_config.sheet_height_mm = height
            
            # Überprüfe ob noch ein Preset passt
            presets = {
                "DIN A4 (210 x 297 mm)": (210, 297),
                "DIN A3 (297 x 420 mm)": (297, 420),
                "Versandetikett (100 x 150 mm)": (100, 150),
            }
            
            found_preset = False
            for preset_name, (p_width, p_height) in presets.items():
                if abs(width - p_width) < 0.1 and abs(height - p_height) < 0.1:
                    if self.format_combo:
                        self.format_combo.blockSignals(True)
                        self.format_combo.setCurrentText(preset_name)
                        self.format_combo.blockSignals(False)
                    found_preset = True
                    break
            
            if not found_preset:
                # Nur zu Rollenmodus wechseln wenn bereits im Roll-Mode
                if self.export_config.roll_mode and self.format_combo:
                    self.format_combo.blockSignals(True)
                    self.format_combo.setCurrentText("Rollenmodus")
                    self.format_combo.blockSignals(False)
            
            # Speichere die Einstellungen
            self.config_manager.save_export(self.export_config)
            self.settings_changed.emit()
            
        except Exception as e:
            logger.error(f"Fehler beim Ändern der Seitengröße: {e}")
    
    def on_export_settings_changed(self):
        """Handler: Irgendeine Export-Einstellung geändert"""
        try:
            # Speichere alle Änderungen
            self.config_manager.save_export(self.export_config)
            self.settings_changed.emit()
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Export-Einstellungen: {e}")
    
    def on_roll_width_changed(self, width_mm: float):
        """Handler: Rollenbreite geändert"""
        try:
            self.export_config.roll_width_mm = width_mm
            self.config_manager.save_export(self.export_config)
            self.settings_changed.emit()
            logger.info(f"Rollenbreite geändert auf: {width_mm}mm")
        except Exception as e:
            logger.error(f"Fehler beim Ändern der Rollenbreite: {e}")

    def _update_roll_mode_visibility(self):
        """Aktualisiere Sichtbarkeit von Höhen-Eingabe basierend auf Roll-Modus"""
        roll_mode_active = self.export_config.roll_mode
        
        # Zeige/Verstecke Sheet-Breite/Höhe im Rollenmodus
        width_label = getattr(self.parent_app, 'width_label', None)
        width_container = getattr(self.parent_app, 'width_container', None)
        width_spin = getattr(self.parent_app, 'width_spin', None)
        if width_label:
            width_label.setVisible(not roll_mode_active)
        if width_container:
            width_container.setVisible(not roll_mode_active)
        if width_spin:
            width_spin.setVisible(not roll_mode_active)

        height_label = getattr(self.parent_app, 'height_label', None)
        height_container = getattr(self.parent_app, 'height_container', None)
        height_spin = getattr(self.parent_app, 'height_spin', None)
        if height_label:
            height_label.setVisible(not roll_mode_active)
        if height_container:
            height_container.setVisible(not roll_mode_active)
        if height_spin:
            height_spin.setVisible(not roll_mode_active)

        # Rollenbreite nur im Rollenmodus anzeigen
        roll_width_label = getattr(self.parent_app, 'roll_width_label', None)
        roll_width_container = getattr(self.parent_app, 'roll_width_container', None)
        roll_width_spin = getattr(self.parent_app, 'roll_width_spin', None)
        if roll_width_label:
            roll_width_label.setVisible(roll_mode_active)
        if roll_width_container:
            roll_width_container.setVisible(roll_mode_active)
        if roll_width_spin:
            roll_width_spin.setVisible(roll_mode_active)
        
        logger.info(f"Roll-Modus Sichtbarkeit aktualisiert: {roll_mode_active}")
