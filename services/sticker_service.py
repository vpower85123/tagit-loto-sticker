"""
Sticker Service
Verwaltet Sticker-Generierung und Konfiguration
"""

from typing import Optional, Tuple
from PIL import Image
from PyQt6.QtCore import QObject, pyqtSignal

from generators.sticker_generator import StickerGenerator
from core.models import StickerConfig, SymbolType


class StickerService(QObject):
    """Service für Sticker-Generierung und Verwaltung"""
    
    # Signals
    sticker_generated = pyqtSignal(object)  # PIL Image
    config_changed = pyqtSignal(object)  # StickerConfig
    generation_error = pyqtSignal(str)  # Error message
    
    def __init__(self, initial_config: StickerConfig):
        super().__init__()
        self.config = initial_config
        self.generator = StickerGenerator(self.config)
    
    def update_config(self, config: StickerConfig):
        """Update Sticker-Konfiguration"""
        self.config = config
        self.generator = StickerGenerator(self.config)
        self.config_changed.emit(self.config)
    
    def generate_sticker(
        self, 
        energy_id: str, 
        equipment: str, 
        symbol_name: str,
        description: str = ""
    ) -> Optional[Image.Image]:
        """
        Generiert einen einzelnen Sticker
        
        Returns:
            PIL Image oder None bei Fehler
        """
        try:
            # Symbol-Typ ermitteln
            symbol_type = self._get_symbol_type(symbol_name)
            
            # Zeilen zusammenstellen
            lines = [energy_id, equipment]
            if description:
                lines.append(description)
            
            # Sticker generieren
            img = self.generator.generate(symbol_type, lines)
            
            self.sticker_generated.emit(img)
            return img
            
        except Exception as e:
            error_msg = f"Fehler bei Sticker-Generierung: {str(e)}"
            self.generation_error.emit(error_msg)
            return None
    
    def generate_preview(
        self,
        energy_id: str,
        equipment: str,
        symbol_name: str,
        description: str = ""
    ) -> Optional[Image.Image]:
        """
        Generiert eine Vorschau (identisch mit generate_sticker, 
        aber für semantische Klarheit getrennt)
        """
        return self.generate_sticker(energy_id, equipment, symbol_name, description)
    
    def _get_symbol_type(self, symbol_name: str) -> SymbolType:
        """Konvertiert Symbol-Name zu SymbolType Enum"""
        # Mapping für Abwärtskompatibilität und UI-Namen
        symbol_map = {
            'ELECTRIC': SymbolType.ELECTRICAL,
            'ELECTRICAL': SymbolType.ELECTRICAL,
            'MECHANIC': SymbolType.MECHANICAL,
            'MECHANICAL': SymbolType.MECHANICAL,
            'HYDRAULIC': SymbolType.HYDRAULIC,
            'PNEUMATIC': SymbolType.PNEUMATIC,
            'GAS': SymbolType.STEAM,  # Fallback/Mapping
            'STEAM': SymbolType.STEAM,
            'WATER': SymbolType.HYDRAULIC,  # Fallback
            'THERMAL': SymbolType.THERMAL,
            'CHEMICAL': SymbolType.CHEMICAL,
            'GRAVITATIONAL': SymbolType.GRAVITATIONAL,
            'KINETIC': SymbolType.KINETIC,
            # Alte Typen auf generische mappen falls nötig
            'RADIATION': SymbolType.ELECTRICAL,  # Fallback
            'BIOHAZARD': SymbolType.CHEMICAL,    # Fallback
            'MAIN SWITCH': SymbolType.ELECTRICAL # Fallback
        }
        return symbol_map.get(symbol_name.upper(), SymbolType.ELECTRICAL)
    
    def get_available_symbols(self) -> list[str]:
        """Gibt Liste verfügbarer Symbol-Namen zurück"""
        return SymbolType.names()
    
    def validate_input(self, energy_id: str, equipment: str) -> Tuple[bool, str]:
        """
        Validiert Eingabedaten
        
        Returns:
            (is_valid, error_message)
        """
        if not energy_id or not energy_id.strip():
            return False, "Energie-ID darf nicht leer sein"
        
        if not equipment or not equipment.strip():
            return False, "Equipment darf nicht leer sein"
        
        if len(energy_id) > 50:
            return False, "Energie-ID zu lang (max. 50 Zeichen)"
        
        if len(equipment) > 100:
            return False, "Equipment-Name zu lang (max. 100 Zeichen)"
        
        return True, ""
    
    def get_config(self) -> StickerConfig:
        """Gibt aktuelle Konfiguration zurück"""
        return self.config
