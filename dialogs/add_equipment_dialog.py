"""
Optimierter Equipment-Hinzufügen Dialog
- Alle Details/Felder
- Sticker-Preset Auswahl
- Autovervollständigung
- Validierung
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QFrame, QMessageBox, QCompleter, QGroupBox,
    QRadioButton, QButtonGroup, QScrollArea, QWidget, QSizePolicy
)
from PyQt6.QtCore import Qt, QStringListModel
from PyQt6.QtGui import QFont
from core.models import SymbolType
from ui.glass_button import GlassGlowButton


class AddEquipmentDialog(QDialog):
    """Dialog zum Hinzufügen von neuem Equipment mit allen Details."""
    
    def __init__(self, parent, equipment_manager=None, existing_locations=None, 
                 existing_systems=None, existing_equipment=None):
        super().__init__(parent)
        self.equipment_manager = equipment_manager
        self.result_data = None
        
        # Für Autovervollständigung
        self.existing_locations = existing_locations or []
        self.existing_systems = existing_systems or []
        self.existing_equipment = existing_equipment or []
        
        self.setWindowTitle("Equipment hinzufügen")
        self.setModal(True)
        self.setMinimumSize(550, 650)
        self.resize(600, 700)
        
        self._build_ui()
        self._setup_completers()
    
    def _build_ui(self):
        """UI aufbauen."""
        # Styling
        self.setStyleSheet("""
            QDialog {
                background-color: #f8fafc;
            }
            QLabel {
                color: #1e293b;
                font-size: 13px;
            }
            QLineEdit {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 10px 12px;
                font-size: 13px;
                color: #1e293b;
            }
            QLineEdit:focus {
                border: 2px solid #3b82f6;
                background-color: #ffffff;
            }
            QLineEdit:disabled {
                background-color: #f1f5f9;
                color: #94a3b8;
            }
            QComboBox {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 10px 12px;
                font-size: 13px;
                color: #1e293b;
            }
            QComboBox:focus {
                border: 2px solid #3b82f6;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #64748b;
                margin-right: 10px;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                selection-background-color: #3b82f6;
                selection-color: #ffffff;
            }
            QGroupBox {
                font-weight: 600;
                font-size: 14px;
                color: #1e293b;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                margin-top: 12px;
                padding-top: 10px;
                background-color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
                background-color: #ffffff;
            }
            QRadioButton {
                color: #1e293b;
                font-size: 13px;
                spacing: 8px;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
                border-radius: 9px;
                border: 2px solid #cbd5e1;
                background-color: #ffffff;
            }
            QRadioButton::indicator:checked {
                border: 2px solid #3b82f6;
                background-color: #3b82f6;
            }
            QRadioButton::indicator:hover {
                border: 2px solid #3b82f6;
            }
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(24, 24, 24, 24)
        
        # Header
        header = QLabel("⚡ Neues Equipment")
        header.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        header.setStyleSheet("color: #0f172a; background: transparent;")
        main_layout.addWidget(header)
        
        subtitle = QLabel("Alle Felder ausfüllen für vollständige Equipment-Daten")
        subtitle.setStyleSheet("color: #64748b; font-size: 12px; background: transparent;")
        main_layout.addWidget(subtitle)
        
        main_layout.addSpacing(8)
        
        # Scroll Area für Formular
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        
        form_widget = QWidget()
        form_widget.setStyleSheet("background: transparent;")
        form_layout = QVBoxLayout(form_widget)
        form_layout.setSpacing(16)
        
        # === STANDORT & SYSTEM ===
        location_group = QGroupBox("Standort & System")
        location_layout = QGridLayout(location_group)
        location_layout.setSpacing(12)
        location_layout.setContentsMargins(16, 20, 16, 16)
        
        # Standort
        location_layout.addWidget(QLabel("Standort:"), 0, 0)
        self.location_entry = QLineEdit()
        self.location_entry.setPlaceholderText("z.B. FRAX, Halle A, Gebäude 1...")
        location_layout.addWidget(self.location_entry, 0, 1)
        
        # System
        location_layout.addWidget(QLabel("System:"), 1, 0)
        self.system_entry = QLineEdit()
        self.system_entry.setPlaceholderText("z.B. SHIPPING, 01, LANE 01...")
        location_layout.addWidget(self.system_entry, 1, 1)
        
        form_layout.addWidget(location_group)
        
        # === EQUIPMENT DETAILS ===
        equipment_group = QGroupBox("Equipment Details")
        equipment_layout = QGridLayout(equipment_group)
        equipment_layout.setSpacing(12)
        equipment_layout.setContentsMargins(16, 20, 16, 16)
        
        # Equipment Name
        equipment_layout.addWidget(QLabel("Equipment Name:*"), 0, 0)
        self.name_entry = QLineEdit()
        self.name_entry.setPlaceholderText("z.B. SHP.01.LN01.RO1-1")
        equipment_layout.addWidget(self.name_entry, 0, 1)
        
        # Energy ID
        equipment_layout.addWidget(QLabel("Energy ID:*"), 1, 0)
        self.energy_id_entry = QLineEdit()
        self.energy_id_entry.setPlaceholderText("z.B. E28, P15, H03...")
        equipment_layout.addWidget(self.energy_id_entry, 1, 1)
        
        # Description
        equipment_layout.addWidget(QLabel("Beschreibung:"), 2, 0)
        self.description_entry = QLineEdit()
        self.description_entry.setPlaceholderText("z.B. MAIN SWITCH, Kompressor...")
        equipment_layout.addWidget(self.description_entry, 2, 1)
        
        # Symbol-Typ
        equipment_layout.addWidget(QLabel("Energie-Typ:*"), 3, 0)
        self.symbol_combo = QComboBox()
        symbol_names = [s.name.capitalize() for s in SymbolType]
        self.symbol_combo.addItems(symbol_names)
        equipment_layout.addWidget(self.symbol_combo, 3, 1)
        
        form_layout.addWidget(equipment_group)
        
        # === STICKER PRESET ===
        preset_group = QGroupBox("Sticker Einstellungen")
        preset_layout = QVBoxLayout(preset_group)
        preset_layout.setSpacing(12)
        preset_layout.setContentsMargins(16, 20, 16, 16)
        
        preset_label = QLabel("Sticker-Form wählen:")
        preset_label.setStyleSheet("font-weight: 500;")
        preset_layout.addWidget(preset_label)
        
        # Radio Buttons für Presets
        preset_btn_layout = QHBoxLayout()
        preset_btn_layout.setSpacing(20)
        
        self.preset_group = QButtonGroup(self)
        
        self.preset_rectangle = QRadioButton("▬ Rechteck")
        self.preset_rectangle.setChecked(True)
        self.preset_group.addButton(self.preset_rectangle, 0)
        preset_btn_layout.addWidget(self.preset_rectangle)
        
        self.preset_square = QRadioButton("◼ Quadrat")
        self.preset_group.addButton(self.preset_square, 1)
        preset_btn_layout.addWidget(self.preset_square)
        
        self.preset_circle = QRadioButton("● Kreis")
        self.preset_group.addButton(self.preset_circle, 2)
        preset_btn_layout.addWidget(self.preset_circle)
        
        self.preset_rounded = QRadioButton("▢ Abgerundet")
        self.preset_group.addButton(self.preset_rounded, 3)
        preset_btn_layout.addWidget(self.preset_rounded)
        
        preset_btn_layout.addStretch()
        preset_layout.addLayout(preset_btn_layout)
        
        # LOTO Modus
        loto_label = QLabel("LOTO Modus:")
        loto_label.setStyleSheet("font-weight: 500; margin-top: 8px;")
        preset_layout.addWidget(loto_label)
        
        loto_btn_layout = QHBoxLayout()
        loto_btn_layout.setSpacing(20)
        
        self.loto_group = QButtonGroup(self)
        
        self.single_loto = QRadioButton("Single LOTO")
        self.single_loto.setChecked(True)
        self.loto_group.addButton(self.single_loto, 0)
        loto_btn_layout.addWidget(self.single_loto)
        
        self.multi_loto = QRadioButton("Multi LOTO")
        self.loto_group.addButton(self.multi_loto, 1)
        loto_btn_layout.addWidget(self.multi_loto)
        
        loto_btn_layout.addStretch()
        preset_layout.addLayout(loto_btn_layout)
        
        form_layout.addWidget(preset_group)
        
        form_layout.addStretch()
        
        scroll.setWidget(form_widget)
        main_layout.addWidget(scroll, 1)
        
        # === BUTTONS ===
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        
        # Validierungs-Info
        self.validation_label = QLabel("")
        self.validation_label.setStyleSheet("color: #ef4444; font-size: 12px;")
        button_layout.addWidget(self.validation_label)
        
        button_layout.addStretch()
        
        # Cancel Button
        cancel_btn = GlassGlowButton("Abbrechen")
        cancel_btn.setFixedHeight(38)
        cancel_btn.setMinimumWidth(120)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        # Add Button
        add_btn = GlassGlowButton("✓ Hinzufügen")
        add_btn.setFixedHeight(38)
        add_btn.setMinimumWidth(140)
        add_btn.clicked.connect(self._on_add_clicked)
        button_layout.addWidget(add_btn)
        
        main_layout.addLayout(button_layout)
    
    def _setup_completers(self):
        """Autovervollständigung einrichten."""
        # Standort Completer
        if self.existing_locations:
            location_completer = QCompleter(self.existing_locations)
            location_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            location_completer.setFilterMode(Qt.MatchFlag.MatchContains)
            self.location_entry.setCompleter(location_completer)
        
        # System Completer
        if self.existing_systems:
            system_completer = QCompleter(self.existing_systems)
            system_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            system_completer.setFilterMode(Qt.MatchFlag.MatchContains)
            self.system_entry.setCompleter(system_completer)
        
        # Equipment Name Completer (für Muster-Erkennung)
        if self.existing_equipment:
            equipment_completer = QCompleter(self.existing_equipment)
            equipment_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            equipment_completer.setFilterMode(Qt.MatchFlag.MatchContains)
            self.name_entry.setCompleter(equipment_completer)
    
    def _validate(self) -> bool:
        """Pflichtfelder validieren."""
        errors = []
        
        if not self.name_entry.text().strip():
            errors.append("Equipment Name")
            self.name_entry.setStyleSheet(self.name_entry.styleSheet() + "border: 2px solid #ef4444;")
        else:
            self.name_entry.setStyleSheet("")
        
        if not self.energy_id_entry.text().strip():
            errors.append("Energy ID")
            self.energy_id_entry.setStyleSheet(self.energy_id_entry.styleSheet() + "border: 2px solid #ef4444;")
        else:
            self.energy_id_entry.setStyleSheet("")
        
        if errors:
            self.validation_label.setText(f"Pflichtfelder: {', '.join(errors)}")
            return False
        
        self.validation_label.setText("")
        return True
    
    def _get_preset_type(self) -> str:
        """Ausgewähltes Preset zurückgeben."""
        checked_id = self.preset_group.checkedId()
        presets = {0: "rectangle", 1: "square", 2: "circle", 3: "rounded"}
        return presets.get(checked_id, "rectangle")
    
    def _get_loto_mode(self) -> str:
        """Ausgewählten LOTO Modus zurückgeben."""
        return "multi" if self.multi_loto.isChecked() else "single"
    
    def _on_add_clicked(self):
        """Hinzufügen Button geklickt."""
        if not self._validate():
            return
        
        # Daten sammeln
        self.result_data = {
            "location": self.location_entry.text().strip(),
            "system": self.system_entry.text().strip(),
            "name": self.name_entry.text().strip(),
            "energy_id": self.energy_id_entry.text().strip(),
            "description": self.description_entry.text().strip(),
            "symbol_type": self.symbol_combo.currentText().upper(),
            "preset_type": self._get_preset_type(),
            "loto_mode": self._get_loto_mode(),
        }
        
        self.accept()
    
    def get_result(self) -> dict:
        """Ergebnis-Daten zurückgeben."""
        return self.result_data


def show_add_equipment_dialog(parent, equipment_manager=None, 
                              pre_location: str = "", pre_system: str = "") -> dict:
    """Hilfsfunktion zum Anzeigen des Dialogs.
    
    Args:
        parent: Parent Widget
        equipment_manager: Equipment Manager Instanz
        pre_location: Vorausgewählter Standort
        pre_system: Vorausgewähltes System
    """
    # Sammle existierende Daten für Autovervollständigung
    existing_locations = []
    existing_systems = []
    existing_equipment = []
    
    if equipment_manager:
        try:
            # Hole alle Standorte
            hierarchy = equipment_manager.get_hierarchy()
            if hierarchy:
                existing_locations = list(hierarchy.keys())
                
                # Hole alle Systeme und Equipment
                for loc_data in hierarchy.values():
                    if isinstance(loc_data, dict):
                        systems = loc_data.get("systems", [])
                        for sys in systems:
                            if isinstance(sys, dict):
                                sys_name = sys.get("name", "")
                                if sys_name:
                                    existing_systems.append(sys_name)
                                
                                equip_list = sys.get("equipment", [])
                                for eq in equip_list:
                                    if isinstance(eq, dict):
                                        eq_name = eq.get("name", "")
                                        if eq_name:
                                            existing_equipment.append(eq_name)
        except Exception:
            pass
    
    dialog = AddEquipmentDialog(
        parent,
        equipment_manager=equipment_manager,
        existing_locations=existing_locations,
        existing_systems=existing_systems,
        existing_equipment=existing_equipment
    )
    
    # Vorauswahl setzen
    if pre_location:
        dialog.location_entry.setText(pre_location)
    if pre_system:
        dialog.system_entry.setText(pre_system)
    
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog.get_result()
    
    return None
