"""
Equipment Service
Wrapper um EquipmentManager mit Suchfunktionalität
"""

import logging
from typing import List, Dict
from PyQt6.QtCore import QObject, pyqtSignal
from pathlib import Path

from managers.equipment_manager import EquipmentManager

logger = logging.getLogger(__name__)


class EquipmentService(QObject):
    """Service für Equipment-Management mit Suche und Caching"""
    
    # Signals
    equipment_changed = pyqtSignal()  # Equipment-Daten haben sich geändert
    equipment_saved = pyqtSignal()  # Equipment wurde gespeichert
    
    def __init__(self, equipment_path: Path):
        super().__init__()
        self.equipment_manager = EquipmentManager(str(equipment_path))
        self._search_cache: Dict[str, List[Dict[str, str]]] = {}
    
    def get_manager(self) -> EquipmentManager:
        """Gibt den EquipmentManager zurück (für direkten Zugriff)"""
        return self.equipment_manager
    
    def save(self) -> bool:
        """
        Speichert Equipment-Daten
        
        Returns:
            True wenn erfolgreich
        """
        try:
            self.equipment_manager.save()
            self.equipment_saved.emit()
            self.clear_search_cache()
            return True
        except Exception as e:
            logger.error(f"Fehler beim Speichern: {e}")
            return False
    
    def search(self, query: str) -> List[Dict[str, str]]:
        """
        Sucht in Equipment-Daten (Location, System, Equipment Namen)
        
        Args:
            query: Suchbegriff
            
        Returns:
            Liste von Treffern mit Typ, Name und Pfad
            [{
                'type': 'location'|'system'|'equipment',
                'name': 'Item-Name',
                'path': 'Vollständiger Pfad',
                'location': 'Location-Name',
                'system': 'System-Name' (bei equipment)
            }]
        """
        if not query or len(query) < 2:
            return []
        
        # Cache prüfen
        if query in self._search_cache:
            return self._search_cache[query]
        
        results = []
        query_lower = query.lower()
        
        # Durchsuche alle Locations
        for location_name in self.equipment_manager.get_all_locations():
            location_data = self.equipment_manager.equipment_data.get(location_name, {})
            
            # Location-Match
            if query_lower in location_name.lower():
                results.append({
                    'type': 'location',
                    'name': location_name,
                    'path': location_name,
                    'location': location_name
                })
            
            # Durchsuche Systeme
            for system in location_data.get('systems', []):
                system_name = system.get('name', '')
                
                # System-Match
                if query_lower in system_name.lower():
                    results.append({
                        'type': 'system',
                        'name': system_name,
                        'path': f"{location_name} → {system_name}",
                        'location': location_name,
                        'system': system_name
                    })
                
                # Durchsuche Equipment
                for equipment in system.get('equipment', []):
                    equipment_name = equipment.get('name', '')
                    
                    # Equipment-Match
                    if query_lower in equipment_name.lower():
                        results.append({
                            'type': 'equipment',
                            'name': equipment_name,
                            'path': f"{location_name} → {system_name} → {equipment_name}",
                            'location': location_name,
                            'system': system_name
                        })
        
        # Cache speichern
        self._search_cache[query] = results
        return results
    
    def clear_search_cache(self):
        """Leert den Such-Cache"""
        self._search_cache.clear()
    
    def get_statistics(self) -> Dict[str, int]:
        """
        Gibt Statistiken zurück
        
        Returns:
            Dict mit Anzahl Locations, Systems, Equipment
        """
        locations = self.equipment_manager.get_all_locations()
        total_systems = 0
        total_equipment = 0
        
        for location_name in locations:
            location_data = self.equipment_manager.equipment_data.get(location_name, {})
            systems = location_data.get('systems', [])
            total_systems += len(systems)
            
            for system in systems:
                total_equipment += len(system.get('equipment', []))
        
        return {
            'locations': len(locations),
            'systems': total_systems,
            'equipment': total_equipment
        }
