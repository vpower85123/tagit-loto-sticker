"""
Equipment Dialog für Auswahl von Ausrüstung aus der Hierarchie.
"""

import logging
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QTreeWidget, QTreeWidgetItem, QPushButton, QMenu, QMessageBox
)

logger = logging.getLogger(__name__)
from PyQt6.QtCore import Qt, Qt as QtCore_Qt
from ui.components import ModernComboBox
from ui.glass_button import GlassGlowButton


class EquipmentSelectionDialog(QDialog):
    """Dialog zur Auswahl von Equipment aus der Hierarchie."""
    
    def __init__(self, parent, equipment_manager, theme):
        super().__init__(parent)
        self.equipment_manager = equipment_manager
        self.theme = theme
        self.selected_data = None
        
        self.setWindowTitle("Equipment auswählen")
        self.setModal(True)
        self.resize(760, 600)
        
        self._build_ui()
    
    def _build_ui(self):
        """UI aufbauen."""
        # Entferne Dark Mode - verwende immer Light Theme
        is_dark = False
        
        # Modernes Styling
        style = """
            QDialog {
                background-color: #f4f6f9;
                color: #2c3e50;
            }
            QLabel {
                color: #2c3e50;
                font-size: 14px;
                font-weight: 500;
            }
            /* Card Style for Tree Container */
            QFrame#TreeContainer {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 16px;
            }
            QTreeWidget {
                border: none;
                background-color: transparent;
                color: #2c3e50;
                font-size: 14px;
                outline: none;
            }
            QTreeWidget::item {
                padding: 10px;
                border-radius: 8px;
                margin: 2px 8px;
            }
            QTreeWidget::item:hover {
                background-color: #f0f2f5;
            }
            QTreeWidget::item:selected {
                background-color: #3498db;
                color: #ffffff;
            }
            /* Scrollbar Styling */
            QScrollBar:vertical {
                border: none;
                background: #f0f2f5;
                width: 10px;
                border-radius: 5px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #bdc3c7;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #95a5a6;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """
        
        self.setStyleSheet(style)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # --- Header Section ---
        header_layout = QHBoxLayout()
        
        # Title
        title_label = QLabel("Equipment auswählen")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # --- Filter Section ---
        filter_frame = QHBoxLayout()
        filter_frame.setSpacing(15)
        
        loc_label = QLabel("Standort:")
        loc_label.setStyleSheet("font-weight: bold;")
        filter_frame.addWidget(loc_label)
        
        self.location_combo = ModernComboBox(dark_mode=is_dark)
        self.location_combo.setMinimumWidth(250)
        try:
            locations = self.equipment_manager.get_all_locations()
            self.location_combo.addItems(locations)
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Fehler beim Laden der Standorte: {e}")
            return
        
        filter_frame.addWidget(self.location_combo)
        filter_frame.addStretch()
        layout.addLayout(filter_frame)
        
        # --- Path Display ---
        self.path_label = QLabel("Bitte wählen Sie ein Equipment aus...")
        self.path_label.setStyleSheet("""
            color: #7f8c8d; 
            font-style: italic; 
            padding: 8px 12px; 
            background: rgba(52, 152, 219, 0.1); 
            border-radius: 8px;
            border: 1px solid rgba(52, 152, 219, 0.2);
        """)
        layout.addWidget(self.path_label)
        
        # --- Tree Section ---
        from PyQt6.QtWidgets import QFrame
        tree_container = QFrame()
        tree_container.setObjectName("TreeContainer")
        tree_layout = QVBoxLayout(tree_container)
        tree_layout.setContentsMargins(4, 4, 4, 4)
        
        self.equipment_tree = QTreeWidget()
        self.equipment_tree.setHeaderHidden(True)
        self.equipment_tree.setContextMenuPolicy(QtCore_Qt.ContextMenuPolicy.CustomContextMenu)
        self.equipment_tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.equipment_tree.setIndentation(24)
        self.equipment_tree.setAlternatingRowColors(False)
        
        tree_layout.addWidget(self.equipment_tree)
        layout.addWidget(tree_container)
        
        # --- Footer / Buttons ---
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = GlassGlowButton("Abbrechen")
        cancel_btn.setMinimumWidth(250)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        select_btn = GlassGlowButton("✓ Auswählen")
        select_btn.setMinimumWidth(250)
        select_btn.setEnabled(False)
        select_btn.clicked.connect(self.accept)
        btn_layout.addWidget(select_btn)
        
        layout.addLayout(btn_layout)
        
        self.select_btn = select_btn

        # Connect signals
        self.location_combo.currentTextChanged.connect(self._populate_tree)
        self.equipment_tree.itemSelectionChanged.connect(self._on_item_clicked)
        self.equipment_tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.equipment_tree.customContextMenuRequested.connect(self._show_context_menu)
        
        # Initial population
        self._populate_tree()
    
    def _populate_tree(self):
        """Equipment Tree basierend auf Standort-Auswahl aktualisieren"""
        self.equipment_tree.clear()
        location = self.location_combo.currentText()
        if not location:
            return
        
        try:
            # Hole alle Systeme für den Standort
            systems = self.equipment_manager.get_system_names(location)
            
            for system_name in sorted(systems):
                # System als Top-Level Item
                system_item = QTreeWidgetItem([system_name])
                system_item.setData(0, Qt.ItemDataRole.UserRole, ('system', location, system_name))
                self.equipment_tree.addTopLevelItem(system_item)
                
                # Hole alle Betriebsmittel des Systems
                equipment_list = self.equipment_manager.get_equipment(location, system_name)

                def _energy_id_sort_key(eq):
                    energy_id = (eq.get('energy_id') or '').upper()
                    import re
                    match = re.match(r'E(\d+)', energy_id)
                    if match:
                        return (int(match.group(1)), energy_id)
                    return (float('inf'), energy_id)
                
                for eq in sorted(equipment_list, key=_energy_id_sort_key):
                    eq_name = eq.get('name', '')
                    eq_item = QTreeWidgetItem([eq_name])
                    eq_item.setData(0, Qt.ItemDataRole.UserRole, ('equipment', location, system_name, eq_name))
                    system_item.addChild(eq_item)
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren des Equipment Trees: {e}")

    def _on_item_clicked(self):
        """Handler für Klick auf Tree-Item"""
        current_item = self.equipment_tree.currentItem()
        selected_items = self.equipment_tree.selectedItems()
        if not current_item:
            self.path_label.setText("Bitte wählen Sie ein Equipment oder System aus...")
            self.select_btn.setEnabled(False)
            self.selected_data = None
            return

        # Mehrfachauswahl prüfen (nur Equipment-Items)
        if selected_items and len(selected_items) > 1:
            multi_equipment = []
            for sel in selected_items:
                data = sel.data(0, Qt.ItemDataRole.UserRole)
                if not data:
                    continue
                if data[0] == 'equipment':
                    location, system_name, equipment_name = data[1], data[2], data[3]
                    energy_id = ''
                    symbol_type = ''
                    try:
                        equipment_list = self.equipment_manager.get_equipment(location, system_name)
                        for eq in equipment_list:
                            if eq.get('name', '') == equipment_name:
                                energy_id = eq.get('energy_id', '')
                                symbol_type = eq.get('symbol_type', '')
                                break
                    except Exception:
                        pass
                    multi_equipment.append({
                        'name': equipment_name,
                        'energy_id': energy_id,
                        'symbol_type': symbol_type
                    })

            if multi_equipment:
                self.path_label.setText(f"Mehrfachauswahl: {len(multi_equipment)} Equipment")
                self.selected_data = {
                    'type': 'multi_equipment',
                    'equipment_list': multi_equipment
                }
                self.select_btn.setEnabled(True)
                return
        
        # Pfad zusammenbauen
        path_parts = []
        item = current_item
        while item:
            path_parts.append(item.text(0))
            item = item.parent()
        path_parts.reverse()
        self.path_label.setText(f"Gewählter Pfad: {' / '.join(path_parts)}")
        
        # Daten extrahieren
        data = current_item.data(0, Qt.ItemDataRole.UserRole)
        if data:
            item_type = data[0]
            
            if item_type == 'equipment':
                # Betriebsmittel wurde ausgewählt
                location, system_name, equipment_name = data[1], data[2], data[3]
                
                # Daten vorbereiten
                self.selected_data = {
                    'type': 'equipment',
                    'location': location,
                    'system_name': system_name,
                    'equipment_name': equipment_name,
                    'energy_id': '',
                    'symbol_type': ''
                }
                
                # Energie-ID und Symbol-Typ aus EquipmentManager holen
                try:
                    equipment_list = self.equipment_manager.get_equipment(location, system_name)
                    for eq in equipment_list:
                        if eq.get('name', '') == equipment_name:
                            self.selected_data['energy_id'] = eq.get('energy_id', '')
                            self.selected_data['symbol_type'] = eq.get('symbol_type', '')
                            break
                except Exception:
                    pass
                
                self.select_btn.setEnabled(True)
            elif item_type == 'system':
                # System wurde ausgewählt - lade alle Equipment in diesem System
                location, system_name = data[1], data[2]
                
                # Daten vorbereiten
                self.selected_data = {
                    'type': 'system',
                    'system_name': system_name,
                    'location': location,
                    'equipment_list': []
                }
                
                # Lade alle Equipment des Systems
                try:
                    equipment_list = self.equipment_manager.get_equipment(location, system_name)
                    for eq in equipment_list:
                        self.selected_data['equipment_list'].append({
                            'name': eq.get('name', ''),
                            'energy_id': eq.get('energy_id', ''),
                            'symbol_type': eq.get('symbol_type', '')
                        })
                except Exception:
                    pass
                
                self.select_btn.setEnabled(True)
            else:
                self.select_btn.setEnabled(False)
                self.selected_data = None
        else:
            self.select_btn.setEnabled(False)
            self.selected_data = None

    def _on_item_double_clicked(self, item, column):
        """Handler für Doppelklick"""
        self._on_item_clicked()
        if self.select_btn.isEnabled():
            self.accept()

    def _show_context_menu(self, pos):
        """Zeige Kontextmenü beim Rechtsklick"""
        item = self.equipment_tree.itemAt(pos)
        if not item:
            return
        
        # Stelle das Item als ausgewählt dar
        self.equipment_tree.setCurrentItem(item)
        self._on_item_clicked()
        
        # Erstelle Kontextmenü
        menu = QMenu(self)
        
        # Prüfe ob es ein Equipment-Item ist (für QR-Code Funktionen)
        data = item.data(0, Qt.ItemDataRole.UserRole)
        is_equipment = data and data[0] == 'equipment'
        
        # "Zur Sammlung hinzufügen" Aktion
        add_action = menu.addAction("Zur Sammlung hinzufügen")
        add_action.triggered.connect(self._add_to_collection_from_context)
        
        # QR-Code Aktionen nur für Equipment-Items
        if is_equipment:
            menu.addSeparator()
            
            # QR-Code anzeigen/bearbeiten
            qr_action = menu.addAction("QR-Code verwalten")
            qr_action.triggered.connect(self._manage_qr_code)
            
            # QR-Code zuweisen
            assign_qr_action = menu.addAction("QR-Code zuweisen")
            assign_qr_action.triggered.connect(self._assign_qr_code_quick)
            
            # Prüfe ob Equipment einen QR-Code hat
            location, system_name, equipment_name = data[1], data[2], data[3]
            equipment_list = self.equipment_manager.get_equipment(location, system_name)
            has_qr = False
            for eq in equipment_list:
                if eq.get('name', '') == equipment_name:
                    has_qr = bool(eq.get('qr_path', ''))
                    break
            
            if has_qr:
                # QR-Code löschen
                delete_qr_action = menu.addAction("QR-Code löschen")
                delete_qr_action.triggered.connect(self._delete_qr_code)
        
        # Zeige Menü
        global_pos = self.equipment_tree.mapToGlobal(pos)
        menu.exec(global_pos)
    
    def _accept_from_context(self):
        """Akzeptiere Auswahl aus Kontextmenü"""
        if self.select_btn.isEnabled():
            self.accept()
    
    def _add_to_collection_from_context(self):
        """Füge Equipment oder System direkt zur Sammlung hinzu"""
        if not self.selected_data:
            QMessageBox.warning(self, "Fehler", "Bitte wählen Sie ein Equipment oder System aus")
            return
        
        # Hole die Parent-App (MainApp)
        parent = self.parent()
        if not hasattr(parent, 'add_to_collection'):
            QMessageBox.warning(self, "Fehler", "Parent-App nicht gefunden")
            return
        
        try:
            item_type = self.selected_data.get('type', 'equipment')
            
            if item_type == 'equipment':
                # Einzelnes Equipment hinzufügen
                parent.energy_entry.setText(self.selected_data.get('energy_id', ''))
                parent.equipment_entry.setText(self.selected_data.get('equipment_name', ''))
                parent.add_to_collection()
                
                self.accept()
                QMessageBox.information(self, "Erfolg", "Equipment zur Sammlung hinzugefügt")
                
            elif item_type in ('system', 'multi_equipment'):
                # Alle Equipment hinzufügen
                equipment_list = self.selected_data.get('equipment_list', [])
                if not equipment_list:
                    QMessageBox.warning(self, "Fehler", "System enthält keine Equipment")
                    return
                
                added_count = 0
                for eq_data in equipment_list:
                    try:
                        parent.energy_entry.setText(eq_data.get('energy_id', ''))
                        parent.equipment_entry.setText(eq_data.get('name', ''))
                        parent.add_to_collection()
                        added_count += 1
                    except Exception as e:
                        logger.error(f"Fehler beim Hinzufügen von {eq_data.get('name', '')}: {e}")
                
                self.accept()
                QMessageBox.information(self, "Erfolg", f"{added_count} Equipment zur Sammlung hinzugefügt")
                
        except Exception as e:
            QMessageBox.warning(self, "Fehler", f"Fehler beim Hinzufügen: {e}")

    def get_selected_equipment(self):
        """Gibt das ausgewählte Equipment zurück."""
        return self.selected_data

    def _manage_qr_code(self):
        """Öffnet den QR-Code Verwaltungsdialog"""
        if not self.selected_data or self.selected_data.get('type') != 'equipment':
            QMessageBox.warning(self, "Fehler", "Bitte wählen Sie ein Equipment aus")
            return
        
        from dialogs.qr_code_dialog import QRCodeDialog
        
        equipment_name = self.selected_data.get('equipment_name', '')
        location = self.selected_data.get('location', '')
        system_name = self.selected_data.get('system_name', '')
        
        # Hole aktuellen QR-Pfad
        current_qr_path = ""
        try:
            equipment_list = self.equipment_manager.get_equipment(location, system_name)
            for eq in equipment_list:
                if eq.get('name', '') == equipment_name:
                    current_qr_path = eq.get('qr_path', '')
                    break
        except Exception:
            pass
        
        # Öffne Dialog
        dialog = QRCodeDialog(self, equipment_name, current_qr_path)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Hole neuen QR-Pfad
            new_qr_path = dialog.get_qr_path() or ""
            
            # Aktualisiere im Equipment Manager
            try:
                equipment_list = self.equipment_manager.get_equipment(location, system_name)
                for eq in equipment_list:
                    if eq.get('name', '') == equipment_name:
                        eq['qr_path'] = new_qr_path
                        break
                
                self.equipment_manager.save()
                QMessageBox.information(self, "Erfolg", f"QR-Code für '{equipment_name}' aktualisiert")
                
            except Exception as e:
                QMessageBox.critical(self, "Fehler", f"Fehler beim Speichern: {str(e)}")
    
    def _assign_qr_code_quick(self):
        """Schnellzuweisung eines QR-Codes per Dateidialog"""
        if not self.selected_data or self.selected_data.get('type') != 'equipment':
            QMessageBox.warning(self, "Fehler", "Bitte wählen Sie ein Equipment aus")
            return
        
        from PyQt6.QtWidgets import QFileDialog
        from pathlib import Path
        
        equipment_name = self.selected_data.get('equipment_name', '')
        location = self.selected_data.get('location', '')
        system_name = self.selected_data.get('system_name', '')
        
        # Dateidialog öffnen
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            f"QR-Code für '{equipment_name}' auswählen",
            str(Path.home()),
            "Bilder (*.png *.jpg *.jpeg *.bmp *.gif);;PDF Dateien (*.pdf);;Alle Dateien (*)"
        )
        
        if not file_path:
            return
        
        # Speichere im Equipment Manager
        try:
            equipment_list = self.equipment_manager.get_equipment(location, system_name)
            for eq in equipment_list:
                if eq.get('name', '') == equipment_name:
                    eq['qr_path'] = file_path
                    break
            
            self.equipment_manager.save()
            QMessageBox.information(
                self, 
                "Erfolg", 
                f"QR-Code erfolgreich zugewiesen!\n\nEquipment: {equipment_name}\nDatei: {Path(file_path).name}"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Fehler beim Speichern: {str(e)}")
    
    def _delete_qr_code(self):
        """Löscht die QR-Code Zuweisung"""
        if not self.selected_data or self.selected_data.get('type') != 'equipment':
            QMessageBox.warning(self, "Fehler", "Bitte wählen Sie ein Equipment aus")
            return
        
        equipment_name = self.selected_data.get('equipment_name', '')
        location = self.selected_data.get('location', '')
        system_name = self.selected_data.get('system_name', '')
        
        reply = QMessageBox.question(
            self,
            "QR-Code löschen",
            f"QR-Code Zuweisung für '{equipment_name}' wirklich löschen?\n\n"
            "Die Bilddatei bleibt erhalten, nur die Verknüpfung wird gelöscht.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Lösche QR-Pfad
        try:
            equipment_list = self.equipment_manager.get_equipment(location, system_name)
            for eq in equipment_list:
                if eq.get('name', '') == equipment_name:
                    eq['qr_path'] = ""
                    break
            
            self.equipment_manager.save()
            QMessageBox.information(self, "Erfolg", f"QR-Code für '{equipment_name}' entfernt")
            
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Fehler beim Speichern: {str(e)}")
