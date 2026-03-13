"""
Equipment Controller
Verwaltet alle Equipment-Tree Operationen und UI-Logik
"""

from typing import Optional, List, Dict, Any, TYPE_CHECKING
from PyQt6.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QInputDialog, QMenu,
    QMessageBox, QLabel, QProgressDialog, QDialog, QFileDialog
)
from PyQt6.QtCore import QObject, pyqtSignal, Qt, QTimer, QPoint, QCoreApplication
from PyQt6.QtGui import QAction, QBrush, QColor
import logging

from managers.equipment_manager import EquipmentManager
from core.models import SymbolType

if TYPE_CHECKING:
    from sticker_app_pyqt6 import StickerApp

logger = logging.getLogger(__name__)


class EquipmentController(QObject):
    """Controller für Equipment-Tree Management"""
    
    # Signals
    equipment_selected = pyqtSignal(str, str, str, str)  # energy_id, equipment, symbol, qr_path
    equipment_saved = pyqtSignal()
    tree_updated = pyqtSignal()
    
    def __init__(self, equipment_manager: EquipmentManager, parent: Any = None):
        super().__init__(parent)
        self.equipment_manager = equipment_manager
        self.equipment_tree: Optional[QTreeWidget] = None
        self.equipment_status_label: Optional[QLabel] = None
        self.parent_app = parent
        self._expanded_items: set = set()  # Speichert expandierte Items
    
    def _show_styled_info_dialog(self, title: str, text: str):
        """Zeigt einen gestylten Info-Dialog"""
        from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel
        from ui.glass_button import GlassGlowButton
        from ui.theme import Theme
        
        dialog = QDialog(self.parent_app)
        dialog.setWindowTitle(title)
        dialog.setModal(True)
        dialog.setFixedWidth(450)
        
        bg_color = "#f4f6f9"
        text_color = "#2c3e50"
        
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_color};
                color: {text_color};
            }}
            QLabel {{
                color: {text_color};
            }}
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 20, 25, 20)
        
        # Icon + Nachricht
        content_layout = QHBoxLayout()
        icon_label = QLabel("ℹ️")
        icon_label.setStyleSheet("font-size: 24px; padding-right: 10px;")
        content_layout.addWidget(icon_label)
        
        msg_label = QLabel(text)
        msg_label.setStyleSheet(f"font-size: 12px; color: {text_color};")
        msg_label.setWordWrap(True)
        content_layout.addWidget(msg_label, 1)
        layout.addLayout(content_layout)
        
        layout.addSpacing(10)
        
        # Button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        ok_btn = GlassGlowButton("OK")
        ok_btn.setFixedHeight(32)
        ok_btn.setMinimumWidth(100)
        ok_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(ok_btn)
        layout.addLayout(button_layout)
        
        dialog.exec()
    
    def _show_styled_question_dialog(self, title: str, text: str) -> bool:
        """Zeigt einen gestylten Frage-Dialog, gibt True zurück wenn Ja geklickt"""
        from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel
        from ui.glass_button import GlassGlowButton
        from ui.theme import Theme
        
        dialog = QDialog(self.parent_app)
        dialog.setWindowTitle(title)
        dialog.setModal(True)
        dialog.setFixedWidth(450)
        
        bg_color = "#f4f6f9"
        text_color = "#2c3e50"
        
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_color};
                color: {text_color};
            }}
            QLabel {{
                color: {text_color};
            }}
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 20, 25, 20)
        
        # Icon + Nachricht
        content_layout = QHBoxLayout()
        icon_label = QLabel("❓")
        icon_label.setStyleSheet("font-size: 24px; padding-right: 10px;")
        content_layout.addWidget(icon_label)
        
        msg_label = QLabel(text)
        msg_label.setStyleSheet(f"font-size: 12px; color: {text_color};")
        msg_label.setWordWrap(True)
        content_layout.addWidget(msg_label, 1)
        layout.addLayout(content_layout)
        
        layout.addSpacing(10)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        button_layout.addStretch()
        
        no_btn = GlassGlowButton("Nein")
        no_btn.setFixedHeight(32)
        no_btn.setMinimumWidth(100)
        no_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(no_btn)
        
        yes_btn = GlassGlowButton("Ja")
        yes_btn.setFixedHeight(32)
        yes_btn.setMinimumWidth(100)
        yes_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(yes_btn)
        
        layout.addLayout(button_layout)
        
        return dialog.exec() == QDialog.DialogCode.Accepted
    
    def set_tree_widget(self, tree: QTreeWidget):
        """Setze das Tree-Widget"""
        self.equipment_tree = tree
        self.equipment_tree.itemDoubleClicked.connect(self._edit_selected_item_via_doubleclick)
        self.equipment_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.equipment_tree.customContextMenuRequested.connect(self._show_tree_context_menu)
        self.equipment_tree.itemSelectionChanged.connect(self._on_tree_selection_changed)
        self.equipment_tree.itemExpanded.connect(self._on_item_expanded)
        self.equipment_tree.itemCollapsed.connect(self._on_item_collapsed)
    
    def _get_item_key(self, item: QTreeWidgetItem) -> str:
        """Erstellt einen eindeutigen Schlüssel für ein Item"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return ""
        item_type = data.get('type', '')
        if item_type == 'location':
            return f"loc::{data.get('name', '')}"
        elif item_type == 'system':
            return f"sys::{data.get('location', '')}::{data.get('name', '')}"
        return ""
    
    def _on_item_expanded(self, item: QTreeWidgetItem):
        """Speichert expandierten Zustand"""
        key = self._get_item_key(item)
        if key:
            self._expanded_items.add(key)
    
    def _on_item_collapsed(self, item: QTreeWidgetItem):
        """Beim Einklappen: Entferne Zustand dieses Items UND aller Kinder"""
        key = self._get_item_key(item)
        if key:
            self._expanded_items.discard(key)
        
        # Auch alle Kinder aus der Liste entfernen und einklappen
        for i in range(item.childCount()):
            child = item.child(i)
            if child:
                child.setExpanded(False)
                child_key = self._get_item_key(child)
                if child_key:
                    self._expanded_items.discard(child_key)
    
    def set_status_label(self, label: QLabel):
        """Setze das Status-Label"""
        self.equipment_status_label = label
    
    def refresh_tree(self):
        """Equipment-Tree aktualisieren"""
        if not self.equipment_tree:
            return
        
        try:
            root = self.equipment_tree.invisibleRootItem()
            if root is None:
                return
            
            # Farben für Tree-Items
            location_color = QColor(20, 107, 138)
            system_color = QColor(40, 167, 69)
            equipment_color = QColor(108, 117, 125)
            
            # Sammle expandierte Items in die persistente Liste
            for i in range(root.childCount()):
                loc_item = root.child(i)
                if loc_item:
                    loc_key = self._get_item_key(loc_item)
                    if loc_item.isExpanded():
                        self._expanded_items.add(loc_key)
                    for j in range(loc_item.childCount()):
                        sys_item = loc_item.child(j)
                        if sys_item:
                            sys_key = self._get_item_key(sys_item)
                            if sys_item.isExpanded():
                                self._expanded_items.add(sys_key)
            
            self.equipment_tree.clear()
            
            for location_name in self.equipment_manager.get_all_locations():
                location_data = self.equipment_manager.equipment_data.get(location_name, {})
                systems = location_data.get('systems', [])
                
                loc_item = QTreeWidgetItem([location_name])
                loc_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'location', 'name': location_name})
                loc_item.setForeground(0, QBrush(location_color))
                
                for system in systems:
                    system_name = system.get('name', 'Unnamed System')
                    equipment_list = system.get('equipment', [])
                    
                    sys_item = QTreeWidgetItem([system_name])
                    sys_item.setData(0, Qt.ItemDataRole.UserRole, {
                        'type': 'system',
                        'location': location_name,
                        'name': system_name
                    })
                    sys_item.setForeground(0, QBrush(system_color))
                    
                    for equip in equipment_list:
                        equip_name = equip.get('name', 'Unnamed Equipment')
                        energy_id = equip.get('energy_id', '')
                        symbol_type = equip.get('symbol_type', '')
                        description = equip.get('description', '')
                        
                        display_text = equip_name
                        # Nur Energy-ID hinzufügen, wenn sie nicht bereits im Namen enthalten ist
                        # und wenn Name und Energy-ID unterschiedlich sind
                        if energy_id and energy_id != equip_name and f"[{energy_id}]".upper() not in equip_name.upper():
                            display_text += f" [{energy_id}]"
                        # Description hinzufügen wenn vorhanden
                        if description:
                            display_text += f" - {description}"
                        
                        equip_item = QTreeWidgetItem([display_text])
                        equip_item.setData(0, Qt.ItemDataRole.UserRole, {
                            'type': 'equipment',
                            'location': location_name,
                            'system': system_name,
                            'name': equip_name,
                            'energy_id': energy_id,
                            'symbol_type': symbol_type,
                            'description': description,
                            'qr_path': equip.get('qr_path', '')
                        })
                        equip_item.setForeground(0, QBrush(equipment_color))
                        
                        sys_item.addChild(equip_item)
                    
                    loc_item.addChild(sys_item)
                
                self.equipment_tree.addTopLevelItem(loc_item)
                
                # Restore expansion state aus persistenter Liste
                loc_key = f"loc::{location_name}"
                if loc_key in self._expanded_items:
                    loc_item.setExpanded(True)
                
                for j in range(loc_item.childCount()):
                    sys_item = loc_item.child(j)
                    if sys_item:
                        sys_data = sys_item.data(0, Qt.ItemDataRole.UserRole)
                        if sys_data:
                            sys_key = f"sys::{location_name}::{sys_data.get('name', '')}"
                            if sys_key in self._expanded_items:
                                sys_item.setExpanded(True)
            
            self.tree_updated.emit()
            
        except Exception as e:
            logger.error(f"Error refreshing equipment tree: {e}", exc_info=True)
    
    def add_location(self):
        """Neue Location hinzufügen"""
        name, ok = QInputDialog.getText(
            self.equipment_tree,
            "Neuer Standort",
            "Standort-Name:"
        )
        if ok and name:
            if self.equipment_manager.add_location(name):
                self.refresh_tree()
                QMessageBox.information(
                    self.equipment_tree,
                    "Erfolg",
                    f"Standort '{name}' hinzugefügt"
                )
            else:
                QMessageBox.warning(
                    self.equipment_tree,
                    "Fehler",
                    f"Standort '{name}' existiert bereits"
                )
    
    def add_system(self):
        """Neues System hinzufügen"""
        if not self.equipment_tree:
            return
            
        selected = self.equipment_tree.selectedItems()
        if not selected:
            QMessageBox.warning(
                self.equipment_tree,
                "Keine Auswahl",
                "Bitte zuerst einen Standort auswählen"
            )
            return
        
        item = selected[0]
        data = item.data(0, Qt.ItemDataRole.UserRole)
        
        if data['type'] == 'location':
            location_name = data['name']
        elif data['type'] == 'system':
            location_name = data['location']
        elif data['type'] == 'equipment':
            location_name = data['location']
        else:
            return
        
        name, ok = QInputDialog.getText(
            self.equipment_tree,
            "Neues System",
            f"System-Name für Standort '{location_name}':"
        )
        
        if ok and name:
            symbol, ok2 = QInputDialog.getText(
                self.equipment_tree,
                "Symbol-Typ",
                "Symbol-Typ (z.B. ELECTRIC):",
                text="ELECTRIC"
            )
            
            if ok2:
                if self.equipment_manager.add_system(location_name, name, symbol or "ELECTRIC"):
                    self.refresh_tree()
                    QMessageBox.information(
                        self.equipment_tree,
                        "Erfolg",
                        f"System '{name}' hinzugefügt"
                    )
    
    def add_equipment(self):
        """Neues Equipment hinzufügen mit optimiertem Dialog"""
        if not self.equipment_tree:
            return
        
        # Importiere den neuen Dialog
        from dialogs.add_equipment_dialog import show_add_equipment_dialog
        
        # Vorauswahl aus Tree übernehmen falls vorhanden
        pre_location = ""
        pre_system = ""
        
        selected = self.equipment_tree.selectedItems()
        if selected:
            item = selected[0]
            data = item.data(0, Qt.ItemDataRole.UserRole)
            
            if data and data.get('type') == 'location':
                pre_location = data.get('name', '')
            elif data and data.get('type') == 'system':
                pre_location = data.get('location', '')
                pre_system = data.get('name', '')
            elif data and data.get('type') == 'equipment':
                pre_location = data.get('location', '')
                pre_system = data.get('system', '')
        
        # Dialog anzeigen mit Vorauswahl
        result = show_add_equipment_dialog(
            self.parent_app, 
            self.equipment_manager,
            pre_location=pre_location,
            pre_system=pre_system
        )
        
        if result:
            # Verwende Vorauswahl wenn keine Eingabe im Dialog
            location_name = result.get('location') or pre_location
            system_name = result.get('system') or pre_system
            equipment_name = result.get('name', '')
            energy_id = result.get('energy_id', '')
            description = result.get('description', '')
            symbol_type = result.get('symbol_type', 'ELECTRICAL')
            
            # Validierung
            if not location_name:
                self._show_styled_info_dialog("Hinweis", "Bitte einen Standort angeben.")
                return
            if not system_name:
                self._show_styled_info_dialog("Hinweis", "Bitte ein System angeben.")
                return
            if not equipment_name:
                self._show_styled_info_dialog("Hinweis", "Bitte einen Equipment-Namen angeben.")
                return
            
            # Standort erstellen falls nicht vorhanden
            hierarchy = self.equipment_manager.get_hierarchy()
            if location_name not in hierarchy:
                self.equipment_manager.add_location(location_name)
            
            # System erstellen falls nicht vorhanden
            location_data = self.equipment_manager.get_hierarchy().get(location_name, {})
            systems = location_data.get('systems', [])
            system_exists = any(s.get('name') == system_name for s in systems)
            
            if not system_exists:
                self.equipment_manager.add_system(location_name, system_name, symbol_type)
            
            # Sticker-Konfiguration für das Equipment speichern
            preset_type = result.get('preset_type', 'rectangle')
            loto_mode = result.get('loto_mode', 'single')
            sticker_config = {
                'preset_type': preset_type,
                'loto_mode': loto_mode
            }
            
            # Equipment hinzufügen (Reihenfolge: location, system, name, energy_id, symbol_type, description, qr_path, sticker_config)
            if self.equipment_manager.add_equipment(
                location_name, system_name, equipment_name, 
                energy_id, symbol_type, description, 
                "", sticker_config
            ):
                self.refresh_tree()
                
                # Preset und LOTO-Modus an Parent-App weitergeben
                if self.parent_app:
                    # Sticker Preset anwenden
                    if hasattr(self.parent_app, '_apply_sticker_preset'):
                        try:
                            self.parent_app._apply_sticker_preset(preset_type)
                        except Exception:
                            pass
                    
                    # LOTO Modus setzen
                    if hasattr(self.parent_app, 'single_loto_radio') and hasattr(self.parent_app, 'multi_loto_radio'):
                        if loto_mode == 'multi':
                            self.parent_app.multi_loto_radio.setChecked(True)
                        else:
                            self.parent_app.single_loto_radio.setChecked(True)
                
                self._show_styled_info_dialog(
                    "Erfolg", 
                    f"Equipment '{equipment_name}' wurde erfolgreich hinzugefügt!\n\n"
                    f"Standort: {location_name}\n"
                    f"System: {system_name}\n"
                    f"Equipment: {equipment_name}\n"
                    f"Energy ID: {energy_id}\n"
                    f"Sticker: {preset_type.title()}, {'Multi-LOTO' if loto_mode == 'multi' else 'Single-LOTO'}"
                )
    
    def add_equipment_batch(self):
        """Mehrere Equipments auf einmal hinzufügen (Tabellen-Dialog wie Excel/Sheets)"""
        if not self.equipment_tree:
            return
        
        # Importiere den Batch-Dialog
        from dialogs.batch_equipment_dialog import show_batch_equipment_dialog
        
        # Vorauswahl aus Tree übernehmen falls vorhanden
        pre_location = ""
        pre_system = ""
        
        selected = self.equipment_tree.selectedItems()
        if selected:
            item = selected[0]
            data = item.data(0, Qt.ItemDataRole.UserRole)
            
            if data and data.get('type') == 'location':
                pre_location = data.get('name', '')
            elif data and data.get('type') == 'system':
                pre_location = data.get('location', '')
                pre_system = data.get('name', '')
            elif data and data.get('type') == 'equipment':
                pre_location = data.get('location', '')
                pre_system = data.get('system', '')
        
        # Batch-Dialog anzeigen
        results = show_batch_equipment_dialog(
            self.parent_app,
            self.equipment_manager,
            pre_location=pre_location,
            pre_system=pre_system
        )
        
        if results and len(results) > 0:
            added_count = 0
            failed_count = 0
            
            for equipment_data in results:
                location_name = equipment_data.get('location', '').strip().upper()
                system_name = equipment_data.get('system', '').strip().upper()
                equipment_name = equipment_data.get('name', '').strip().upper()
                energy_id = equipment_data.get('energy_id', '').strip().upper()
                description = equipment_data.get('description', '').strip()
                symbol_type = equipment_data.get('symbol_type', 'ELECTRICAL').upper()
                preset_index = equipment_data.get('preset_index', 0)
                loto_mode = equipment_data.get('loto_mode', 'single')
                qr_code_path = equipment_data.get('qr_code_path', None)
                
                # Sticker-Konfiguration mit QR-Code
                sticker_config = {
                    'preset_index': preset_index,
                    'loto_mode': loto_mode,
                    'qr_code_path': qr_code_path
                }
                
                # Standort erstellen falls nicht vorhanden
                all_locations = self.equipment_manager.get_all_locations()
                if location_name not in all_locations:
                    self.equipment_manager.add_location(location_name)
                
                # System erstellen falls nicht vorhanden
                system_names = self.equipment_manager.get_system_names(location_name)
                if system_name not in system_names:
                    self.equipment_manager.add_system(location_name, system_name, symbol_type)
                
                # Equipment hinzufügen (mit QR-Code-Pfad)
                if self.equipment_manager.add_equipment(
                    location_name, system_name, equipment_name,
                    energy_id, symbol_type, description,
                    qr_code_path or "", sticker_config
                ):
                    added_count += 1
                else:
                    failed_count += 1
            
            # Tree aktualisieren
            self.refresh_tree()
            
            # Sticker Preset und LOTO Modus vom ersten Equipment anwenden
            if results and self.parent_app:
                first = results[0]
                preset_index = first.get('preset_index', 0)
                loto_mode = first.get('loto_mode', 'single')
                add_to_collection = first.get('add_to_collection', False)
                
                # Preset laden (wie in Sticker-Einstellungen)
                if hasattr(self.parent_app, '_load_preset_by_index'):
                    try:
                        self.parent_app._load_preset_by_index(preset_index)
                    except Exception:
                        pass
                
                # LOTO Modus setzen UND persistent speichern
                is_multi = (loto_mode == 'multi')
                if hasattr(self.parent_app, '_on_loto_mode_changed'):
                    # Das setzt die Radio-Buttons UND speichert in export_config
                    self.parent_app._on_loto_mode_changed(is_multi)
                
                # Radio-Buttons manuell setzen (falls _on_loto_mode_changed sie nicht setzt)
                if hasattr(self.parent_app, 'single_loto_radio') and hasattr(self.parent_app, 'multi_loto_radio'):
                    if is_multi:
                        self.parent_app.multi_loto_radio.setChecked(True)
                    else:
                        self.parent_app.single_loto_radio.setChecked(True)
                
                # Equipments zur Collection hinzufügen wenn Option aktiviert
                if add_to_collection and added_count > 0:
                    self._add_batch_to_collection(results, loto_mode)
            
            # Erfolgsmeldung
            message = f"{added_count} Equipment(s) erfolgreich hinzugefügt!"
            if failed_count > 0:
                message += f"\n{failed_count} konnten nicht hinzugefügt werden (bereits vorhanden)."
            if first.get('add_to_collection', False) and added_count > 0:
                message += f"\n{added_count} zur Collection hinzugefügt."
            
            self._show_styled_info_dialog("Batch Import", message)
    
    def _add_batch_to_collection(self, results: list, loto_mode: str):
        """Fügt alle Batch-Equipments zur Collection hinzu"""
        if not self.parent_app or not results:
            return
        
        for equipment_data in results:
            try:
                energy_id = equipment_data.get('energy_id', '')
                equipment_name = equipment_data.get('name', '')
                description = equipment_data.get('description', '')
                symbol_type = equipment_data.get('symbol_type', 'ELECTRICAL')
                
                # UI-Felder setzen
                if hasattr(self.parent_app, 'energy_entry'):
                    self.parent_app.energy_entry.setText(energy_id)
                if hasattr(self.parent_app, 'equipment_entry'):
                    self.parent_app.equipment_entry.setText(equipment_name)
                if hasattr(self.parent_app, 'description_entry'):
                    self.parent_app.description_entry.setText(description)
                if hasattr(self.parent_app, 'symbol_combo'):
                    index = self.parent_app.symbol_combo.findText(symbol_type.capitalize(), Qt.MatchFlag.MatchFixedString)
                    if index >= 0:
                        self.parent_app.symbol_combo.setCurrentIndex(index)
                
                # Zur Collection hinzufügen (ohne auto Count für alle außer dem letzten bei Multi)
                if hasattr(self.parent_app, 'add_to_collection'):
                    # Bei Multi-LOTO: Count erst beim letzten hinzufügen
                    is_last = equipment_data == results[-1]
                    if loto_mode == 'multi':
                        self.parent_app.add_to_collection(auto_add_count=is_last)
                    else:
                        # Bei Single-LOTO: immer Count hinzufügen
                        self.parent_app.add_to_collection(auto_add_count=True)
                        
            except Exception as e:
                logger.warning(f"Fehler beim Hinzufügen zur Collection: {e}")
    
    def save_equipment(self):
        """Equipment speichern"""
        try:
            self.equipment_manager.save()
            self.equipment_saved.emit()
            
            if self.equipment_status_label:
                self.equipment_status_label.setText("Equipment gespeichert")
                # Use a local variable to avoid closure issue with self.equipment_status_label potentially changing (though unlikely)
                lbl = self.equipment_status_label
                QTimer.singleShot(2000, lambda: lbl.setText("Keine Auswahl") if lbl else None)
            
        except Exception as e:
            if self.equipment_tree:
                QMessageBox.critical(
                    self.equipment_tree,
                    "Fehler",
                    f"Fehler beim Speichern: {e}"
                )
    
    def _on_tree_select(self):
        """Tree-Item wurde ausgewählt"""
        if not self.equipment_tree:
            return
            
        selected = self.equipment_tree.selectedItems()
        if not selected:
            if self.equipment_status_label:
                self.equipment_status_label.setText("Keine Auswahl")
            return
        
        item = selected[0]
        data = item.data(0, Qt.ItemDataRole.UserRole)
        
        if not data:
            return
        
        item_type = data.get('type', '')
        
        if item_type == 'equipment':
            energy_id = data.get('energy_id', '')
            equipment_name = data.get('name', '')
            symbol_type = data.get('symbol_type', 'ELECTRIC')
            qr_path = data.get('qr_path', '')
            
            if self.equipment_status_label:
                self.equipment_status_label.setText(
                    f"Equipment: {equipment_name} [{energy_id}]"
                )
            
            # Signal emittieren
            self.equipment_selected.emit(energy_id, equipment_name, symbol_type, qr_path)
            
        elif item_type == 'system':
            if self.equipment_status_label:
                self.equipment_status_label.setText(
                    f"System: {data.get('name', '')}"
                )
        elif item_type == 'location':
            if self.equipment_status_label:
                self.equipment_status_label.setText(
                    f"Standort: {data.get('name', '')}"
                )
    
    def _edit_selected_item_via_doubleclick(self, item: QTreeWidgetItem, column: int):
        """Item wurde doppelt geklickt -> Eigenschaften bearbeiten"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data.get('type') == 'equipment':
            self._edit_equipment_properties(item)
        else:
            self._rename_item(item)
    
    def _show_tree_context_menu(self, position: QPoint):
        """Context-Menü für Tree anzeigen"""
        if not self.equipment_tree:
            return
        
        tree = self.equipment_tree
        item = tree.itemAt(position)
        if not item:
            return
        
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        
        menu = QMenu(tree)
        
        item_type = data.get('type', '')
        
        if item_type == 'system':
            # System-Menü
            add_equipment_action = QAction("Betriebsmittel hinzufügen", menu)
            add_equipment_action.triggered.connect(lambda: self._add_equipment_to_system(item))
            menu.addAction(add_equipment_action)
            
            group_equipment_action = QAction("Equipment automatisch gruppieren", menu)
            group_equipment_action.triggered.connect(lambda: self._auto_group_equipment(item))
            menu.addAction(group_equipment_action)
            
            menu.addSeparator()
            
            add_to_collection_action = QAction("Zum Collection hinzufügen", menu)
            add_to_collection_action.triggered.connect(lambda: self._add_system_to_collection(item))
            menu.addAction(add_to_collection_action)
            
            export_direct_action = QAction("Direkt exportieren (PDF)", menu)
            export_direct_action.triggered.connect(lambda: self._export_system_direct(item))
            menu.addAction(export_direct_action)
            
            menu.addSeparator()
            
            # QR-Code Funktionen auch für System
            location = data.get('location', '')
            system_name = data.get('system', '')
            
            qr_manage_action = QAction("QR-Code verwalten", menu)
            qr_manage_action.triggered.connect(lambda: self._manage_system_qr_code(item))
            menu.addAction(qr_manage_action)
            
            qr_assign_action = QAction("QR-Code zuweisen", menu)
            qr_assign_action.triggered.connect(lambda: self._assign_system_qr_code_quick(item))
            menu.addAction(qr_assign_action)
            
            # Prüfe ob System einen QR-Code hat
            has_qr = False
            try:
                system_obj = self.equipment_manager.get_system(location, system_name)
                if system_obj:
                    has_qr = bool(system_obj.get('qr_path', ''))
            except Exception:
                pass
            
            if has_qr:
                qr_delete_action = QAction("QR-Code löschen", menu)
                qr_delete_action.triggered.connect(lambda: self._delete_system_qr_code(item))
                menu.addAction(qr_delete_action)
            
            menu.addSeparator()
            
            rename_action = QAction("Umbenennen", menu)
            rename_action.triggered.connect(lambda: self._rename_item(item))
            menu.addAction(rename_action)
            
            delete_action = QAction("Löschen", menu)
            delete_action.triggered.connect(lambda: self._delete_item(item))
            menu.addAction(delete_action)
            
        elif item_type == 'equipment':
            # Equipment-Menü
            selected_items = self.equipment_tree.selectedItems()
            selected_equipment = [it for it in selected_items
                                  if (it.data(0, Qt.ItemDataRole.UserRole) or {}).get('type') == 'equipment']
            if len(selected_equipment) > 1:
                add_selection_action = QAction("Auswahl zur Collection hinzufügen", menu)
                add_selection_action.triggered.connect(self._add_selected_equipment_to_collection)
                menu.addAction(add_selection_action)
            else:
                add_to_collection_action = QAction("Zur Collection hinzufügen", menu)
                add_to_collection_action.triggered.connect(lambda: self._add_item_to_collection(item))
                menu.addAction(add_to_collection_action)
            
            if len(selected_equipment) > 1:
                export_selection_action = QAction("Auswahl direkt exportieren (PDF)", menu)
                export_selection_action.triggered.connect(self._export_selected_equipment_direct)
                menu.addAction(export_selection_action)
            else:
                export_direct_action = QAction("Direkt exportieren (PDF)", menu)
                export_direct_action.triggered.connect(lambda: self._export_equipment_direct(item))
                menu.addAction(export_direct_action)
            
            menu.addSeparator()
            
            # QR-Code Funktionen (nur für einzelnes Equipment)
            if len(selected_equipment) <= 1:
                qr_manage_action = QAction("QR-Code verwalten", menu)
                qr_manage_action.triggered.connect(lambda: self._manage_qr_code(item))
                menu.addAction(qr_manage_action)
                
                qr_assign_action = QAction("QR-Code zuweisen", menu)
                qr_assign_action.triggered.connect(lambda: self._assign_qr_code_quick(item))
                menu.addAction(qr_assign_action)
                
                # Prüfe ob Equipment einen QR-Code hat
                location = data.get('location', '')
                system = data.get('system', '')
                equipment_name = data.get('equipment', '')
                has_qr = False
                try:
                    equipment_list = self.equipment_manager.get_equipment(location, system)
                    for eq in equipment_list:
                        if eq.get('name', '') == equipment_name:
                            has_qr = bool(eq.get('qr_path', ''))
                            break
                except Exception:
                    pass
                
                if has_qr:
                    qr_delete_action = QAction("QR-Code löschen", menu)
                    qr_delete_action.triggered.connect(lambda: self._delete_qr_code(item))
                    menu.addAction(qr_delete_action)
                
                menu.addSeparator()
            
            edit_action = QAction("Eigenschaften bearbeiten", menu)
            edit_action.triggered.connect(lambda: self._edit_equipment_properties(item))
            menu.addAction(edit_action)
            
            rename_action = QAction("Umbenennen", menu)
            rename_action.triggered.connect(lambda: self._rename_item(item))
            menu.addAction(rename_action)
            
            # Löschen: Bei Mehrfachauswahl alle löschen
            if len(selected_equipment) > 1:
                delete_action = QAction(f"{len(selected_equipment)} Auswahl löschen", menu)
                delete_action.triggered.connect(self._delete_selected_items)
            else:
                delete_action = QAction("Löschen", menu)
                delete_action.triggered.connect(lambda: self._delete_item(item))
            menu.addAction(delete_action)
            
        elif item_type == 'location':
            # Location-Menü
            add_system_action = QAction("System hinzufügen", menu)
            add_system_action.triggered.connect(lambda: self._add_system_to_location(item))
            menu.addAction(add_system_action)
            
            menu.addSeparator()
            
            add_to_collection_action = QAction("Standort komplett zur Collection hinzufügen", menu)
            add_to_collection_action.triggered.connect(lambda: self._add_location_to_collection(item))
            menu.addAction(add_to_collection_action)
            
            export_direct_action = QAction("Standort komplett exportieren (PDF)", menu)
            export_direct_action.triggered.connect(lambda: self._export_location_direct(item))
            menu.addAction(export_direct_action)
            
            menu.addSeparator()
            
            rename_action = QAction("Umbenennen", menu)
            rename_action.triggered.connect(lambda: self._rename_item(item))
            menu.addAction(rename_action)
            
            delete_action = QAction("Löschen", menu)
            delete_action.triggered.connect(lambda: self._delete_item(item))
            menu.addAction(delete_action)
        
        viewport = tree.viewport()
        if viewport:
            menu.exec(viewport.mapToGlobal(position))

    def _add_selected_equipment_to_collection(self):
        """Mehrfachauswahl aus dem Tree zur Collection hinzufügen"""
        if not self.parent_app or not self.equipment_tree:
            return

        selected_items = self.equipment_tree.selectedItems()
        equipment_items = []

        for item in selected_items:
            data = item.data(0, Qt.ItemDataRole.UserRole) or {}
            if data.get('type') != 'equipment':
                continue
            equipment_items.append(data)

        if not equipment_items:
            return

        added = 0
        progress = None
        total_items = len(equipment_items)
        if total_items > 1:
            progress = QProgressDialog("Lade Auswahl in die Ablage…", "Abbrechen", 0, total_items, self.equipment_tree)
            progress.setWindowTitle("Bitte warten")
            progress.setWindowModality(Qt.WindowModality.ApplicationModal)
            progress.setMinimumDuration(0)

        for idx, data in enumerate(equipment_items, start=1):
            if progress:
                progress.setValue(idx - 1)
                QCoreApplication.processEvents()
                if progress.wasCanceled():
                    break

            energy_id = data.get('energy_id', '')
            equipment_name = data.get('name', '')
            symbol_type = data.get('symbol_type', '')
            description = data.get('description', '')

            if hasattr(self.parent_app, 'energy_entry'):
                self.parent_app.energy_entry.setText(energy_id)
            if hasattr(self.parent_app, 'equipment_entry'):
                self.parent_app.equipment_entry.setText(equipment_name)
            if hasattr(self.parent_app, 'description_entry'):
                self.parent_app.description_entry.setText(description or '')
            if hasattr(self.parent_app, 'symbol_combo') and symbol_type:
                index = self.parent_app.symbol_combo.findText(symbol_type.capitalize(), Qt.MatchFlag.MatchFixedString)
                if index >= 0:
                    self.parent_app.symbol_combo.setCurrentIndex(index)

            if hasattr(self.parent_app, 'add_to_collection'):
                if hasattr(self.parent_app, 'register_collection_source'):
                    self.parent_app.register_collection_source(data.get('system', ''))
                # Gruppe für per-group Count-Sticker setzen
                # Verwende gespeicherte loto_group aus sticker_config (falls vorhanden)
                eq_system = data.get('system', '')
                loto_group = ''
                try:
                    location = data.get('location', '')
                    eq_list = self.equipment_manager.get_equipment(location, eq_system)
                    for eq in eq_list:
                        if eq.get('name', '') == equipment_name:
                            sc = eq.get('sticker_config') or {}
                            loto_group = sc.get('loto_group', '')
                            break
                except Exception:
                    pass
                self.parent_app._current_collection_group = loto_group or eq_system
                self.parent_app._current_collection_location = data.get('location', '')
                self.parent_app._current_collection_system = eq_system
                self.parent_app.add_to_collection()
                added += 1

        if progress:
            progress.setValue(total_items)

        if added > 0 and self.parent_app and hasattr(self.parent_app, 'status_bar') and self.parent_app.status_bar:
            msg_text = f"{added} Equipment-Items zur Collection hinzugefügt" if added > 1 else "Equipment zur Collection hinzugefügt"
            self.parent_app.status_bar.showMessage(msg_text, 3000)
    
    def _clear_collection_silent(self):
        """Collection leeren ohne Bestätigungsdialog (für Direkt-Export)"""
        if not self.parent_app:
            return
        if hasattr(self.parent_app, 'collection_service'):
            self.parent_app.collection_service.clear()
        self.parent_app.collection.clear()
        self.parent_app.collection_export_sources.clear()
        if hasattr(self.parent_app, 'update_collection_list'):
            self.parent_app.update_collection_list()
    
    def _ask_count_copies(self):
        """Fragt den Benutzer wie viele Count-Sticker Kopien exportiert werden sollen.
        Setzt die Kopienanzahl direkt auf die Count-Sticker in der Collection.
        Returns: True wenn weiter, False wenn abgebrochen."""
        if not self.parent_app:
            return True
        # Prüfe ob Count-Sticker in der Collection vorhanden sind
        has_count = any(
            self.parent_app._is_count_multi(it) or self.parent_app._is_count_single(it)
            for it in self.parent_app.collection
        )
        if not has_count:
            return True
        
        from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QDialogButtonBox
        from ui.glass_button import GlassGlowButton
        from ui.theme import create_dialog_stylesheet, get_theme_colors, Theme
        from ui.spinboxes import StyledSpinBox
        
        colors = get_theme_colors(Theme.LIGHT)
        dialog = QDialog(self.parent_app)
        dialog.setWindowTitle("Count-Sticker Kopien")
        dialog.setFixedWidth(320)
        dialog.setStyleSheet(create_dialog_stylesheet(Theme.LIGHT))
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        label = QLabel("Wie viele Count-Sticker Kopien exportieren?")
        label.setStyleSheet(f"color: {colors['fg']}; font-size: 13px;")
        label.setWordWrap(True)
        layout.addWidget(label)
        
        spin = StyledSpinBox()
        spin.setRange(1, 50)
        spin.setValue(1)
        spin.setStyleSheet(
            f"padding: 6px; background: {colors['input_bg']}; color: {colors['fg']}; border: 1px solid {colors['border']}; border-radius: 6px;"
        )
        layout.addWidget(spin)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = GlassGlowButton("Abbrechen")
        cancel_btn.setMinimumHeight(38)
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)
        ok_btn = GlassGlowButton("Exportieren")
        ok_btn.setMinimumHeight(38)
        ok_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)
        
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return False
        
        copies = spin.value()
        # Setze Kopienanzahl auf alle Count-Sticker
        for item in self.parent_app.collection:
            if (self.parent_app._is_count_multi(item) or self.parent_app._is_count_single(item)):
                if len(item) > 5 and isinstance(item[5], dict):
                    item[5]["copies"] = copies
        self.parent_app.update_collection_list()
        return True

    def _ask_count_copies_detailed(self):
        """Zeigt ein Auswahlfenster für alle Count-Sticker mit individuellen Kopienanzahlen.
        Erlaubt Aktivieren/Deaktivieren einzelner Count-Sticker.
        Returns: True wenn exportieren, False wenn abgebrochen."""
        if not self.parent_app:
            return True
        
        # Sammle alle Count-Sticker mit Index
        count_entries = []
        for idx, item in enumerate(self.parent_app.collection):
            if self.parent_app._is_count_multi(item) or self.parent_app._is_count_single(item):
                marker = item[5] if len(item) > 5 and isinstance(item[5], dict) else {}
                is_multi = self.parent_app._is_count_multi(item)
                group = marker.get("group", "")
                details = marker.get("details", "")
                copies = marker.get("copies", 1)
                
                if is_multi:
                    # Zähle reguläre Sticker der gleichen Gruppe
                    regular_count = sum(
                        1 for it in self.parent_app.collection
                        if not (self.parent_app._is_count_single(it) or self.parent_app._is_count_multi(it))
                        and len(it) > 5 and isinstance(it[5], dict) and it[5].get("group", "") == group
                    )
                    label = f"{group} — {regular_count} LOTO Points" if group else f"TOTAL — {regular_count} LOTO Points"
                else:
                    energy_id = item[2] if len(item) > 2 else ""
                    label = f"{energy_id} — 1 LOTO Point"
                
                count_entries.append({
                    'idx': idx, 'label': label, 'group': group,
                    'copies': copies, 'is_multi': is_multi
                })
        
        if not count_entries:
            return True
        
        # Bei nur einem Count-Sticker: einfachen Dialog zeigen
        if len(count_entries) <= 1:
            return self._ask_count_copies()
        
        from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel,
                                      QCheckBox, QScrollArea, QWidget, QFrame)
        from ui.glass_button import GlassGlowButton
        from ui.theme import create_dialog_stylesheet, get_theme_colors, Theme
        from ui.spinboxes import StyledSpinBox
        
        colors = get_theme_colors(Theme.LIGHT)
        dialog = QDialog(self.parent_app)
        dialog.setWindowTitle("Count-Sticker Auswahl")
        dialog.setMinimumWidth(480)
        dialog.setMaximumHeight(600)
        dialog.setStyleSheet(create_dialog_stylesheet(Theme.LIGHT))
        
        main_layout = QVBoxLayout(dialog)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        header = QLabel(f"{len(count_entries)} Count-Sticker gefunden. Auswahl und Kopien festlegen:")
        header.setStyleSheet(f"color: {colors['fg']}; font-size: 13px; font-weight: bold;")
        header.setWordWrap(True)
        main_layout.addWidget(header)
        
        # Scroll area for count sticker entries
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(6)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        
        checkboxes = []
        spinboxes = []
        
        for entry in count_entries:
            row = QFrame()
            row.setStyleSheet(
                f"QFrame {{ background: {colors['input_bg']}; border: 1px solid {colors['border']};"
                f" border-radius: 6px; padding: 4px; }}"
            )
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(8, 4, 8, 4)
            row_layout.setSpacing(8)
            
            cb = QCheckBox()
            cb.setChecked(True)
            cb.setStyleSheet("QCheckBox::indicator { width: 18px; height: 18px; }")
            row_layout.addWidget(cb)
            checkboxes.append(cb)
            
            lbl = QLabel(entry['label'])
            lbl.setStyleSheet(f"color: {colors['fg']}; font-size: 12px; border: none;")
            lbl.setWordWrap(True)
            row_layout.addWidget(lbl, 1)
            
            copies_lbl = QLabel("x")
            copies_lbl.setStyleSheet(f"color: {colors['fg']}; font-size: 12px; border: none;")
            row_layout.addWidget(copies_lbl)
            
            spin = StyledSpinBox()
            spin.setRange(1, 50)
            spin.setValue(entry['copies'])
            spin.setFixedWidth(60)
            spin.setStyleSheet(
                f"padding: 4px; background: white; color: {colors['fg']};"
                f" border: 1px solid {colors['border']}; border-radius: 4px;"
            )
            row_layout.addWidget(spin)
            spinboxes.append(spin)
            
            scroll_layout.addWidget(row)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
        
        # Alle/Keine Buttons
        toggle_layout = QHBoxLayout()
        select_all_btn = GlassGlowButton("Alle")
        select_all_btn.setMinimumHeight(30)
        select_all_btn.clicked.connect(lambda: [cb.setChecked(True) for cb in checkboxes])
        toggle_layout.addWidget(select_all_btn)
        select_none_btn = GlassGlowButton("Keine")
        select_none_btn.setMinimumHeight(30)
        select_none_btn.clicked.connect(lambda: [cb.setChecked(False) for cb in checkboxes])
        toggle_layout.addWidget(select_none_btn)
        toggle_layout.addStretch()
        main_layout.addLayout(toggle_layout)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = GlassGlowButton("Abbrechen")
        cancel_btn.setMinimumHeight(38)
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)
        ok_btn = GlassGlowButton("Exportieren")
        ok_btn.setMinimumHeight(38)
        ok_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(ok_btn)
        main_layout.addLayout(btn_layout)
        
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return False
        
        # Anwenden: Deaktivierte Count-Sticker entfernen, Kopien setzen
        indices_to_remove = []
        for i, entry in enumerate(count_entries):
            idx = entry['idx']
            if not checkboxes[i].isChecked():
                indices_to_remove.append(idx)
            else:
                item = self.parent_app.collection[idx]
                if len(item) > 5 and isinstance(item[5], dict):
                    item[5]["copies"] = spinboxes[i].value()
        
        # Entferne deaktivierte Count-Sticker (von hinten nach vorne)
        for idx in sorted(indices_to_remove, reverse=True):
            self.parent_app.collection.pop(idx)
        
        self.parent_app.update_collection_list()
        return True

    def _export_system_direct(self, item: QTreeWidgetItem):
        """System direkt als PDF exportieren (Collection leeren → hinzufügen → export)"""
        if not self.parent_app:
            return
        self._clear_collection_silent()
        self._add_system_to_collection(item)
        if self.parent_app.collection:
            if self._ask_count_copies():
                self.parent_app.export_pdf()
    
    def _export_equipment_direct(self, item: QTreeWidgetItem):
        """Einzelnes Equipment direkt als PDF exportieren"""
        if not self.parent_app:
            return
        self._clear_collection_silent()
        self._add_item_to_collection(item)
        if self.parent_app.collection:
            if self._ask_count_copies():
                self.parent_app.export_pdf()
    
    def _export_selected_equipment_direct(self):
        """Mehrfachauswahl direkt als PDF exportieren"""
        if not self.parent_app:
            return
        self._clear_collection_silent()
        self._add_selected_equipment_to_collection()
        if self.parent_app.collection:
            if self._ask_count_copies():
                self.parent_app.export_pdf()
    
    def _add_equipment_to_system(self, item: QTreeWidgetItem):
        """Equipment zu System hinzufügen"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        location_name = data['location']
        system_name = data['name']
        
        name, ok = QInputDialog.getText(
            self.equipment_tree,
            "Neues Betriebsmittel",
            f"Name:"
        )
        
        if ok and name:
            energy_id, ok2 = QInputDialog.getText(
                self.equipment_tree,
                "Energie-ID",
                "Energie-ID:"
            )
            
            if ok2:
                if self.equipment_manager.add_equipment(
                    location_name, system_name, name, energy_id or "", description=""
                ):
                    self.refresh_tree()
    
    def _add_system_to_location(self, item: QTreeWidgetItem):
        """System zu Location hinzufügen"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        location_name = data['name']
        
        name, ok = QInputDialog.getText(
            self.equipment_tree,
            "Neues System",
            "System-Name:"
        )
        
        if ok and name:
            symbol, ok2 = QInputDialog.getText(
                self.equipment_tree,
                "Symbol-Typ",
                "Symbol-Typ:",
                text="ELECTRIC"
            )
            
            if ok2:
                if self.equipment_manager.add_system(
                    location_name, name, symbol or "ELECTRIC"
                ):
                    self.refresh_tree()
    
    def _add_system_to_collection(self, item: QTreeWidgetItem):
        """Alle Equipment eines Systems zur Collection hinzufügen"""
        if not self.parent_app:
            return
        
        data = item.data(0, Qt.ItemDataRole.UserRole)
        location_name = data['location']
        system_name = data['name']

        if hasattr(self.parent_app, 'register_collection_source'):
            self.parent_app.register_collection_source(system_name)
        
        # Gruppe für per-group Count-Sticker setzen
        self.parent_app._current_collection_group = system_name
        
        # WICHTIG: Lösche Input-Felder VOR der Schleife, um sicherzustellen, dass keine alten Werte verwendet werden
        if hasattr(self.parent_app, 'energy_entry'):
            self.parent_app.energy_entry.clear()
        if hasattr(self.parent_app, 'equipment_entry'):
            self.parent_app.equipment_entry.clear()
        if hasattr(self.parent_app, 'description_entry'):
            self.parent_app.description_entry.clear()
        
        # Zuerst prüfen: Hat das erste Equipment eine gespeicherte sticker_config?
        imported_loto_mode_single = None  # None = nicht definiert
        logger.debug(f"Prüfe sticker_config für System {system_name}, {item.childCount()} Kinder")
        for i in range(item.childCount()):
            equip_item = item.child(i)
            if equip_item:
                eq_data = equip_item.data(0, Qt.ItemDataRole.UserRole)
                logger.debug(f"Child {i} eq_data type={eq_data.get('type') if eq_data else None}")
                if eq_data and eq_data.get('type') == 'equipment':
                    location = eq_data.get('location', '')
                    system = eq_data.get('system', '')
                    eq_name = eq_data.get('name', '')
                    logger.debug(f"Equipment={eq_name}, Location={location}, System={system}")
                    try:
                        equipment_list = self.equipment_manager.get_equipment(location, system)
                        logger.debug(f"{len(equipment_list)} Equipments gefunden")
                        for eq in equipment_list:
                            logger.debug(f"Vergleiche '{eq.get('name', '')}' mit '{eq_name}'")
                            if eq.get('name', '') == eq_name:
                                sticker_cfg = eq.get('sticker_config', {})
                                logger.debug(f"sticker_config gefunden: {bool(sticker_cfg)}, loto_mode_single in config: {'loto_mode_single' in sticker_cfg if sticker_cfg else False}")
                                if sticker_cfg and 'loto_mode_single' in sticker_cfg:
                                    imported_loto_mode_single = sticker_cfg.get('loto_mode_single')
                                    logger.debug(f"Import: loto_mode_single={imported_loto_mode_single} aus Equipment '{eq_name}'")
                                break
                    except Exception as e:
                        logger.error(f"Fehler beim Laden: {e}")
                    break  # Nur erstes Equipment prüfen
        
        # Wenn System-Name "SINGLELOTOCOUNT" enthält, als Single Count behandeln
        if imported_loto_mode_single is None and "SINGLELOTOCOUNT" in system_name.upper().replace(" ", "").replace("_", ""):
            imported_loto_mode_single = True
            logger.debug(f"System-Name '{system_name}' enthält SINGLELOTOCOUNT -> Single Count Modus")
        
        # Config vom ersten Equipment laden (alle im System sollten gleiche Config haben)
        first_config_loaded = False
        
        # Alle Equipment-Items des Systems hinzufügen — OHNE auto_add_count
        # Count-Sticker werden nach der Schleife per-group generiert
        count = 0
        for i in range(item.childCount()):
            equip_item = item.child(i)
            if equip_item:
                # Nur beim ersten Equipment die Config laden
                self._add_item_to_collection(equip_item, load_config=(not first_config_loaded), auto_add_count=False)
                if not first_config_loaded:
                    first_config_loaded = True
                count += 1
        
        # WICHTIG: Löschen Sie nach der Schleife die vorher gespeicherten Werte aus den Eingabefeldern
        if hasattr(self.parent_app, 'energy_entry'):
            self.parent_app.energy_entry.clear()
        if hasattr(self.parent_app, 'equipment_entry'):
            self.parent_app.equipment_entry.clear()
        if hasattr(self.parent_app, 'description_entry'):
            self.parent_app.description_entry.clear()
        
        # Setze die Gruppe zurück nach dem Hinzufügen — merke den letzten Wert
        last_collection_group = getattr(self.parent_app, '_current_collection_group', '') or ''
        self.parent_app._current_collection_group = ''
        
        # Nach dem Hinzufügen aller Items: Count-Sticker generieren
        # PRIORITÄT: Gespeicherte Config > Radio-Button
        
        if imported_loto_mode_single is not None:
            # Gespeicherte Config hat absoluten Vorrang!
            should_generate_multi = not imported_loto_mode_single and count > 0
            should_generate_single = imported_loto_mode_single and count > 0
            logger.debug(f"IMPORT Config überschreibt: Multi-LOTO={not imported_loto_mode_single}, Single-LOTO={imported_loto_mode_single}")
            
            # Radio-Buttons entsprechend setzen UND internen State synchronisieren
            if hasattr(self.parent_app, 'single_loto_radio') and hasattr(self.parent_app, 'multi_loto_radio'):
                if imported_loto_mode_single:
                    self.parent_app.single_loto_radio.setChecked(True)
                else:
                    self.parent_app.multi_loto_radio.setChecked(True)
            # _on_loto_mode_changed aufrufen, da clicked-Signal bei setChecked nicht feuert
            if hasattr(self.parent_app, '_on_loto_mode_changed'):
                mode = 'single' if imported_loto_mode_single else 'multi'
                self.parent_app._on_loto_mode_changed(mode)
                logger.debug(f"LOTO Modus synchronisiert: {mode}")
        elif hasattr(self.parent_app, 'multi_loto_radio') and self.parent_app.multi_loto_radio.isChecked():
            # Fallback: Aktueller Radio-Button - Multi
            should_generate_multi = count > 0
            should_generate_single = False
            logger.debug("Radio-Button: Multi-LOTO aktiv")
        elif hasattr(self.parent_app, 'single_loto_radio') and self.parent_app.single_loto_radio.isChecked():
            # Fallback: Aktueller Radio-Button - Single
            should_generate_multi = False
            should_generate_single = count > 0
            logger.debug("Radio-Button: Single-LOTO aktiv")
        else:
            should_generate_multi = False
            should_generate_single = False
        
        # Single-LOTO: Für jeden Sticker DIESES Systems einen Count-Sticker erstellen
        if should_generate_single:
            logger.debug(f"Prüfe Single-Count-Sticker für System '{system_name}' ({count} Items)")
            try:
                # Ermittle die tatsächliche Gruppe, die die Items bekommen haben
                # (kann loto_group aus sticker_config sein oder system_name)
                actual_group = last_collection_group or system_name
                
                # Nur reguläre Items DIESER Gruppe
                regular_items = [
                    it for it in self.parent_app.collection 
                    if not (self.parent_app._is_count_single(it) or self.parent_app._is_count_multi(it))
                    and len(it) > 5 and isinstance(it[5], dict) and it[5].get("group", "") in (system_name, actual_group)
                ]
                
                # Sammle existierende Count-Sticker IDs
                existing_count_ids = set()
                for item_data in self.parent_app.collection:
                    if self.parent_app._is_count_single(item_data):
                        count_id = item_data[2] if len(item_data) > 2 else ""
                        existing_count_ids.add(count_id)
                
                logger.debug(f"Existierende Count-Sticker: {existing_count_ids}")
                
                # Für jeden regulären Sticker dieses Systems prüfen ob Count-Sticker fehlt
                created_count = 0
                for idx, reg_item in enumerate(regular_items):
                    e_id = reg_item[2] if len(reg_item) > 2 else ""
                    equip = reg_item[3] if len(reg_item) > 3 else ""
                    expected_count_id = f"C_{e_id}"
                    
                    if expected_count_id in existing_count_ids:
                        logger.debug(f"SKIP: Count-Sticker {expected_count_id} existiert bereits")
                        continue
                    
                    if e_id and equip and e_id != equip:
                        detail_str = f"{e_id} {equip}".strip()
                    else:
                        detail_str = (e_id or equip).strip()
                    
                    count_img = self.parent_app.count_generator.generate(detail_str, 1)
                    insert_idx = self.parent_app.collection.index(reg_item) + 1
                    self.parent_app.collection.insert(insert_idx, [
                        count_img, "COUNT_SINGLE", expected_count_id, equip, detail_str, 
                        {"type": "count_single", "details": detail_str}, count_img
                    ])
                    created_count += 1
                    logger.debug(f"Single-Count-Sticker #{created_count} erstellt für {e_id}")
                
                logger.debug(f"{created_count} neue Count-Sticker erstellt (von {len(regular_items)} Items in System '{system_name}')")
                
                if hasattr(self.parent_app, 'update_collection_list'):
                    self.parent_app.update_collection_list()
                    
            except Exception as e:
                logger.error(f"Fehler beim Generieren der Single-Count-Sticker: {e}")
                import traceback
                traceback.print_exc()
        
        # Multi-LOTO: Regeneriere per-group Count-Sticker (ein Count pro Gruppe)
        if should_generate_multi:
            logger.debug(f"Starte Multi-Count-Sticker Generierung für System '{system_name}'")
            try:
                if hasattr(self.parent_app, '_regenerate_multi_count_sticker'):
                    self.parent_app._regenerate_multi_count_sticker()
                    logger.debug("Multi-Count-Sticker regeneriert (per-group)")
            except Exception as e:
                logger.error(f"Fehler beim Generieren des Multi-Count-Stickers: {e}")
                import traceback
                traceback.print_exc()
        elif not should_generate_single:
            if count < 2:
                logger.debug(f"Count-Sticker nicht generiert - zu wenig Items ({count})")
            else:
                logger.debug("Count-Sticker nicht generiert - Benutzer hat abgelehnt")
        
        if count > 0 and self.parent_app and hasattr(self.parent_app, 'status_bar') and self.parent_app.status_bar:
            self.parent_app.status_bar.showMessage(
                f"{count} Equipment-Items zur Collection hinzugefügt", 3000
            )
    
    def _add_location_to_collection(self, item: QTreeWidgetItem):
        """Alle Systeme eines Standorts komplett zur Collection hinzufügen"""
        if not self.parent_app:
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        location_name = data.get('name', '')

        total_systems = item.childCount()
        if total_systems == 0:
            self._show_styled_info_dialog("Hinweis", f"Standort '{location_name}' hat keine Systeme.")
            return

        progress = None
        if total_systems > 1:
            progress = QProgressDialog(
                f"Lade Standort '{location_name}' in die Ablage…",
                "Abbrechen", 0, total_systems, self.equipment_tree
            )
            progress.setWindowTitle("Bitte warten")
            progress.setWindowModality(Qt.WindowModality.ApplicationModal)
            progress.setMinimumDuration(0)

        total_added = 0
        for i in range(total_systems):
            if progress:
                progress.setValue(i)
                QCoreApplication.processEvents()
                if progress.wasCanceled():
                    break

            sys_item = item.child(i)
            if not sys_item:
                continue
            sys_data = sys_item.data(0, Qt.ItemDataRole.UserRole)
            if not sys_data or sys_data.get('type') != 'system':
                continue

            count_before = len(self.parent_app.collection) if hasattr(self.parent_app, 'collection') else 0
            self._add_system_to_collection(sys_item)
            count_after = len(self.parent_app.collection) if hasattr(self.parent_app, 'collection') else 0
            total_added += (count_after - count_before)

        if progress:
            progress.setValue(total_systems)

        if total_added > 0 and self.parent_app and hasattr(self.parent_app, 'status_bar') and self.parent_app.status_bar:
            self.parent_app.status_bar.showMessage(
                f"Standort '{location_name}': {total_added} Items zur Collection hinzugefügt", 3000
            )

    def _export_location_direct(self, item: QTreeWidgetItem):
        """Standort komplett direkt als PDF exportieren (Collection leeren → hinzufügen → export)"""
        if not self.parent_app:
            return
        self._clear_collection_silent()
        self._add_location_to_collection(item)
        if self.parent_app.collection:
            if self._ask_count_copies_detailed():
                self.parent_app.export_pdf()

    def _add_item_to_collection(self, item: QTreeWidgetItem, load_config: bool = True, auto_add_count: bool = True):
        """Equipment-Item zur Collection hinzufügen
        
        Args:
            item: Tree-Widget Item
            load_config: Wenn False, wird die Sticker-Config nicht geladen (nur QR-Code)
            auto_add_count: Wenn False, wird kein Count-Sticker automatisch generiert
        """
        if not self.parent_app:
            return
        
        data = item.data(0, Qt.ItemDataRole.UserRole)
        
        if data.get('type') != 'equipment':
            return
        
        energy_id = data.get('energy_id', '')
        equipment_name = data.get('name', '')
        symbol_type = data.get('symbol_type', 'ELECTRIC')
        description = data.get('description', '')
        location = data.get('location', '')
        system = data.get('system', '')
        
        # QR-Code aus Equipment-Daten holen
        qr_path = ""
        sticker_config = None
        try:
            equipment_list = self.equipment_manager.get_equipment(location, system)
            for eq in equipment_list:
                if eq.get('name', '') == equipment_name:
                    qr_path = eq.get('qr_path', '')
                    sticker_config = eq.get('sticker_config', None)
                    break
        except Exception:
            pass
        
        # Gruppe für per-group Count-Sticker setzen
        # Verwende gespeicherte loto_group aus sticker_config (falls vorhanden), sonst System-Name
        loto_group = sticker_config.get('loto_group', '') if sticker_config else ''
        self.parent_app._current_collection_group = loto_group or system
        # Speichere Location/System für Equipment-Manager Sync
        self.parent_app._current_collection_location = location
        self.parent_app._current_collection_system = system
        
        # Sticker-Config wiederherstellen wenn vorhanden UND gewünscht
        if load_config and sticker_config and hasattr(self.parent_app, 'sticker_service'):
            try:
                from core.models import StickerConfig
                cfg = self.parent_app.sticker_service.generator.cfg
                count_cfg = self.parent_app.count_config
                
                # LOTO Sticker Parameter wiederherstellen
                cfg.width_mm = sticker_config.get('width_mm', cfg.width_mm)
                cfg.height_mm = sticker_config.get('height_mm', cfg.height_mm)
                cfg.dpi = sticker_config.get('dpi', cfg.dpi)
                cfg.corner_radius = sticker_config.get('corner_radius', cfg.corner_radius)
                cfg.outline_width = sticker_config.get('outline_width', cfg.outline_width)
                cfg.font_path = sticker_config.get('font_path', cfg.font_path)
                cfg.auto_adjust = sticker_config.get('auto_adjust', cfg.auto_adjust)
                cfg.sticker_color = sticker_config.get('sticker_color', cfg.sticker_color)
                cfg.font_size_mm = sticker_config.get('font_size_mm', cfg.font_size_mm)
                cfg.line_height_mm = sticker_config.get('line_height_mm', cfg.line_height_mm)
                cfg.symbol_corner_radius = sticker_config.get('symbol_corner_radius', cfg.symbol_corner_radius)
                cfg.symbol_size_mm = sticker_config.get('symbol_size_mm', cfg.symbol_size_mm)
                cfg.symbol_offset_x_mm = sticker_config.get('symbol_offset_x_mm', cfg.symbol_offset_x_mm)
                cfg.symbol_offset_y_mm = sticker_config.get('symbol_offset_y_mm', cfg.symbol_offset_y_mm)
                cfg.text_offset_x = sticker_config.get('text_offset_x', cfg.text_offset_x)
                cfg.text_offset_y = sticker_config.get('text_offset_y', cfg.text_offset_y)
                cfg.qr_mode_enabled = sticker_config.get('qr_mode_enabled', cfg.qr_mode_enabled)
                cfg.qr_placeholder_text = sticker_config.get('qr_placeholder_text', cfg.qr_placeholder_text)
                cfg.qr_placeholder_bg = sticker_config.get('qr_placeholder_bg', cfg.qr_placeholder_bg)
                cfg.qr_image_path = sticker_config.get('qr_image_path', cfg.qr_image_path)
                cfg.preview_scale = sticker_config.get('preview_scale', cfg.preview_scale)
                cfg.export_exact_three_rows = sticker_config.get('export_exact_three_rows', cfg.export_exact_three_rows)
                cfg.export_margin_mm = sticker_config.get('export_margin_mm', cfg.export_margin_mm)
                cfg.export_gap_mm = sticker_config.get('export_gap_mm', cfg.export_gap_mm)
                cfg.export_min_scale = sticker_config.get('export_min_scale', cfg.export_min_scale)
                
                # Count Sticker Parameter wiederherstellen
                count_cfg.width_mm = sticker_config.get('count_width_mm', count_cfg.width_mm)
                count_cfg.height_mm = sticker_config.get('count_height_mm', count_cfg.height_mm)
                count_cfg.dpi = sticker_config.get('count_dpi', count_cfg.dpi)
                count_cfg.corner_radius = sticker_config.get('count_corner_radius', count_cfg.corner_radius)
                count_cfg.outline_width = sticker_config.get('count_outline_width', count_cfg.outline_width)
                count_cfg.font_path = sticker_config.get('count_font_path', count_cfg.font_path)
                count_cfg.auto_adjust = sticker_config.get('count_auto_adjust', count_cfg.auto_adjust)
                count_cfg.font_size_mm = sticker_config.get('count_font_size_mm', count_cfg.font_size_mm)
                count_cfg.line_height_mm = sticker_config.get('count_line_height_mm', count_cfg.line_height_mm)
                count_cfg.header_text = sticker_config.get('count_header_text', count_cfg.header_text)
                count_cfg.bg_color = sticker_config.get('count_bg_color', count_cfg.bg_color)
                count_cfg.stripe_color = sticker_config.get('count_stripe_color', count_cfg.stripe_color)
                count_cfg.show_stripes = sticker_config.get('count_show_stripes', count_cfg.show_stripes)
                count_cfg.header_margin_mm = sticker_config.get('count_header_margin_mm', count_cfg.header_margin_mm)
                count_cfg.text_spacing_mm = sticker_config.get('count_text_spacing_mm', count_cfg.text_spacing_mm)
                
                # Count Generator neu erstellen mit neuer Config
                from generators.count_manager import CountStickerGenerator
                self.parent_app.count_generator = CountStickerGenerator(count_cfg)
                
                # LOTO-Modus wiederherstellen - NUR wenn explizit gespeichert
                if 'loto_mode_single' in sticker_config:
                    loto_mode_single = sticker_config.get('loto_mode_single')
                    logger.debug(f"Config: loto_mode_single={loto_mode_single} (aus gespeicherter Config)")
                    if hasattr(self.parent_app, 'single_loto_radio') and hasattr(self.parent_app, 'multi_loto_radio'):
                        if loto_mode_single:
                            self.parent_app.single_loto_radio.setChecked(True)
                            logger.debug("Single LOTO Radio aktiviert")
                        else:
                            self.parent_app.multi_loto_radio.setChecked(True)
                            logger.debug("Multi LOTO Radio aktiviert")
                        logger.debug(f"Nach Setzen: Single={self.parent_app.single_loto_radio.isChecked()}, Multi={self.parent_app.multi_loto_radio.isChecked()}")
                    # _on_loto_mode_changed aufrufen, da clicked-Signal bei setChecked nicht feuert
                    if hasattr(self.parent_app, '_on_loto_mode_changed'):
                        mode = 'single' if loto_mode_single else 'multi'
                        self.parent_app._on_loto_mode_changed(mode)
                        logger.debug(f"LOTO Modus synchronisiert: {mode}")
                else:
                    logger.debug("loto_mode_single nicht in Config - Radio-Buttons bleiben unverändert")
                
                # UI aktualisieren (falls Spinboxes etc. vorhanden)
                self.parent_app.sticker_service.generator._qr_cache.clear()
                
                # Count-Vorschau aktualisieren
                if hasattr(self.parent_app, 'safe_update_count_preview'):
                    self.parent_app.safe_update_count_preview()
                
                logger.debug(f"Sticker-Config (inkl. Count) wiederhergestellt für Equipment: {equipment_name}")
            except Exception as e:
                logger.error(f"Fehler beim Wiederherstellen der Config: {e}")
        
        # QR-Code im Generator setzen/zurücksetzen (nur wenn keine volle Config geladen wurde oder kein QR in Config)
        if hasattr(self.parent_app, 'sticker_service') and (not load_config or not sticker_config):
            try:
                if qr_path and qr_path.strip():
                    self.parent_app.sticker_service.generator.cfg.qr_mode_enabled = True
                    self.parent_app.sticker_service.generator.cfg.qr_image_path = qr_path
                    logger.debug(f"QR-Code für Equipment gesetzt: {qr_path}")
                else:
                    self.parent_app.sticker_service.generator.cfg.qr_mode_enabled = False
                    self.parent_app.sticker_service.generator.cfg.qr_image_path = None
                    logger.debug("QR-Code deaktiviert (kein QR hinterlegt)")
                self.parent_app.sticker_service.generator._qr_cache.clear()
            except Exception as e:
                logger.error(f"Fehler beim Setzen des QR-Codes: {e}")
        
        # Nutze Parent-App zum Hinzufügen
        if hasattr(self.parent_app, 'energy_entry'):
            self.parent_app.energy_entry.setText(energy_id)
        if hasattr(self.parent_app, 'equipment_entry'):
            self.parent_app.equipment_entry.setText(equipment_name)
        if hasattr(self.parent_app, 'description_entry'):
            self.parent_app.description_entry.setText(description or '')
        if hasattr(self.parent_app, 'symbol_combo'):
            index = self.parent_app.symbol_combo.findText(symbol_type.capitalize(), Qt.MatchFlag.MatchFixedString)
            if index < 0:
                # Fallback: case-insensitive Suche
                for i in range(self.parent_app.symbol_combo.count()):
                    if self.parent_app.symbol_combo.itemText(i).upper() == symbol_type.upper():
                        index = i
                        break
            if index >= 0:
                self.parent_app.symbol_combo.setCurrentIndex(index)
        
        # Auto-Add wenn gewünscht
        if hasattr(self.parent_app, 'add_to_collection'):
            if hasattr(self.parent_app, 'register_collection_source'):
                self.parent_app.register_collection_source(data.get('system', ''))
            self.parent_app.add_to_collection(auto_add_count=auto_add_count)
    
    def _rename_item(self, item: QTreeWidgetItem):
        """Item umbenennen"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        item_type = data.get('type', '')
        current_name = data.get('name', '')
        
        new_name, ok = QInputDialog.getText(
            self.equipment_tree,
            "Umbenennen",
            f"Neuer Name für '{current_name}':",
            text=current_name
        )
        
        if not ok or not new_name or new_name == current_name:
            return
        
        try:
            if item_type == 'location':
                self.equipment_manager.rename_location(current_name, new_name)
            elif item_type == 'system':
                location = data['location']
                self.equipment_manager.rename_system(location, current_name, new_name)
            elif item_type == 'equipment':
                location = data['location']
                system = data['system']
                self.equipment_manager.rename_equipment(location, system, current_name, new_name)
            
            self.refresh_tree()
            
        except Exception as e:
            QMessageBox.critical(
                self.equipment_tree,
                "Fehler",
                f"Fehler beim Umbenennen: {e}"
            )
    
    def _edit_equipment_properties(self, item: QTreeWidgetItem):
        """Equipment-Eigenschaften bearbeiten"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        
        if data.get('type') != 'equipment':
            return
        
        location = data['location']
        system = data['system']
        equipment_name = data['name']
        current_energy_id = data.get('energy_id', '')
        current_symbol = data.get('symbol_type', 'ELECTRIC')
        
        # Energy-ID bearbeiten
        new_energy_id, ok1 = QInputDialog.getText(
            self.equipment_tree,
            "Energy-ID bearbeiten",
            f"Energy-ID für '{equipment_name}':",
            text=current_energy_id
        )
        
        if ok1:
            # Symbol-Typ bearbeiten
            new_symbol, ok2 = QInputDialog.getText(
                self.equipment_tree,
                "Symbol-Typ bearbeiten",
                "Symbol-Typ:",
                text=current_symbol
            )
            
            if ok2:
                # Equipment-Daten aktualisieren
                equipment_list = self.equipment_manager.get_equipment(location, system)
                equipment_obj = next((e for e in equipment_list if e.get('name') == equipment_name), None)
                
                if equipment_obj:
                    equipment_obj['energy_id'] = new_energy_id
                    equipment_obj['symbol_type'] = new_symbol
                    self.refresh_tree()
    
    def _delete_item(self, item: QTreeWidgetItem):
        """Item löschen"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        item_type = data.get('type', '')
        name = data.get('name', '')
        
        reply = QMessageBox.question(
            self.equipment_tree,
            "Löschen bestätigen",
            f"{item_type.capitalize()} '{name}' wirklich löschen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            if item_type == 'location':
                self.equipment_manager.remove_location(name)
            elif item_type == 'system':
                location = data['location']
                self.equipment_manager.remove_system(location, name)
            elif item_type == 'equipment':
                location = data['location']
                system = data['system']
                self.equipment_manager.remove_equipment(location, system, name)
            
            self.refresh_tree()
            
        except Exception as e:
            QMessageBox.critical(
                self.equipment_tree,
                "Fehler",
                f"Fehler beim Löschen: {e}"
            )
    
    def _delete_selected_items(self):
        """Mehrere ausgewählte Items löschen"""
        if not self.equipment_tree:
            return
        
        selected_items = self.equipment_tree.selectedItems()
        if not selected_items:
            return
        
        # Nur Equipments sammeln
        items_to_delete = []
        for item in selected_items:
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get('type') == 'equipment':
                items_to_delete.append({
                    'location': data.get('location', ''),
                    'system': data.get('system', ''),
                    'name': data.get('name', data.get('equipment', ''))
                })
        
        if not items_to_delete:
            return
        
        # Bestätigung
        reply = QMessageBox.question(
            self.equipment_tree,
            "Löschen bestätigen",
            f"{len(items_to_delete)} Equipment(s) wirklich löschen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Löschen
        deleted = 0
        for item_data in items_to_delete:
            try:
                self.equipment_manager.remove_equipment(
                    item_data['location'],
                    item_data['system'],
                    item_data['name']
                )
                deleted += 1
            except Exception as e:
                logger.warning(f"Fehler beim Löschen von {item_data['name']}: {e}")
        
        self.refresh_tree()
        
        if deleted > 0:
            self._show_styled_info_dialog("Gelöscht", f"{deleted} Equipment(s) gelöscht.")

    def _on_tree_selection_changed(self):
        """Tree-Selection hat sich geändert"""
        self._on_tree_select()
    
    def _auto_group_equipment(self, system_item: QTreeWidgetItem):
        """Equipment innerhalb eines Systems automatisch nach gemeinsamen Mustern gruppieren"""
        import re
        from collections import defaultdict, Counter
        
        data = system_item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get('type') != 'system':
            return
        
        location_name = data.get('location')
        system_name = data.get('name')
        
        # Sammle alle Equipment-Items
        equipment_list = []
        for i in range(system_item.childCount()):
            child = system_item.child(i)
            if child:
                child_data = child.data(0, Qt.ItemDataRole.UserRole)
                if child_data and child_data.get('type') == 'equipment':
                    equipment_list.append(child_data)
        
        if not equipment_list:
            QMessageBox.information(
                self.equipment_tree,
                "Info",
                "Keine Equipment-Items zum Gruppieren gefunden."
            )
            return
        
        def extract_all_tokens(name: str) -> set:
            """Extrahiert ALLE möglichen Tokens aus einem Namen für Gruppierung.
            
            Findet:
            - Buchstaben-Sequenzen (ELEC, DP, ALFEN, UV, DBY)
            - Zahlen-Sequenzen (1, 2, 0001, 0021)
            - Buchstaben+Zahlen Kombinationen (UV-1, UV-2, DBY8)
            - Segmente nach Punkt-Trennung
            """
            tokens = set()
            
            # Normalisiere den Namen
            normalized = re.sub(r'\.\s*-\s*', '.', name)  # "ELEC.DP. - UV-1" -> "ELEC.DP.UV-1"
            normalized = re.sub(r'\s+', '', normalized)
            
            # 1. Alle Punkt-getrennten Segmente
            segments = [s for s in normalized.split('.') if s]
            for seg in segments:
                seg_upper = seg.upper()
                if len(seg_upper) >= 2:
                    tokens.add(seg_upper)
                    
                    # Auch ohne langes numerisches Suffix (DBY8_0001 -> DBY8)
                    base = re.sub(r'[_-]\d{3,}$', '', seg_upper)  # Nur 3+ stellige Suffixe entfernen
                    if base and len(base) >= 2 and base != seg_upper:
                        tokens.add(base)
            
            # 2. Buchstaben-Zahlen Kombinationen (UV-1, UV-2, KVS-1, DBY8)
            # Pattern: 2+ Buchstaben, dann optional Trennzeichen, dann 1-2 Ziffern
            patterns = re.findall(r'([A-Za-z]{2,})[_-]?(\d{1,2})(?!\d)', normalized)
            for letters, digits in patterns:
                # BEIDE Varianten speichern: mit und ohne Bindestrich
                token_with_dash = f"{letters.upper()}-{digits}"
                token_no_dash = f"{letters.upper()}{digits}"
                tokens.add(token_with_dash)
                tokens.add(token_no_dash)
            
            # 3. Reine Buchstaben-Sequenzen (mind. 3 Zeichen, um Noise zu vermeiden)
            letter_seqs = re.findall(r'[A-Za-z]{3,}', normalized)
            for seq in letter_seqs:
                tokens.add(seq.upper())
            
            return tokens
        
        # Sammle alle Tokens aus allen Equipment-Namen
        names = [equip.get('name', '') for equip in equipment_list]
        total_items = len(names)
        token_counts = defaultdict(int)
        token_items = defaultdict(set)  # Welche Items haben welchen Token
        
        for idx, name in enumerate(names):
            tokens = extract_all_tokens(name)
            for token in tokens:
                token_counts[token] += 1
                token_items[token].add(idx)
        
        # Tokens die für Gruppierung sinnvoll sind:
        # - Kommen in mindestens 2 Items vor (count >= 2)
        # - Kommen NICHT in allen Items vor (count < total) -> sonst keine Unterscheidung möglich
        grouping_options = []
        for token, count in sorted(token_counts.items(), key=lambda x: (-x[1], x[0])):
            if count >= 2 and count < total_items:
                without_count = total_items - count
                grouping_options.append((token, count, without_count))
        
        # Dialog: Präzise Gruppierungsauswahl mit Preview
        from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                                      QListWidget, QDialogButtonBox, QListWidgetItem,
                                      QLineEdit, QGroupBox, QSplitter, QPushButton, QWidget)
        
        dialog = QDialog(self.equipment_tree)
        dialog.setWindowTitle("Equipment gruppieren")
        dialog.setMinimumWidth(800)
        dialog.setMinimumHeight(600)
        
        layout = QVBoxLayout(dialog)
        
        # Suchfeld für eigenen Filter
        search_layout = QHBoxLayout()
        search_label = QLabel("Suchbegriff (enthält):")
        search_input = QLineEdit()
        search_input.setPlaceholderText("z.B. DBY8, UV-1, ALFEN...")
        search_layout.addWidget(search_label)
        search_layout.addWidget(search_input)
        layout.addLayout(search_layout)
        
        # Splitter für die zwei Listen
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Linke Seite: Vorgeschlagene Tokens
        left_group = QGroupBox("Gefundene Gemeinsamkeiten")
        left_layout = QVBoxLayout(left_group)
        token_list = QListWidget()
        for token, with_count, without_count in grouping_options:
            item = QListWidgetItem(f"{token}  ({with_count} Items)")
            item.setData(Qt.ItemDataRole.UserRole, token)
            token_list.addItem(item)
        if grouping_options:
            token_list.setCurrentRow(0)
        left_layout.addWidget(token_list)
        splitter.addWidget(left_group)
        
        # Rechte Seite: Preview der Gruppierung
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Gruppe "MIT" dem Merkmal
        with_group = QGroupBox("Gruppe: [Merkmal]")
        with_layout = QVBoxLayout(with_group)
        with_list = QListWidget()
        with_layout.addWidget(with_list)
        right_layout.addWidget(with_group)
        
        # Gruppe "OHNE" das Merkmal
        without_group = QGroupBox("Gruppe: Andere")
        without_layout = QVBoxLayout(without_group)
        without_list = QListWidget()
        without_layout.addWidget(without_list)
        right_layout.addWidget(without_group)
        
        splitter.addWidget(right_widget)
        splitter.setSizes([300, 500])
        layout.addWidget(splitter)
        
        # Funktion zum Aktualisieren der Preview
        def update_preview(search_text: str = None):
            with_list.clear()
            without_list.clear()
            
            # Bestimme den Suchtext
            if search_text is None:
                search_text = search_input.text().strip().upper()
            
            manual_text = search_input.text().strip().upper()
            use_token_match = not manual_text

            if not search_text:
                # Wenn kein Suchtext, verwende ausgewählten Token
                current_item = token_list.currentItem()
                if current_item:
                    search_text = current_item.data(Qt.ItemDataRole.UserRole)

            if not search_text:
                return

            with_group.setTitle(f"Gruppe: {search_text}")

            # Gruppiere Items (Token-Match für Listen-Auswahl, Substring für manuelle Eingabe)
            with_items = []
            without_items = []

            if use_token_match and search_text in token_items:
                with_indices = token_items[search_text]
                for idx, name in enumerate(names):
                    if idx in with_indices:
                        with_items.append(name)
                    else:
                        without_items.append(name)
            else:
                for name in names:
                    if search_text.upper() in name.upper():
                        with_items.append(name)
                    else:
                        without_items.append(name)
            
            # Fülle Listen
            for name in with_items:
                with_list.addItem(name)
            for name in without_items:
                without_list.addItem(name)
            
            # Update Titel mit Anzahl
            with_group.setTitle(f"Gruppe: {search_text} ({len(with_items)} Items)")
            without_group.setTitle(f"Gruppe: Andere ({len(without_items)} Items)")
        
        # Verbinde Signale
        token_list.currentItemChanged.connect(lambda: update_preview())
        search_input.textChanged.connect(lambda text: update_preview(text.strip().upper() if text.strip() else None))
        
        # Initial Preview
        update_preview()
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        
        # Bestimme den finalen Suchtext
        selected_token = search_input.text().strip().upper()
        if not selected_token:
            current_item = token_list.currentItem()
            if current_item:
                selected_token = current_item.data(Qt.ItemDataRole.UserRole)
        
        if not selected_token:
            return
        
        # Gruppiere: Token-Match für Listen-Auswahl, Substring für manuelle Eingabe
        manual_text = search_input.text().strip().upper()
        use_token_match = not manual_text
        
        # Erstelle Gruppen basierend auf dem gewählten Token
        groups = defaultdict(list)
        name_to_equip = {equip.get('name', ''): equip for equip in equipment_list}
        
        for name_idx, name in enumerate(names):
            if use_token_match and selected_token in token_items:
                group_key = selected_token if name_idx in token_items[selected_token] else "Andere"
            else:
                group_key = selected_token if selected_token.upper() in name.upper() else "Andere"
            if name in name_to_equip:
                groups[group_key].append(name_to_equip[name])
        
        def energy_id_sort_key(equip: dict) -> tuple:
            """Sortiert nach Energy-ID natürlich (E1, E2, ... E10, E11)"""
            energy_id = equip.get('energy_id', '') or ''
            parts = re.split(r'(\d+)', energy_id.upper())
            key = []
            for part in parts:
                if part.isdigit():
                    key.append(int(part))
                else:
                    key.append(part)
            return tuple(key)
        
        def natural_sort_key(text: str) -> tuple:
            """Natürliche Sortierung für Gruppennamen (KVS-1, KVS-2, ... KVS-10)"""
            parts = re.split(r'(\d+)', text)
            key = []
            for part in parts:
                if part.isdigit():
                    key.append(int(part))
                else:
                    key.append(part)
            return tuple(key)
        
        # Sortiere Items in jeder Gruppe nach Energy-ID
        for key in groups:
            groups[key].sort(key=energy_id_sort_key)
        
        # Sortiere Gruppen natürlich (KVS-1, KVS-2, ... KVS-10)
        sorted_groups = sorted(groups.items(), key=lambda x: natural_sort_key(x[0]))
        
        # Zeige Dialog mit Gruppierungsvorschau
        group_info = []
        for key, items in sorted_groups:
            group_info.append(f"{key}: {len(items)} Items")
        
        msg = "Gefundene Gruppen:\n\n" + "\n".join(group_info)
        msg += "\n\nMöchten Sie neue Systeme für jede Gruppe erstellen?"
        
        reply = QMessageBox.question(
            self.equipment_tree,
            "Equipment gruppieren",
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Erstelle neue Systeme für jede Gruppe (in natürlicher Reihenfolge)
        try:
            for group_key, items in sorted_groups:
                if group_key == "Andere" and len(groups) > 1:
                    # "Andere" Items im Original-System lassen
                    continue
                
                new_system_name = f"{system_name} - {group_key}"
                
                # System hinzufügen (falls nicht existiert)
                self.equipment_manager.add_system(location_name, new_system_name)
                
                # Equipment in neue Gruppe verschieben (sortiert nach Energy-ID)
                for equip in items:
                    # Equipment zur neuen Gruppe hinzufügen
                    self.equipment_manager.add_equipment(
                        location_name,
                        new_system_name,
                        equip.get('name', ''),
                        equip.get('energy_id', ''),
                        equip.get('symbol_type', ''),
                        equip.get('description', '')
                    )
                    
                    # Equipment aus Original-System entfernen
                    self.equipment_manager.remove_equipment(
                        location_name,
                        system_name,
                        equip.get('name', '')
                    )
            
            self.refresh_tree()
            QMessageBox.information(
                self.equipment_tree,
                "Erfolg",
                f"{len(groups)} Gruppen erstellt."
            )
            
        except Exception as e:
            logger.error(f"Error grouping equipment: {e}", exc_info=True)
            QMessageBox.critical(
                self.equipment_tree,
                "Fehler",
                f"Fehler beim Gruppieren: {e}"
            )
    
    def _manage_qr_code(self, item):
        """Öffnet den QR-Code Verwaltungsdialog"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get('type') != 'equipment':
            QMessageBox.warning(self.equipment_tree, "Fehler", "Bitte wählen Sie ein Equipment aus")
            return
        
        from dialogs.qr_code_dialog import QRCodeDialog
        
        equipment_name = data.get('name', '')  # KORRIGIERT: 'name' statt 'equipment'
        location = data.get('location', '')
        system = data.get('system', '')
        
        # Hole aktuellen QR-Pfad
        current_qr_path = ""
        try:
            equipment_list = self.equipment_manager.get_equipment(location, system)
            logger.debug(f"QR: Equipment List für {system}: {equipment_list}")
            for eq in equipment_list:
                if eq.get('name', '') == equipment_name:
                    current_qr_path = eq.get('qr_path', '')
                    logger.debug(f"QR: Gefunden! Equipment={equipment_name}, qr_path={current_qr_path}")
                    break
            if not current_qr_path:
                logger.debug(f"QR: KEIN QR-PATH für {equipment_name} gefunden!")
        except Exception as e:
            logger.error(f"QR: Exception beim Laden: {e}")
            pass
        
        # Öffne Dialog
        dialog = QRCodeDialog(self.equipment_tree, equipment_name, current_qr_path)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Hole neuen QR-Pfad
            new_qr_path = dialog.get_qr_path() or ""
            
            # Aktualisiere im Equipment Manager
            try:
                equipment_list = self.equipment_manager.get_equipment(location, system)
                for eq in equipment_list:
                    if eq.get('name', '') == equipment_name:
                        eq['qr_path'] = new_qr_path
                        break
                
                self.equipment_manager.save()
                QMessageBox.information(self.equipment_tree, "Erfolg", f"QR-Code für '{equipment_name}' aktualisiert")
                
            except Exception as e:
                QMessageBox.critical(self.equipment_tree, "Fehler", f"Fehler beim Speichern: {str(e)}")
    
    def _assign_qr_code_quick(self, item):
        """Schnellzuweisung eines QR-Codes per Dateidialog"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get('type') != 'equipment':
            QMessageBox.warning(self.equipment_tree, "Fehler", "Bitte wählen Sie ein Equipment aus")
            return
        
        from PyQt6.QtWidgets import QFileDialog
        from pathlib import Path
        
        equipment_name = data.get('equipment', '')
        location = data.get('location', '')
        system = data.get('system', '')
        
        # Dateidialog öffnen
        file_path, _ = QFileDialog.getOpenFileName(
            self.equipment_tree,
            f"QR-Code für '{equipment_name}' auswählen",
            str(Path.home()),
            "Bilder (*.png *.jpg *.jpeg *.bmp *.gif);;PDF Dateien (*.pdf);;Alle Dateien (*)"
        )
        
        if not file_path:
            return
        
        # Speichere im Equipment Manager
        try:
            equipment_list = self.equipment_manager.get_equipment(location, system)
            for eq in equipment_list:
                if eq.get('name', '') == equipment_name:
                    eq['qr_path'] = file_path
                    break
            
            self.equipment_manager.save()
            QMessageBox.information(
                self.equipment_tree, 
                "Erfolg", 
                f"QR-Code erfolgreich zugewiesen!\n\nEquipment: {equipment_name}\nDatei: {Path(file_path).name}"
            )
            
        except Exception as e:
            QMessageBox.critical(self.equipment_tree, "Fehler", f"Fehler beim Speichern: {str(e)}")
    
    def _delete_qr_code(self, item):
        """Löscht die QR-Code Zuweisung"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get('type') != 'equipment':
            QMessageBox.warning(self.equipment_tree, "Fehler", "Bitte wählen Sie ein Equipment aus")
            return
        
        equipment_name = data.get('equipment', '')
        location = data.get('location', '')
        system = data.get('system', '')
        
        reply = QMessageBox.question(
            self.equipment_tree,
            "QR-Code löschen",
            f"QR-Code Zuweisung für '{equipment_name}' wirklich löschen?\n\n"
            "Die Bilddatei bleibt erhalten, nur die Verknüpfung wird gelöscht.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Lösche QR-Pfad
        try:
            equipment_list = self.equipment_manager.get_equipment(location, system)
            for eq in equipment_list:
                if eq.get('name', '') == equipment_name:
                    eq['qr_path'] = ""
                    break
            
            self.equipment_manager.save()
            QMessageBox.information(self.equipment_tree, "Erfolg", f"QR-Code für '{equipment_name}' entfernt")
            
        except Exception as e:
            QMessageBox.critical(self.equipment_tree, "Fehler", f"Fehler beim Speichern: {str(e)}")
    
    # ========== SYSTEM QR-CODE FUNKTIONEN ==========
    
    def _manage_system_qr_code(self, item):
        """Öffnet den QR-Code Verwaltungsdialog für ein System"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get('type') != 'system':
            QMessageBox.warning(self.equipment_tree, "Fehler", "Bitte wählen Sie ein System aus")
            return
        
        from dialogs.qr_code_dialog import QRCodeDialog
        
        system_name = data.get('system', '')
        location = data.get('location', '')
        
        # Hole aktuellen QR-Pfad
        current_qr_path = ""
        try:
            system_obj = self.equipment_manager.get_system(location, system_name)
            if system_obj:
                current_qr_path = system_obj.get('qr_path', '')
        except Exception:
            pass
        
        # Öffne Dialog
        dialog = QRCodeDialog(self.equipment_tree, system_name, current_qr_path)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Hole neuen QR-Pfad
            new_qr_path = dialog.get_qr_path() or ""
            
            # Aktualisiere im Equipment Manager
            try:
                self.equipment_manager.update_system_properties(
                    location, system_name, qr_path=new_qr_path
                )
                self.equipment_manager.save()
                QMessageBox.information(self.equipment_tree, "Erfolg", f"QR-Code für System '{system_name}' aktualisiert")
                
            except Exception as e:
                QMessageBox.critical(self.equipment_tree, "Fehler", f"Fehler beim Speichern: {str(e)}")
    
    def _assign_system_qr_code_quick(self, item):
        """Schnellzuweisung eines QR-Codes für ein System"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get('type') != 'system':
            QMessageBox.warning(self.equipment_tree, "Fehler", "Bitte wählen Sie ein System aus")
            return
        
        from PyQt6.QtWidgets import QFileDialog
        from pathlib import Path
        
        system_name = data.get('system', '')
        location = data.get('location', '')
        
        # Dateidialog öffnen
        file_path, _ = QFileDialog.getOpenFileName(
            self.equipment_tree,
            f"QR-Code für System '{system_name}' auswählen",
            str(Path.home()),
            "Bilder (*.png *.jpg *.jpeg *.bmp *.gif);;PDF Dateien (*.pdf);;Alle Dateien (*)"
        )
        
        if not file_path:
            return
        
        # Speichere im Equipment Manager
        try:
            self.equipment_manager.update_system_properties(
                location, system_name, qr_path=file_path
            )
            self.equipment_manager.save()
            QMessageBox.information(
                self.equipment_tree, 
                "Erfolg", 
                f"QR-Code erfolgreich zugewiesen!\n\nSystem: {system_name}\nDatei: {Path(file_path).name}"
            )
            
        except Exception as e:
            QMessageBox.critical(self.equipment_tree, "Fehler", f"Fehler beim Speichern: {str(e)}")
    
    def _delete_system_qr_code(self, item):
        """Löscht die QR-Code Zuweisung eines Systems"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get('type') != 'system':
            QMessageBox.warning(self.equipment_tree, "Fehler", "Bitte wählen Sie ein System aus")
            return
        
        system_name = data.get('system', '')
        location = data.get('location', '')
        
        reply = QMessageBox.question(
            self.equipment_tree,
            "QR-Code löschen",
            f"QR-Code Zuweisung für System '{system_name}' wirklich löschen?\n\n"
            "Die Bilddatei bleibt erhalten, nur die Verknüpfung wird gelöscht.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Lösche QR-Pfad
        try:
            self.equipment_manager.update_system_properties(
                location, system_name, qr_path=""
            )
            self.equipment_manager.save()
            QMessageBox.information(self.equipment_tree, "Erfolg", f"QR-Code für System '{system_name}' entfernt")
            
        except Exception as e:
            QMessageBox.critical(self.equipment_tree, "Fehler", f"Fehler beim Speichern: {str(e)}")

    def select_equipment_dialog(self):
        """Equipment-Auswahl-Dialog öffnen"""
        from dialogs.equipment_dialog import EquipmentSelectionDialog
        from ui.theme import Theme

        dialog = EquipmentSelectionDialog(self.parent_app, self.equipment_manager, Theme.LIGHT)
        dialog.setWindowTitle("Ziel-System auswählen")
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_data:
            return dialog.selected_data
        return None

    def select_equipment_for_form(self):
        """Öffnet Equipment-Auswahl und befüllt das Hauptformular."""
        data = self.select_equipment_dialog()
        if not data:
            return

        app = self.parent_app
        if app is None:
            return

        # Equipment Name
        if hasattr(app, 'equipment_entry') and app.equipment_entry:
            app.equipment_entry.setText(data.get('equipment_name', ''))

        # Energy ID
        if hasattr(app, 'energy_entry') and app.energy_entry and data.get('energy_id'):
            app.energy_entry.setText(data.get('energy_id'))

        # Description
        if hasattr(app, 'description_entry') and app.description_entry:
            app.description_entry.setText("MAIN SWITCH")

        # Symbol Type
        symbol_type = data.get('symbol_type', '')
        if hasattr(app, 'symbol_combo') and app.symbol_combo and symbol_type:
            symbol_name = symbol_type.capitalize()
            index = app.symbol_combo.findText(symbol_name)
            if index >= 0:
                app.symbol_combo.setCurrentIndex(index)

    def import_equipment_from_excel(self):
        """Excel-Import für Equipment - aktuell deaktiviert."""
        app = self.parent_app
        if app and hasattr(app, '_create_styled_msgbox'):
            msg = app._create_styled_msgbox("Info", "Excel-Import ist derzeit nicht verfügbar.")
            msg.exec()
            return

        QMessageBox.information(self.equipment_tree, "Info", "Excel-Import ist derzeit nicht verfügbar.")

    def export_equipment_database(self):
        """Exportiert die Equipment-Datenbank als JSON-Datei."""
        try:
            import json

            file_path, _ = QFileDialog.getSaveFileName(
                self.parent_app,
                "Equipment-Datenbank exportieren",
                "equipment_backup.json",
                "JSON Dateien (*.json);;Alle Dateien (*.*)"
            )

            if not file_path:
                return

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.equipment_manager.equipment_data, f, indent=2, ensure_ascii=False)

            if self.parent_app and hasattr(self.parent_app, '_create_styled_msgbox'):
                msg = self.parent_app._create_styled_msgbox(
                    "Erfolg",
                    f"Equipment-Datenbank erfolgreich exportiert!\n\n{file_path}"
                )
                msg.exec()
            else:
                QMessageBox.information(self.equipment_tree, "Erfolg", f"Export erfolgreich:\n{file_path}")

        except Exception as e:
            logger.error(f"Export fehlgeschlagen: {e}", exc_info=True)
            if self.parent_app and hasattr(self.parent_app, '_create_styled_msgbox'):
                msg = self.parent_app._create_styled_msgbox("Fehler", f"Export fehlgeschlagen:\n{str(e)}")
                msg.exec()
            else:
                QMessageBox.critical(self.equipment_tree, "Fehler", f"Export fehlgeschlagen:\n{str(e)}")

    def import_equipment_database(self):
        """Importiert Equipment-Datenbank aus JSON-Datei."""
        try:
            from PyQt6.QtWidgets import QFileDialog, QDialog, QVBoxLayout, QHBoxLayout, QLabel
            from ui.glass_button import GlassGlowButton
            import json

            file_path, _ = QFileDialog.getOpenFileName(
                self.parent_app,
                "Equipment-Datenbank importieren",
                "",
                "JSON Dateien (*.json);;Alle Dateien (*.*)"
            )

            if not file_path:
                return

            dialog = QDialog(self.parent_app)
            dialog.setWindowTitle("Import bestätigen")
            dialog.setModal(True)
            dialog.setFixedWidth(500)
            dialog.setStyleSheet("""
                QDialog {
                    background-color: #f4f6f9;
                }
                QLabel {
                    color: #2c3e50;
                }
            """)

            layout = QVBoxLayout(dialog)
            layout.setSpacing(15)
            layout.setContentsMargins(25, 20, 25, 20)

            question_label = QLabel("Möchten Sie die aktuelle Datenbank ersetzen\noder die Daten zusammenführen?")
            question_label.setStyleSheet("font-size: 13px; font-weight: bold;")
            layout.addWidget(question_label)

            info_label = QLabel("• Ersetzen = Alte Daten werden überschrieben\n• Zusammenführen = Neue Daten werden hinzugefügt")
            info_label.setStyleSheet("font-size: 11px; color: #666;")
            layout.addWidget(info_label)

            layout.addSpacing(10)

            button_layout = QHBoxLayout()
            button_layout.setSpacing(10)

            replace_btn = GlassGlowButton("Ändern")
            replace_btn.setFixedHeight(38)
            replace_btn.setMinimumWidth(140)

            merge_btn = GlassGlowButton("Zusammenführen")
            merge_btn.setFixedHeight(38)
            merge_btn.setMinimumWidth(180)

            cancel_btn = GlassGlowButton("Abbrechen")
            cancel_btn.setFixedHeight(38)
            cancel_btn.setMinimumWidth(120)

            dialog.result_action = None

            def on_replace():
                dialog.result_action = "replace"
                dialog.accept()

            def on_merge():
                dialog.result_action = "merge"
                dialog.accept()

            replace_btn.clicked.connect(on_replace)
            merge_btn.clicked.connect(on_merge)
            cancel_btn.clicked.connect(dialog.reject)

            button_layout.addWidget(replace_btn)
            button_layout.addWidget(merge_btn)
            button_layout.addStretch()
            button_layout.addWidget(cancel_btn)
            layout.addLayout(button_layout)

            if dialog.exec() != QDialog.DialogCode.Accepted:
                return

            action = dialog.result_action

            with open(file_path, 'r', encoding='utf-8') as f:
                imported_data = json.load(f)

            if not isinstance(imported_data, dict):
                raise ValueError("Ungültiges Dateiformat")

            if action == "replace":
                self.equipment_manager.equipment_data = imported_data
            else:
                for location, location_data in imported_data.items():
                    if location not in self.equipment_manager.equipment_data:
                        self.equipment_manager.equipment_data[location] = location_data
                    else:
                        existing_systems = self.equipment_manager.equipment_data[location].get('systems', [])
                        imported_systems = location_data.get('systems', [])

                        for imp_sys in imported_systems:
                            sys_exists = False
                            for ex_sys in existing_systems:
                                if ex_sys.get('name') == imp_sys.get('name'):
                                    ex_equip = ex_sys.get('equipment', [])
                                    imp_equip = imp_sys.get('equipment', [])

                                    for eq in imp_equip:
                                        eq_exists = any(e.get('name') == eq.get('name') for e in ex_equip)
                                        if not eq_exists:
                                            ex_equip.append(eq)

                                    ex_sys['equipment'] = ex_equip
                                    sys_exists = True
                                    break

                            if not sys_exists:
                                existing_systems.append(imp_sys)

                        self.equipment_manager.equipment_data[location]['systems'] = existing_systems

            self.equipment_manager.save()
            self.refresh_tree()

            count_locations = len(imported_data)
            if self.parent_app and hasattr(self.parent_app, '_create_styled_msgbox'):
                msg = self.parent_app._create_styled_msgbox(
                    "Erfolg",
                    f"Import erfolgreich!\n\n{count_locations} Standort(e) importiert."
                )
                msg.exec()
            else:
                QMessageBox.information(
                    self.equipment_tree,
                    "Erfolg",
                    f"Import erfolgreich!\n\n{count_locations} Standort(e) importiert."
                )

        except Exception as e:
            logger.error(f"Import fehlgeschlagen: {e}", exc_info=True)
            if self.parent_app and hasattr(self.parent_app, '_create_styled_msgbox'):
                msg = self.parent_app._create_styled_msgbox("Fehler", f"Import fehlgeschlagen:\n{str(e)}")
                msg.exec()
            else:
                QMessageBox.critical(self.equipment_tree, "Fehler", f"Import fehlgeschlagen:\n{str(e)}")
