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
