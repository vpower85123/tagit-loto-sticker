"""
Equipment Search Widget
Suchfeld für Equipment mit Auto-Complete
"""

import logging
from typing import List, Dict
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, 
    QListWidget, QListWidgetItem, QLabel, QPushButton
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon
import qtawesome as qta

from services import EquipmentService

logger = logging.getLogger(__name__)


class EquipmentSearchWidget(QWidget):
    """Widget für Equipment-Suche mit Live-Ergebnissen"""
    
    # Signals
    result_selected = pyqtSignal(dict)  # Selected result dict
    
    def __init__(self, equipment_service: EquipmentService, parent=None):
        super().__init__(parent)
        self.equipment_service = equipment_service
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._perform_search)
        
        self.init_ui()
    
    def init_ui(self):
        """UI erstellen"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Suchfeld
        search_layout = QHBoxLayout()
        search_layout.setSpacing(8)
        
        search_label = QLabel()
        search_label.setFixedWidth(24)
        search_label.setPixmap(qta.icon('ph.magnifying-glass', color='#666').pixmap(18, 18))
        search_layout.addWidget(search_label)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Equipment durchsuchen... (min. 2 Zeichen)")
        self.search_input.textChanged.connect(self._on_text_changed)
        self.search_input.returnPressed.connect(self._on_return_pressed)
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 8px 12px;
                border: 2px solid #dce1e6;
                border-radius: 8px;
                background: white;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #146B8A;
                background: #f8fafb;
            }
        """)
        search_layout.addWidget(self.search_input)
        
        # Clear button
        self.clear_btn = QPushButton("✕")
        self.clear_btn.setFixedSize(32, 32)
        self.clear_btn.clicked.connect(self.clear_search)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
                color: #999;
                font-size: 18px;
                border-radius: 16px;
            }
            QPushButton:hover {
                background: #f0f0f0;
                color: #333;
            }
        """)
        self.clear_btn.setVisible(False)
        search_layout.addWidget(self.clear_btn)
        
        layout.addLayout(search_layout)
        
        # Ergebnis-Label
        self.result_label = QLabel("")
        self.result_label.setStyleSheet("color: #666; font-size: 11px; padding: 4px;")
        self.result_label.setVisible(False)
        layout.addWidget(self.result_label)
        
        # Ergebnis-Liste
        self.result_list = QListWidget()
        self.result_list.setMaximumHeight(300)
        self.result_list.itemClicked.connect(self._on_result_clicked)
        self.result_list.itemDoubleClicked.connect(self._on_result_double_clicked)
        self.result_list.setStyleSheet("""
            QListWidget {
                border: 2px solid #dce1e6;
                border-radius: 8px;
                background: white;
                padding: 4px;
            }
            QListWidget::item {
                padding: 8px 12px;
                border-radius: 6px;
                margin: 2px;
            }
            QListWidget::item:hover {
                background: #f0f5f7;
            }
            QListWidget::item:selected {
                background: #146B8A;
                color: white;
            }
        """)
        self.result_list.setVisible(False)
        layout.addWidget(self.result_list)
    
    def _on_text_changed(self, text: str):
        """Text hat sich geändert - starte Debounce-Timer"""
        self.clear_btn.setVisible(len(text) > 0)
        
        if len(text) < 2:
            self.result_list.setVisible(False)
            self.result_label.setVisible(False)
            self._search_timer.stop()
            return
        
        # Debounce: Warte 300ms bevor Suche gestartet wird
        self._search_timer.start(300)
    
    def _perform_search(self):
        """Führe Suche aus"""
        query = self.search_input.text().strip()
        
        if len(query) < 2:
            return
        
        # Suche via EquipmentService
        results = self.equipment_service.search(query)
        
        # Ergebnisse anzeigen
        self.result_list.clear()
        
        if not results:
            self.result_label.setText(f"Keine Ergebnisse für '{query}'")
            self.result_label.setVisible(True)
            self.result_list.setVisible(False)
            return
        
        self.result_label.setText(f"{len(results)} Ergebnis{'se' if len(results) != 1 else ''} gefunden")
        self.result_label.setVisible(True)
        self.result_list.setVisible(True)
        
        for result in results:
            item_type = result['type']
            name = result['name']
            path = result['path']
            
            # Icon basierend auf Typ via Phosphor
            icon_map = {'location': 'ph.map-pin', 'system': 'ph.gear', 'equipment': 'ph.wrench'}
            icon_name = icon_map.get(item_type, '')
            
            item = QListWidgetItem(f"  {name}")
            if icon_name:
                item.setIcon(qta.icon(icon_name, color='#666'))
            item.setToolTip(path)
            item.setData(Qt.ItemDataRole.UserRole, result)
            
            # Farbe basierend auf Typ
            if item_type == 'location':
                item.setForeground(Qt.GlobalColor.darkBlue)
            elif item_type == 'system':
                item.setForeground(Qt.GlobalColor.darkGreen)
            
            self.result_list.addItem(item)
    
    def _on_result_clicked(self, item: QListWidgetItem):
        """Ergebnis wurde geklickt"""
        result = item.data(Qt.ItemDataRole.UserRole)
        if result:
            print(f"Selected: {result['path']}")
    
    def _on_result_double_clicked(self, item: QListWidgetItem):
        """Ergebnis wurde doppelt geklickt"""
        result = item.data(Qt.ItemDataRole.UserRole)
        if result:
            self.result_selected.emit(result)
            print(f"Double-clicked: {result['path']}")
    
    def _on_return_pressed(self):
        """Enter-Taste wurde gedrückt"""
        if self.result_list.count() > 0:
            # Wähle erstes Ergebnis aus
            first_item = self.result_list.item(0)
            if first_item:
                self._on_result_double_clicked(first_item)
    
    def clear_search(self):
        """Suche zurücksetzen"""
        self.search_input.clear()
        self.result_list.clear()
        self.result_list.setVisible(False)
        self.result_label.setVisible(False)
        self.clear_btn.setVisible(False)
    
    def focus_search(self):
        """Fokus auf Suchfeld setzen"""
        self.search_input.setFocus()
        self.search_input.selectAll()


# Standalone Widget für Tests
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    from pathlib import Path
    
    app = QApplication(sys.argv)
    
    # Equipment Service erstellen
    equipment_path = Path("equipment.json")
    service = EquipmentService(equipment_path)
    
    # Widget erstellen
    widget = EquipmentSearchWidget(service)
    widget.setWindowTitle("Equipment Search Demo")
    widget.resize(500, 600)
    widget.show()
    
    sys.exit(app.exec())
