"""
Collection Service
Verwaltet die Sticker-Collection (Liste der generierten Sticker)
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from PIL import Image
from PyQt6.QtCore import QObject, pyqtSignal
import json
from pathlib import Path


@dataclass
class CollectionItem:
    """Ein Item in der Collection"""
    energy_id: str
    equipment: str
    symbol_type: str
    description: str
    image: Optional[Image.Image] = None
    thumbnail: Optional[Image.Image] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dictionary (ohne Bilder)"""
        return {
            'energy_id': self.energy_id,
            'equipment': self.equipment,
            'symbol_type': self.symbol_type,
            'description': self.description
        }


class CollectionService(QObject):
    """Service für Collection-Management"""
    
    # Signals
    collection_changed = pyqtSignal()  # Collection wurde geändert
    item_added = pyqtSignal(int)  # Index des neuen Items
    item_removed = pyqtSignal(int)  # Index des entfernten Items
    item_moved = pyqtSignal(int, int)  # old_index, new_index
    collection_cleared = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self._items: List[CollectionItem] = []
    
    def add_item(
        self,
        energy_id: str,
        equipment: str,
        symbol_type: str,
        description: str,
        image: Optional[Image.Image] = None,
        thumbnail: Optional[Image.Image] = None
    ) -> int:
        """
        Fügt Item zur Collection hinzu
        
        Returns:
            Index des neuen Items
        """
        item = CollectionItem(
            energy_id=energy_id,
            equipment=equipment,
            symbol_type=symbol_type,
            description=description,
            image=image,
            thumbnail=thumbnail
        )
        
        self._items.append(item)
        index = len(self._items) - 1
        
        self.item_added.emit(index)
        self.collection_changed.emit()
        
        return index
    
    def remove_item(self, index: int) -> bool:
        """
        Entfernt Item an Index
        
        Returns:
            True wenn erfolgreich
        """
        if 0 <= index < len(self._items):
            self._items.pop(index)
            self.item_removed.emit(index)
            self.collection_changed.emit()
            return True
        return False
    
    def remove_items(self, indices: List[int]) -> int:
        """
        Entfernt mehrere Items
        
        Returns:
            Anzahl entfernter Items
        """
        # Sortiere Indizes absteigend, damit das Entfernen korrekt funktioniert
        for index in sorted(indices, reverse=True):
            if 0 <= index < len(self._items):
                self._items.pop(index)
        
        self.collection_changed.emit()
        return len(indices)
    
    def move_item(self, from_index: int, to_index: int) -> bool:
        """
        Verschiebt Item von from_index nach to_index
        
        Returns:
            True wenn erfolgreich
        """
        if (0 <= from_index < len(self._items) and 
            0 <= to_index < len(self._items)):
            
            item = self._items.pop(from_index)
            self._items.insert(to_index, item)
            
            self.item_moved.emit(from_index, to_index)
            self.collection_changed.emit()
            return True
        return False
    
    def move_item_up(self, index: int) -> bool:
        """Verschiebt Item eine Position nach oben"""
        if index > 0:
            return self.move_item(index, index - 1)
        return False
    
    def move_item_down(self, index: int) -> bool:
        """Verschiebt Item eine Position nach unten"""
        if index < len(self._items) - 1:
            return self.move_item(index, index + 1)
        return False
    
    def clear(self):
        """Leert die gesamte Collection"""
        self._items.clear()
        self.collection_cleared.emit()
        self.collection_changed.emit()
    
    def sort_by_energy_id(self):
        """Sortiert Collection nach Energie-ID numerisch"""
        import re
        
        def energy_id_sort_key(item):
            energy_id = item.energy_id
            if not energy_id:
                return (float('inf'), "")
            
            # Versuche Nummer nach E zu extrahieren
            match = re.match(r'E(\d+)', energy_id.upper())
            if match:
                return (int(match.group(1)), energy_id)
            else:
                # Keine Nummer gefunden, alphabetisch sortieren
                return (float('inf'), energy_id)
        
        self._items.sort(key=energy_id_sort_key)
        self.collection_changed.emit()
    
    def sort_by_equipment(self):
        """Sortiert Collection nach Equipment-Name"""
        self._items.sort(key=lambda x: x.equipment)
        self.collection_changed.emit()
    
    def get_item(self, index: int) -> Optional[CollectionItem]:
        """Gibt Item an Index zurück"""
        if 0 <= index < len(self._items):
            return self._items[index]
        return None
    
    def get_all_items(self) -> List[CollectionItem]:
        """Gibt alle Items zurück"""
        return self._items.copy()
    
    def get_count(self) -> int:
        """Gibt Anzahl der Items zurück"""
        return len(self._items)
    
    def is_empty(self) -> bool:
        """Prüft ob Collection leer ist"""
        return len(self._items) == 0
    
    def search(self, query: str) -> List[int]:
        """
        Sucht in Collection
        
        Returns:
            Liste der Indizes, die zum Query passen
        """
        query_lower = query.lower()
        results = []
        
        for i, item in enumerate(self._items):
            if (query_lower in item.energy_id.lower() or
                query_lower in item.equipment.lower() or
                query_lower in item.description.lower()):
                results.append(i)
        
        return results
    
    def save_to_file(self, filepath: Path) -> bool:
        """
        Speichert Collection-Metadaten in JSON-Datei
        (ohne Bilder)
        
        Returns:
            True wenn erfolgreich
        """
        try:
            data = [item.to_dict() for item in self._items]
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Fehler beim Speichern: {e}")
            return False
    
    def load_from_file(self, filepath: Path) -> bool:
        """
        Lädt Collection-Metadaten aus JSON-Datei
        
        Returns:
            True wenn erfolgreich
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self._items.clear()
            for item_data in data:
                self.add_item(
                    energy_id=item_data.get('energy_id', ''),
                    equipment=item_data.get('equipment', ''),
                    symbol_type=item_data.get('symbol_type', 'ELECTRIC'),
                    description=item_data.get('description', '')
                )
            
            return True
        except Exception as e:
            print(f"Fehler beim Laden: {e}")
            return False
    
    def duplicate_item(self, index: int) -> Optional[int]:
        """
        Dupliziert Item an Index
        
        Returns:
            Index des neuen Items oder None
        """
        item = self.get_item(index)
        if item:
            return self.add_item(
                energy_id=item.energy_id,
                equipment=item.equipment,
                symbol_type=item.symbol_type,
                description=item.description,
                image=item.image.copy() if item.image else None,
                thumbnail=item.thumbnail.copy() if item.thumbnail else None
            )
        return None
