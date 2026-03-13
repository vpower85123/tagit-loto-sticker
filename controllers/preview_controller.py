"""
Preview Controller - Verwaltet Sticker-Vorschau-Logik
"""
import logging
import math
from typing import Optional, Any
from PyQt6.QtWidgets import QWidget, QLabel
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QPixmap
from PIL import Image
from PIL.ImageQt import ImageQt
from dataclasses import replace

logger = logging.getLogger(__name__)


class PreviewController:
    """Controller für Sticker-Vorschau-Management"""
    
    def __init__(self, sticker_generator, sticker_config, parent: Any = None):
        """
        Initialisiere Preview Controller
        
        Args:
            sticker_generator: StickerGenerator-Instanz
            sticker_config: StickerConfig-Instanz
            parent: Parent Widget (StickerApp)
        """
        self.parent = parent
        self.sticker_generator = sticker_generator
        self.sticker_config = sticker_config
        
        # Timer für verzögerte Updates
        self.preview_update_timer = None
        self.preview_update_delay_ms = 180
        
        # UI-Elemente (werden nach UI-Erstellung gesetzt)
        self.preview_label: Optional[QLabel] = None
        self.scale_slider = None
        self.scale_value_label = None
        self.energy_entry = None
        self.equipment_entry = None
        self.description_entry = None
        self.symbol_combo = None
        
        logger.info("PreviewController initialisiert")
    
    def set_ui_elements(self, preview_label, scale_slider, scale_value_label,
                       energy_entry, equipment_entry, symbol_combo, description_entry=None):
        """Setze UI-Element-Referenzen nach UI-Erstellung"""
        self.preview_label = preview_label
        self.scale_slider = scale_slider
        self.scale_value_label = scale_value_label
        self.energy_entry = energy_entry
        self.equipment_entry = equipment_entry
        self.symbol_combo = symbol_combo
        self.description_entry = description_entry
        
        # Timer initialisieren
        self._ensure_preview_timer()
    
    def _ensure_preview_timer(self):
        """Stelle sicher, dass ein Preview-Timer existiert"""
        if self.preview_update_timer is None and self.parent is not None:
            try:
                self.preview_update_timer = QTimer(self.parent)
                self.preview_update_timer.setSingleShot(True)
                self.preview_update_timer.timeout.connect(self.update_preview)
            except Exception as exc:
                logger.debug(f"Preview timer creation error: {exc}")
                return None
        return self.preview_update_timer
    
    def update_preview(self):
        """Sticker-Vorschau aktualisieren"""
        try:
            # Stop laufenden Timer
            if self.preview_update_timer is not None and self.preview_update_timer.isActive():
                try:
                    self.preview_update_timer.stop()
                except Exception:
                    pass
            
            # Werte aus UI-Elementen holen
            energy_id = self.energy_entry.text().strip() if self.energy_entry else "TEST"
            equipment = self.equipment_entry.text().strip() if self.equipment_entry else "EQUIPMENT"
            description = ""
            if self.description_entry and hasattr(self.description_entry, 'text'):
                description = self.description_entry.text().strip()
            
            logger.debug(f"Preview Update: energy={energy_id}, equipment={equipment}, description={description}")
            
            # Baue Zeilen
            lines = [energy_id, equipment]
            if description:
                lines.append(description)
            
            logger.debug(f"Lines für Generator: {lines}")
            
            # Symbol-Typ ermitteln
            from core.models import SymbolType
            symbol_name = self.symbol_combo.currentText().upper() if self.symbol_combo else "ELECTRICAL"
            try:
                symbol_type = SymbolType[symbol_name]
            except (KeyError, AttributeError):
                symbol_type = SymbolType.ELECTRICAL
            
            # Temporarily boost resolution for sharp preview
            original_dpi = self.sticker_config.dpi
            original_corner_radius = getattr(self.sticker_config, 'corner_radius', 0)
            
            target_dpi = int(12.0 * 25.4)  # 12 px/mm * 25.4 mm/inch = ~305 DPI
            scale_factor = target_dpi / original_dpi if original_dpi > 0 else 1.0
            
            self.sticker_config.dpi = target_dpi
            if hasattr(self.sticker_config, 'corner_radius'):
                self.sticker_config.corner_radius = int(original_corner_radius * scale_factor)

            try:
                # Sticker generieren
                img = self.sticker_generator.generate(symbol_type, lines)
            finally:
                # Restore original resolution
                self.sticker_config.dpi = original_dpi
                if hasattr(self.sticker_config, 'corner_radius'):
                    self.sticker_config.corner_radius = original_corner_radius
            
            # PIL zu QPixmap konvertieren
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            qimage = ImageQt(img)
            pixmap = QPixmap.fromImage(qimage)
            
            # Skalieren für Vorschau
            try:
                scale = float(getattr(self.sticker_config, 'preview_scale', 1.0) or 1.0)
            except Exception:
                scale = 1.0
            if not math.isfinite(scale) or scale <= 0:
                scale = 0.1
            
            # Use original base size (400) to fit UI, but source image is now high-res
            scaled_pixmap = pixmap.scaled(
                int(400 * scale), int(300 * scale),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            
            mask_pixmap = None
            get_mask = getattr(self.sticker_generator, 'get_last_text_mask', None)
            if callable(get_mask):
                mask_image = get_mask()
            else:
                mask_image = None

            if mask_image is not None and scaled_pixmap:
                mask_rgba = Image.new("RGBA", mask_image.size, (255, 255, 255, 0))
                mask_rgba.putalpha(mask_image)
                mask_qimage = ImageQt(mask_rgba)
                mask_pixmap = QPixmap.fromImage(mask_qimage)
                mask_pixmap = mask_pixmap.scaled(
                    scaled_pixmap.width(), scaled_pixmap.height(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )

            if self.preview_label:
                self.preview_label.setPixmap(scaled_pixmap)
                if hasattr(self.preview_label, 'set_mask_pixmap'):
                    self.preview_label.set_mask_pixmap(mask_pixmap)
            
            # Count Preview aktualisieren (wenn parent verfügbar)
            if self.parent and hasattr(self.parent, 'update_collection_count_preview'):
                self.parent.update_collection_count_preview()
        
        except Exception as e:
            logger.error(f"Vorschau-Fehler: {e}")
            if self.preview_label:
                self.preview_label.setText(f"Vorschau-Fehler:\n{e}")

    def safe_update_count_preview(self):
        """Sichere Count-Vorschau-Aktualisierung (für externe Aufrufe)."""
        try:
            self.update_count_preview()
        except Exception as e:
            logger.error(f"Fehler bei safe_update_count_preview: {e}")

    def update_count_preview(self):
        """Count-Sticker-Vorschau aktualisieren."""
        from PyQt6.QtGui import QPixmap
        from PyQt6.QtCore import Qt
        from PIL.ImageQt import ImageQt

        app = self.parent
        if app is None:
            return

        try:
            # Zähle nur reguläre Items (keine COUNT-Sticker)
            regular_items = [
                it for it in app.collection
                if not (app._is_count_single(it) or app._is_count_multi(it))
            ]
            actual_count = len(regular_items)

            if actual_count == 0:
                actual_count = 1  # Mindestens 1 für Vorschau
                detail = "Beispiel Equipment"
            else:
                # Details aus Collection extrahieren - in Reihenfolge
                detail_parts = []
                for item in regular_items:
                    e_id = item[2] if len(item) > 2 else ""
                    equip = item[3] if len(item) > 3 else ""
                    if e_id and equip:
                        detail_parts.append(f"{e_id} {equip}")
                    elif e_id:
                        detail_parts.append(e_id)
                    elif equip:
                        detail_parts.append(equip)

                import re as _re_sort
                detail_parts.sort(
                    key=lambda s: [
                        int(t) if t.isdigit() else t.lower()
                        for t in _re_sort.split(r'(\d+)', s)
                    ]
                )
                detail = ", ".join(detail_parts)

            # Count-Sticker generieren
            preview_img = app.count_generator.generate(detail=detail, count=actual_count)

            # Bild zu QPixmap konvertieren
            if preview_img.mode != 'RGBA':
                preview_img = preview_img.convert('RGBA')
            qimage = ImageQt(preview_img)
            pixmap = QPixmap.fromImage(qimage)

            # Vorschau im Hauptfenster aktualisieren
            if hasattr(app, 'preview_label') and app.preview_label:
                scaled_pixmap = pixmap.scaled(
                    800,
                    600,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                app.preview_label.setPixmap(scaled_pixmap)
        except Exception as e:
            logger.error(f"Count-Vorschau-Fehler: {e}", exc_info=True)
    
    def queue_preview_update(self, delay: Optional[int] = None):
        """Starte ein verzögertes Vorschau-Update"""
        timer = self._ensure_preview_timer()
        if timer is None:
            self.update_preview()
            return
        
        if delay is None:
            delay_ms = self.preview_update_delay_ms
        else:
            delay_ms = max(0, int(delay))
        
        try:
            timer.stop()
            timer.start(delay_ms)
        except Exception as exc:
            logger.debug(f"Preview timer error: {exc}")
            self.update_preview()
    
    def on_text_changed(self, _value):
        """Debounce für Texteingaben"""
        self.queue_preview_update()
    
    def on_symbol_changed(self, _index):
        """Sofortige Vorschau nach Symbolwechsel"""
        self.queue_preview_update(0)
    
    def increase_scale(self):
        """Sticker-Skalierung erhöhen"""
        self.sticker_config.preview_scale = round(min(2.0, self.sticker_config.preview_scale + 0.1), 1)
        if self.scale_slider:
            self.scale_slider.setValue(int(self.sticker_config.preview_scale * 200))
        if self.scale_value_label:
            self.scale_value_label.setText(f"{self.sticker_config.preview_scale:.1f}")
        
        # Count-Skalierung synchron anpassen
        if self.parent and hasattr(self.parent, 'count_preview_scale'):
            self.parent.count_preview_scale = self.sticker_config.preview_scale
            if hasattr(self.parent, 'update_collection_count_preview'):
                self.parent.update_collection_count_preview()
    
    def decrease_scale(self):
        """Sticker-Skalierung verringern"""
        self.sticker_config.preview_scale = round(max(0.1, self.sticker_config.preview_scale - 0.1), 1)
        if self.scale_slider:
            self.scale_slider.setValue(int(self.sticker_config.preview_scale * 200))
        if self.scale_value_label:
            self.scale_value_label.setText(f"{self.sticker_config.preview_scale:.1f}")
        
        # Count-Skalierung synchron anpassen
        if self.parent and hasattr(self.parent, 'count_preview_scale'):
            self.parent.count_preview_scale = self.sticker_config.preview_scale
            if hasattr(self.parent, 'update_collection_count_preview'):
                self.parent.update_collection_count_preview()
    
    def update_scale_from_dial(self, dial_value):
        """Aktualisiere Skalierung vom Drehregler (High DPI: Factor 200)"""
        scale_value = dial_value / 200.0
        self.update_scale(scale_value)
        if self.scale_value_label:
            self.scale_value_label.setText(f"{scale_value:.1f}")
    
    def update_scale(self, value):
        """Sichere Aktualisierung der Sticker-Skalierung mit Validierung"""
        if value > 0:
            # Maximal 2.0 zulassen
            new_scale = min(2.0, value)
            old_scale = getattr(self.sticker_config, 'preview_scale', new_scale)
            
            # Cache leeren wenn sich Scale ändert
            if not math.isclose(new_scale, old_scale, rel_tol=1e-3):
                if self.parent and hasattr(self.parent, '_clear_collection_preview_cache'):
                    self.parent._clear_collection_preview_cache()
            
            self.sticker_config.preview_scale = new_scale
            self.update_preview()
            
            # Count-Skalierung synchron anpassen
            if self.parent and hasattr(self.parent, 'count_preview_scale'):
                self.parent.count_preview_scale = self.sticker_config.preview_scale
                if hasattr(self.parent, 'update_collection_count_preview'):
                    self.parent.update_collection_count_preview()
        else:
            # Wert zurücksetzen auf Minimum (0.1 * 200 = 20)
            if self.scale_slider:
                self.scale_slider.setValue(20)

    def apply_sticker_preset(self, preset_type: str):
        """Wendet ein Sticker-Preset an (Form)."""
        app = self.parent
        if app is None:
            return

        try:
            # Speichere aktuelle Form-Einstellungen bevor wir wechseln
            if hasattr(app, 'current_form_type') and app.current_form_type != preset_type:
                self.save_current_form_config()

            # Wenn wir bereits gespeicherte Einstellungen fuer diese Form haben, lade sie
            if hasattr(app, 'form_configs') and app.form_configs.get(preset_type) is not None:
                self.load_form_config(preset_type)
                app.current_form_type = preset_type
            else:
                # Ansonsten verwende Standard-Preset-Werte
                px_per_mm = app.sticker_config.dpi / 25.4

                if preset_type == "rectangle":
                    app.sticker_config.width_mm = 85.0
                    app.sticker_config.height_mm = 25.0
                    app.sticker_config.corner_radius = int(12.0 * px_per_mm)

                elif preset_type == "square":
                    app.sticker_config.width_mm = 85.0
                    app.sticker_config.height_mm = 85.0
                    app.sticker_config.corner_radius = int(20.0 * px_per_mm)

                elif preset_type == "circle":
                    size_mm = 70.0
                    app.sticker_config.width_mm = size_mm
                    app.sticker_config.height_mm = size_mm
                    size_px = int(size_mm * px_per_mm)
                    app.sticker_config.corner_radius = size_px // 2

                elif preset_type == "rounded":
                    app.sticker_config.width_mm = 85.0
                    app.sticker_config.height_mm = 25.0
                    app.sticker_config.corner_radius = int(5.0 * px_per_mm)

                app.current_form_type = preset_type
                self.save_current_form_config()

            # Speichere Änderungen
            app.config_manager.save(app.sticker_config, app.count_config, app.theme_config)

            # Update Generator und Preview
            from generators.sticker_generator import StickerGenerator
            app.sticker_generator = StickerGenerator(app.sticker_config)
            self.sticker_generator = app.sticker_generator
            self.update_preview()

            if getattr(app, 'status_bar', None):
                app.status_bar.showMessage(f"Preset '{preset_type}' angewendet", 2000)

        except Exception as e:
            logger.error(f"Fehler beim Anwenden des Presets: {e}", exc_info=True)
            if hasattr(app, '_create_styled_msgbox'):
                msg = app._create_styled_msgbox(
                    "Fehler",
                    f"Preset konnte nicht angewendet werden: {e}",
                )
                msg.exec()

    def save_current_form_config(self):
        """Speichert die aktuellen Sticker-Einstellungen fuer die aktuelle Form."""
        app = self.parent
        if app is None:
            return

        if not hasattr(app, 'current_form_type') or not hasattr(app, 'form_configs'):
            return

        app.form_configs[app.current_form_type] = replace(app.sticker_config)

    def load_form_config(self, form_type: str):
        """Laedt die gespeicherten Einstellungen fuer eine Form."""
        app = self.parent
        if app is None:
            return

        if not hasattr(app, 'form_configs') or form_type not in app.form_configs:
            return

        saved_config = app.form_configs[form_type]
        if saved_config is None:
            return

        app.sticker_config.width_mm = saved_config.width_mm
        app.sticker_config.height_mm = saved_config.height_mm
        app.sticker_config.corner_radius = saved_config.corner_radius
        app.sticker_config.dpi = saved_config.dpi
        app.sticker_config.outline_width = saved_config.outline_width
        app.sticker_config.font_size_mm = saved_config.font_size_mm
        app.sticker_config.line_height_mm = saved_config.line_height_mm
        app.sticker_config.symbol_size_mm = saved_config.symbol_size_mm
        app.sticker_config.symbol_corner_radius = saved_config.symbol_corner_radius
        app.sticker_config.sticker_color = saved_config.sticker_color
        app.sticker_config.font_path = saved_config.font_path
