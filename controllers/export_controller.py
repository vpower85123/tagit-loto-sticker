"""
Export Controller
Verwaltet PDF-Export und Export-Einstellungen
"""

from typing import Optional, Any
from PyQt6.QtWidgets import QMessageBox, QFileDialog, QInputDialog
from PyQt6.QtCore import QObject, pyqtSignal
import logging
import math

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
            self._update_dimensions_widget()
            
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
            self._update_dimensions_widget()
    
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
            self._update_dimensions_widget()
            
        except Exception as e:
            logger.error(f"Fehler beim Ändern der Seitengröße: {e}")
    
    def on_export_settings_changed(self):
        """Handler: Irgendeine Export-Einstellung geändert"""
        try:
            # Lese ggf. aktuelle Werte aus App-Spinboxen
            margin_spin = getattr(self.parent_app, 'margin_spin', None)
            gap_spin = getattr(self.parent_app, 'gap_spin', None)
            if margin_spin is not None:
                self.export_config.margin_mm = margin_spin.value()
            if gap_spin is not None:
                self.export_config.gap_mm = gap_spin.value()

            # Speichere alle Änderungen
            self.config_manager.save_export(self.export_config)
            self.settings_changed.emit()
            self._update_dimensions_widget()
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Export-Einstellungen: {e}")
    
    def on_roll_width_changed(self, width_mm: Optional[float] = None):
        """Handler: Rollenbreite geändert"""
        try:
            if width_mm is None:
                roll_spin = getattr(self.parent_app, 'roll_width_spin', None)
                if roll_spin is None:
                    return
                width_mm = roll_spin.value()

            self.export_config.roll_width_mm = width_mm
            self.config_manager.save_export(self.export_config)
            self.settings_changed.emit()
            self._update_dimensions_widget()
            logger.info(f"Rollenbreite geändert auf: {width_mm}mm")
        except Exception as e:
            logger.error(f"Fehler beim Ändern der Rollenbreite: {e}")

    def calculate_roll_height(self):
        """Berechne Rollenhöhe (Platzhalter, aktuell nicht verwendet)."""
        return None

    def _update_dimensions_widget(self):
        """Aktualisiert die Dimensions-Vorschau, falls vorhanden."""
        widget = getattr(self.parent_app, 'dimensions_widget', None)
        if widget is None or self.parent_app is None:
            return

        widget.set_dimensions(
            self.export_config.sheet_width_mm,
            self.export_config.sheet_height_mm,
            self.export_config.margin_mm,
            self.export_config.gap_mm,
            self.export_config.roll_mode,
            self.parent_app.sticker_config.width_mm,
            self.parent_app.sticker_config.height_mm,
            self.export_config.roll_width_mm,
        )

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

    def compute_auto_sheet_height(self, count_mode, regular_items, count_single_items, sheet_w_mm, header_h_mm=0.0):
        """
        Berechne automatische Seitenhöhe (mm), so dass alle Sticker auf eine Seite passen.
        Layout: (optional Header) -> Raster reguläre Sticker -> Raster Count-Sticker (single mode).
        """
        app = self.parent_app
        if app is None:
            raise RuntimeError("ExportController benötigt parent_app für compute_auto_sheet_height")

        margin = self.export_config.margin_mm
        gap = self.export_config.gap_mm

        # Basis-Dimensionen
        st_w = app.sticker_config.width_mm
        st_h = app.sticker_config.height_mm

        # Header (nur Multi)
        header_block_h = 0.0
        if count_mode == 'multi' and self.export_config.include_count_header and regular_items:
            if header_h_mm > 0:
                header_block_h = header_h_mm + gap
            else:
                header_block_h = app.count_config.height_mm + gap

        # Rotation beurteilen (nur für reguläre Sticker)
        rotate_mode = getattr(self.export_config, 'sticker_rotate_mode', 'none')

        def cols_for(w_s, h_s):
            usable_w = sheet_w_mm - 2 * margin
            return max(1, int((usable_w + gap) // (w_s + gap)))

        if rotate_mode == 'always':
            use_rot = True
        elif rotate_mode == 'auto':
            cols_norm = cols_for(st_w, st_h)
            cols_rot = cols_for(st_h, st_w)
            use_rot = cols_rot > cols_norm
        else:
            use_rot = False

        if use_rot:
            st_w, st_h = st_h, st_w

        # Reguläre Sticker Raster (nur im Multi-Modus)
        n_reg = len(regular_items)
        cols_reg = cols_for(st_w, st_h)
        rows_reg = math.ceil(n_reg / cols_reg) if n_reg else 0
        reg_block_h = 0.0

        # Im Single-Modus werden reguläre Sticker mit Count-Stickern als Paare behandelt
        if count_mode != 'single' and rows_reg:
            reg_block_h = rows_reg * st_h + (rows_reg - 1) * gap

        # Count-Singles Block (nur single Mode)
        count_block_h = 0.0
        if count_mode == 'single':
            # Single-Modus: identische Logik wie beim PDF-Export verwenden
            ct_w_orig = app.count_config.width_mm
            ct_h_orig = app.count_config.height_mm
            count_copies = max(1, int(getattr(app.count_config, 'count_print_copies', 1)))
            st_w_orig = st_w
            st_h_orig = st_h
            usable_w = sheet_w_mm - 2 * margin
            total_pairs = len(regular_items)

            def evaluate(lo_rot: bool, ct_rot: bool):
                loto_w = st_h_orig if lo_rot else st_w_orig
                loto_h = st_w_orig if lo_rot else st_h_orig
                count_w = ct_h_orig if ct_rot else ct_w_orig
                count_h = ct_w_orig if ct_rot else ct_h_orig
                pair_width_local = loto_w + gap + count_w
                if usable_w <= 0:
                    pairs_per_row_local = 1
                else:
                    pairs_per_row_local = max(1, int((usable_w + gap) // (pair_width_local + gap)))
                rows_local = math.ceil(total_pairs / pairs_per_row_local) if total_pairs else 0
                stacked_count_h = count_copies * (count_h + gap)
                pair_height_local = max(loto_h, stacked_count_h)
                total_height_local = rows_local * pair_height_local + max(rows_local - 1, 0) * gap
                pairs_in_row = pairs_per_row_local if total_pairs >= pairs_per_row_local else (total_pairs or pairs_per_row_local)
                width_used = pairs_in_row * pair_width_local + max(pairs_in_row - 1, 0) * gap
                width_penalty = max(usable_w - width_used, 0.0)
                rotation_penalty = 0 if lo_rot == ct_rot else 1
                return (
                    -pairs_per_row_local,
                    width_penalty,
                    rotation_penalty,
                    total_height_local,
                    total_height_local,
                )

            option_metrics = [
                evaluate(False, False),
                evaluate(True, True),
                evaluate(True, False),
                evaluate(False, True),
            ]

            best_option = min(option_metrics, key=lambda item: item[:4])
            count_block_h = best_option[4]

            # Im Single-Modus sind die regulären Sticker bereits in count_block_h enthalten
            reg_block_h = 0.0
        elif count_mode == 'single' and count_single_items:
            ct_w = app.count_config.width_mm
            ct_h = app.count_config.height_mm
            usable_w = sheet_w_mm - 2 * margin
            ct_cols = max(1, int((usable_w + gap) // (ct_w + gap)))
            rows_ct = math.ceil(len(count_single_items) / ct_cols)
            count_block_h = rows_ct * ct_h + (rows_ct - 1) * gap
            if rows_reg:
                count_block_h += gap

        total_h = margin + header_block_h + reg_block_h + count_block_h + margin
        return math.ceil(total_h + 0.0001)
