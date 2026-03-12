# equipment_manager_new.py
"""
Equipment Manager mit 3-stufiger Hierarchie:
Standort → System → Betriebsmittel

Neue Datenstruktur:
{
  "STANDORT_NAME": {
    "systems": [
      {
        "name": "SYSTEM_NAME",
        "equipment": [
          {
            "name": "BETRIEBSMITTEL_NAME",
            "energy_id": "E001",
            "symbol_type": "ELECTRICAL"
          }
        ]
      }
    ]
  }
}
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)


class EquipmentManager:
    """Verwaltet Equipment-Daten mit Hierarchie: Standort → System → Betriebsmittel"""

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.equipment_data: Dict[str, Any] = self._load_equipment()
        logger.info(f"EquipmentManager initialisiert. Datenpfad: {self.file_path}")

    def _load_equipment(self) -> Dict[str, Any]:
        """Lädt Equipment-Daten aus der JSON-Datei."""
        if not self.file_path.exists():
            logger.warning(f"Datei nicht gefunden: {self.file_path}. Erstelle leere Daten.")
            return {}
        
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    logger.error(f"Ungültiges Format in {self.file_path}")
                    return {}
                return data
        except json.JSONDecodeError as e:
            logger.error(f"JSON-Fehler in {self.file_path}: {e}")
            return {}
        except Exception as e:
            logger.error(f"Fehler beim Laden von {self.file_path}: {e}")
            return {}

    def save_equipment(self) -> bool:
        """Speichert die Equipment-Daten."""
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.equipment_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Daten gespeichert: {self.file_path}")
            return True
        except Exception as e:
            logger.error(f"Fehler beim Speichern: {e}")
            return False

    def save(self):
        """Alias für save_equipment()"""
        self.save_equipment()

    # ========== STANDORT (Location) ==========
    
    def get_all_locations(self) -> List[str]:
        """Gibt alle Standortnamen zurück."""
        return sorted(self.equipment_data.keys())

    def add_location(self, location_name: str) -> bool:
        """Fügt einen neuen Standort hinzu."""
        location_name = location_name.strip().upper()
        if not location_name:
            return False
        
        if location_name in self.equipment_data:
            logger.warning(f"Standort '{location_name}' existiert bereits")
            return False
        
        self.equipment_data[location_name] = {"systems": []}
        logger.info(f"Standort '{location_name}' hinzugefügt")
        return True

    def remove_location(self, location_name: str) -> bool:
        """Entfernt einen Standort."""
        if location_name not in self.equipment_data:
            return False
        
        del self.equipment_data[location_name]
        logger.info(f"Standort '{location_name}' entfernt")
        return True

    def rename_location(self, old_name: str, new_name: str) -> bool:
        """Benennt einen Standort um."""
        new_name = new_name.strip().upper()
        if not new_name or old_name not in self.equipment_data:
            return False
        
        if new_name in self.equipment_data and new_name != old_name:
            logger.warning(f"Standort '{new_name}' existiert bereits")
            return False
        
        self.equipment_data[new_name] = self.equipment_data.pop(old_name)
        logger.info(f"Standort umbenannt: '{old_name}' → '{new_name}'")
        return True

    # ========== SYSTEM ==========
    
    def get_systems(self, location_name: str) -> List[Dict[str, Any]]:
        """Gibt alle Systeme eines Standorts zurück."""
        if location_name not in self.equipment_data:
            return []
        return self.equipment_data[location_name].get("systems", [])

    def get_system_names(self, location_name: str) -> List[str]:
        """Gibt Namen aller Systeme eines Standorts zurück."""
        systems = self.get_systems(location_name)
        return [s["name"] for s in systems if isinstance(s, dict) and "name" in s]

    def add_system(self, location_name: str, system_name: str, symbol_type: str = "") -> bool:
        """Fügt ein System zu einem Standort hinzu."""
        system_name = system_name.strip().upper()
        symbol_type = symbol_type.strip().upper()
        if not system_name or location_name not in self.equipment_data:
            return False
        
        systems = self.equipment_data[location_name].get("systems", [])
        
        # Prüfe ob System bereits existiert
        if any(s.get("name") == system_name for s in systems):
            logger.warning(f"System '{system_name}' existiert bereits in '{location_name}'")
            return False
        
        systems.append({
            "name": system_name,
            "symbol_type": symbol_type,
            "equipment": []
        })
        self.equipment_data[location_name]["systems"] = systems
        logger.info(f"System '{system_name}' zu '{location_name}' hinzugefügt")
        return True

    def remove_system(self, location_name: str, system_name: str) -> bool:
        """Entfernt ein System."""
        if location_name not in self.equipment_data:
            return False
        
        system_name = system_name.strip().upper()
        systems = self.equipment_data[location_name].get("systems", [])
        systems[:] = [s for s in systems if s.get("name") != system_name]
        self.equipment_data[location_name]["systems"] = systems
        logger.info(f"System '{system_name}' aus '{location_name}' entfernt")
        return True

    def rename_system(self, location_name: str, old_name: str, new_name: str) -> bool:
        """Benennt ein System um."""
        new_name = new_name.strip().upper()
        old_name = old_name.strip().upper()
        if not new_name or location_name not in self.equipment_data:
            return False
        
        systems = self.equipment_data[location_name].get("systems", [])
        
        # Prüfe ob neuer Name bereits existiert
        if any(s.get("name") == new_name for s in systems if s.get("name") != old_name):
            logger.warning(f"System '{new_name}' existiert bereits")
            return False
        
        for system in systems:
            if system.get("name") == old_name:
                system["name"] = new_name
                logger.info(f"System umbenannt: '{old_name}' → '{new_name}'")
                return True
        
        return False

    def update_system_properties(self, location_name: str, system_name: str,
                                 symbol_type: Optional[str] = None,
                                 qr_path: Optional[str] = None) -> bool:
        """Aktualisiert Eigenschaften eines Systems (z.B. Symbol-Typ, QR-Code)."""
        if location_name not in self.equipment_data:
            return False

        system_name = system_name.strip().upper()
        systems = self.equipment_data[location_name].get("systems", [])
        for system in systems:
            if system.get("name") == system_name:
                if symbol_type is not None:
                    system["symbol_type"] = symbol_type.strip().upper()
                if qr_path is not None:
                    system["qr_path"] = qr_path.strip()
                return True
        return False

    def get_system(self, location_name: str, system_name: str) -> Optional[Dict[str, Any]]:
        """Gibt ein spezifisches System zurück."""
        if location_name not in self.equipment_data:
            return None
        
        system_name = system_name.strip().upper()
        systems = self.equipment_data[location_name].get("systems", [])
        for system in systems:
            if system.get("name") == system_name:
                return system
        return None

    # ========== BETRIEBSMITTEL (Equipment) ==========
    
    def get_equipment(self, location_name: str, system_name: str) -> List[Dict[str, Any]]:
        """Gibt alle Betriebsmittel eines Systems zurück."""
        system = self.get_system(location_name, system_name)
        if not system:
            return []
        return system.get("equipment", [])

    def get_equipment_names(self, location_name: str, system_name: str) -> List[str]:
        """Gibt Namen aller Betriebsmittel eines Systems zurück."""
        equipment = self.get_equipment(location_name, system_name)
        return [e["name"] for e in equipment if isinstance(e, dict) and "name" in e]

    def add_equipment(self, location_name: str, system_name: str, equipment_name: str,
                     energy_id: str = "", symbol_type: str = "", description: str = "", qr_path: str = "", sticker_config: dict = None) -> bool:
        """Fügt ein Betriebsmittel zu einem System hinzu."""
        equipment_name = equipment_name.strip().upper()
        energy_id = energy_id.strip().upper()
        symbol_type = symbol_type.strip().upper()
        description = description.strip()
        qr_path = qr_path.strip() if qr_path else ""
        
        logger.info(f"DEBUG add_equipment: name={equipment_name}, qr_path={qr_path}")
        
        if not equipment_name:
            return False
        
        system = self.get_system(location_name, system_name)
        if not system:
            return False
        
        equipment_list = system.get("equipment", [])
        
        # Prüfe ob Betriebsmittel mit gleichem Namen UND gleicher Energy-ID bereits existiert
        # (Gleicher Name mit unterschiedlicher Energy-ID ist erlaubt!)
        if any(e.get("name") == equipment_name and e.get("energy_id", "").upper() == energy_id for e in equipment_list):
            logger.warning(f"Betriebsmittel '{equipment_name}' mit Energy-ID '{energy_id}' existiert bereits")
            return False
        
        equipment_data = {
            "name": equipment_name,
            "energy_id": energy_id,
            "symbol_type": symbol_type,
            "description": description,
            "qr_path": qr_path
        }
        
        if sticker_config:
            equipment_data["sticker_config"] = sticker_config
        
        equipment_list.append(equipment_data)
        
        system["equipment"] = equipment_list
        logger.info(f"Betriebsmittel '{equipment_name}' zu System '{system_name}' hinzugefügt")
        return True

    def remove_equipment(self, location_name: str, system_name: str, equipment_name: str) -> bool:
        """Entfernt ein Betriebsmittel."""
        system = self.get_system(location_name, system_name)
        if not system:
            return False
        
        equipment_list = system.get("equipment", [])
        equipment_list[:] = [e for e in equipment_list if e.get("name") != equipment_name]
        system["equipment"] = equipment_list
        logger.info(f"Betriebsmittel '{equipment_name}' entfernt")
        return True

    def rename_equipment(self, location_name: str, system_name: str, 
                        old_name: str, new_name: str) -> bool:
        """Benennt ein Betriebsmittel um."""
        new_name = new_name.strip().upper()
        if not new_name:
            return False
        
        system = self.get_system(location_name, system_name)
        if not system:
            return False
        
        equipment_list = system.get("equipment", [])
        
        # Prüfe ob neuer Name bereits existiert
        if any(e.get("name") == new_name for e in equipment_list if e.get("name") != old_name):
            logger.warning(f"Betriebsmittel '{new_name}' existiert bereits")
            return False
        
        for equipment in equipment_list:
            if equipment.get("name") == old_name:
                equipment["name"] = new_name
                logger.info(f"Betriebsmittel umbenannt: '{old_name}' → '{new_name}'")
                return True
        
        return False

    def update_equipment_properties(self, location_name: str, system_name: str,
                                   equipment_name: str, energy_id: Optional[str] = None,
                                   symbol_type: Optional[str] = None,
                                   description: Optional[str] = None,
                                   qr_path: Optional[str] = None,
                                   sticker_config: Optional[dict] = None,
                                   match_energy_id: Optional[str] = None) -> bool:
        """Aktualisiert die Eigenschaften eines Betriebsmittels.
        
        Args:
            match_energy_id: Wenn gesetzt, wird nach Name UND dieser Energy-ID gesucht.
        """
        system = self.get_system(location_name, system_name)
        if not system:
            return False
        
        equipment_list = system.get("equipment", [])
        
        for equipment in equipment_list:
            name_match = equipment.get("name") == equipment_name
            if match_energy_id is not None:
                energy_match = equipment.get("energy_id", "").upper() == match_energy_id.upper()
                if not (name_match and energy_match):
                    continue
            elif not name_match:
                continue
            
            if energy_id is not None:
                equipment["energy_id"] = energy_id.strip().upper()
            if symbol_type is not None:
                equipment["symbol_type"] = symbol_type.strip().upper()
            if description is not None:
                equipment["description"] = description.strip()
            if qr_path is not None:
                equipment["qr_path"] = qr_path.strip() if qr_path else ""
            if sticker_config is not None:
                equipment["sticker_config"] = sticker_config
            logger.info(f"Betriebsmittel '{equipment_name}' aktualisiert")
            return True
        
        return False

    def get_equipment_properties(self, location_name: str, system_name: str,
                                equipment_name: str, energy_id: Optional[str] = None) -> Optional[Dict[str, str]]:
        """Gibt die Eigenschaften eines Betriebsmittels zurück.
        
        Args:
            energy_id: Wenn gesetzt, wird nach Name UND dieser Energy-ID gesucht.
        """
        equipment_list = self.get_equipment(location_name, system_name)
        
        for equipment in equipment_list:
            name_match = equipment.get("name") == equipment_name
            if energy_id is not None:
                energy_match = equipment.get("energy_id", "").upper() == energy_id.upper()
                if not (name_match and energy_match):
                    continue
            elif not name_match:
                continue
                
            return {
                "name": equipment.get("name", ""),
                "energy_id": equipment.get("energy_id", ""),
                "symbol_type": equipment.get("symbol_type", ""),
                "description": equipment.get("description", "")
            }
        
        return None

    # ========== LEGACY COMPATIBILITY ==========
    # Diese Methoden für Rückwärtskompatibilität mit alter 2-stufiger Struktur
    
    def get_equipment_by_location(self, location_name: str) -> List[str]:
        """LEGACY: Gibt alle Systemnamen eines Standorts zurück."""
        return self.get_system_names(location_name)

    def edit_equipment(self, location_name: str, old_name: str, new_name: str) -> bool:
        """LEGACY: Benennt ein System um."""
        return self.rename_system(location_name, old_name, new_name)
    
    def remove_subcategory(self, location_or_system: str, subcategory_name: str) -> bool:
        """LEGACY: Entfernt ein Betriebsmittel (interpretiert als System → Equipment)."""
        # Diese Methode kann nicht einfach konvertiert werden ohne Kontext
        # Daher als Stub für Migration
        logger.warning("remove_subcategory() ist veraltet - verwenden Sie remove_equipment()")
        return False
