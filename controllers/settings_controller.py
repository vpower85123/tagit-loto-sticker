"""
Settings Controller - Verwaltet Dialog- und Konfigurations-Management
"""
import logging
from typing import Optional, Any
from PyQt6.QtWidgets import QWidget, QDialog, QMessageBox

logger = logging.getLogger(__name__)


class SettingsController:
    """Controller für Settings-Dialogs und Konfiguration"""
    
    def __init__(self, config_manager, parent: Any = None):
        """
        Initialisiere Settings Controller
        
        Args:
            config_manager: ConfigManager-Instanz
            parent: Parent Widget (StickerApp)
        """
        self.parent = parent
        self.config_manager = config_manager
        
        logger.info("SettingsController initialisiert")
    
    def open_sticker_settings(self):
        """Sticker-Einstellungen öffnen"""
        try:
            from dialogs.sticker_settings_dialog import StickerSettingsDialog
            from generators.sticker_generator import StickerGenerator
            
            if not self.parent:
                return
            
            sticker_config = getattr(self.parent, 'sticker_config', None)
            if not sticker_config:
                logger.warning("Sticker-Config nicht gefunden")
                return
            
            # Vor dem Öffnen des Dialogs: Speichere aktuelle Form-Config
            if hasattr(self.parent, '_save_current_form_config'):
                self.parent._save_current_form_config()
            
            dialog = StickerSettingsDialog(self.parent, sticker_config)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Nach dem Dialog: Aktualisiere die gespeicherte Form-Config mit den neuen Werten
                if hasattr(self.parent, '_save_current_form_config'):
                    self.parent._save_current_form_config()
                
                # Speichere die Änderungen
                self.config_manager.save_sticker(sticker_config)
                
                # Generator neu initialisieren (auf Parent)
                if hasattr(self.parent, 'sticker_generator'):
                    self.parent.sticker_generator = StickerGenerator(sticker_config)
                
                # Update Preview Controller generator reference
                if hasattr(self.parent, 'preview_controller') and hasattr(self.parent, 'sticker_generator'):
                    self.parent.preview_controller.sticker_generator = self.parent.sticker_generator

                # Vorschau aktualisieren
                if hasattr(self.parent, 'update_sticker_preview'):
                    self.parent.update_sticker_preview()
                
                # Einstellungen in Equipment-Manager zurückschreiben
                if hasattr(self.parent, '_sync_settings_to_equipment_manager'):
                    self.parent._sync_settings_to_equipment_manager()
                
                logger.info("Sticker-Einstellungen aktualisiert")
                
        except Exception as e:
            logger.error(f"Fehler bei Sticker-Einstellungen: {e}")
            QMessageBox.warning(
                self.parent if self.parent else None,
                "Fehler",
                "Einstellungen konnten nicht geöffnet werden"
            )
    
    def open_count_settings(self):
        """Count-Einstellungen öffnen"""
        try:
            from dialogs.count_settings_dialog import CountSettingsDialog
            from generators.count_manager import CountStickerGenerator
            
            if not self.parent:
                return
            
            count_config = getattr(self.parent, 'count_config', None)
            if not count_config:
                logger.warning("Count-Config nicht gefunden")
                return
            
            dialog = CountSettingsDialog(self.parent, count_config)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Speichere die Änderungen
                self.config_manager.save_count(count_config)
                
                # Generator neu initialisieren (auf Parent)
                if hasattr(self.parent, 'count_generator'):
                    self.parent.count_generator = CountStickerGenerator(count_config)
                
                # Regeneriere Count-Sticker in der Sammlung
                if hasattr(self.parent, 'current_loto_mode') and self.parent.current_loto_mode == 'multi':
                    if hasattr(self.parent, '_regenerate_multi_count_sticker'):
                        self.parent._regenerate_multi_count_sticker()
                
                # Einstellungen in Equipment-Manager zurückschreiben
                if hasattr(self.parent, '_sync_settings_to_equipment_manager'):
                    self.parent._sync_settings_to_equipment_manager()
                
                logger.info("Count-Einstellungen aktualisiert")
                
        except Exception as e:
            logger.error(f"Fehler bei Count-Einstellungen: {e}")
            QMessageBox.warning(
                self.parent if self.parent else None,
                "Fehler",
                "Einstellungen konnten nicht geöffnet werden"
            )
    
    def save_and_update_sticker(self):
        """Konfiguration speichern und Sticker-Generator neu initialisieren"""
        try:
            from generators.sticker_generator import StickerGenerator
            
            if not self.parent:
                return
            
            sticker_config = getattr(self.parent, 'sticker_config', None)
            if sticker_config and hasattr(self.parent, 'sticker_generator'):
                # Generator mit neuer Konfiguration neu initialisieren
                self.parent.sticker_generator = StickerGenerator(sticker_config)
            
            # Speichere Configs
            if hasattr(self.parent, 'save_configs'):
                self.parent.save_configs()
            
            # Sicheres Update der Vorschau
            if hasattr(self.parent, 'safe_update_sticker_preview'):
                self.parent.safe_update_sticker_preview()
                
        except Exception as e:
            logger.error(f"Fehler beim Speichern und Aktualisieren: {e}")
    
    def save_and_update_count(self):
        """Konfiguration speichern und Count-Generator neu initialisieren"""
        try:
            from generators.count_manager import CountStickerGenerator
            
            if not self.parent:
                return
            
            count_config = getattr(self.parent, 'count_config', None)
            if count_config and hasattr(self.parent, 'count_generator'):
                # Generator mit neuer Konfiguration neu initialisieren
                self.parent.count_generator = CountStickerGenerator(count_config)
            
            # Speichere Configs
            if hasattr(self.parent, 'save_configs'):
                self.parent.save_configs()
            
            # Sicheres Update der Vorschau
            if hasattr(self.parent, 'safe_update_count_preview'):
                self.parent.safe_update_count_preview()
            
            # Collection Count Preview auch aktualisieren
            if hasattr(self.parent, 'update_collection_count_preview'):
                self.parent.update_collection_count_preview()
                
        except Exception as e:
            logger.error(f"Fehler beim Speichern und Aktualisieren: {e}")

    def on_loto_mode_changed(self, mode_or_bool):
        """Synchronisiert LOTO-Modus mit Export-Konfiguration und Legacy-State."""
        if not self.parent:
            return

        # Rückwärtskompatibilität: Boolean zu String konvertieren
        if isinstance(mode_or_bool, bool):
            mode = 'multi' if mode_or_bool else 'single'
        else:
            mode = mode_or_bool  # 'single', 'multi', oder 'none'

        self.parent.current_loto_mode = mode

        # Legacy-StringVar-ähnliches Objekt bedienen/fallbacken
        if getattr(self.parent, 'count_mode', None):
            try:
                self.parent.count_mode.set(mode)
            except Exception:
                class _CountModeFallback:
                    def __init__(self, value: str):
                        self._value = value

                    def get(self) -> str:
                        return self._value

                    def set(self, value: str) -> None:
                        self._value = value

                self.parent.count_mode = _CountModeFallback(mode)
        else:
            class _CountModeFallback:
                def __init__(self, value: str):
                    self._value = value

                def get(self) -> str:
                    return self._value

                def set(self, value: str) -> None:
                    self._value = value

            self.parent.count_mode = _CountModeFallback(mode)

        if getattr(self.parent, 'export_config', None):
            self.parent.export_config.export_mode = mode
            try:
                self.config_manager.save_export(self.parent.export_config)
                logger.info(f"LOTO Modus gespeichert: {mode}")
            except Exception as exc:
                logger.warning(f"Export-Config konnte nicht gespeichert werden (LOTO Modus): {exc}")
