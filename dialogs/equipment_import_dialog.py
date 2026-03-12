"""
Dialog: Übernahme von importierten Stickern in den Equipment-Manager.
"""

from typing import List, Dict, Any
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QRadioButton, QButtonGroup, QFrame, QCheckBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from ui.theme import (
    get_unified_button_style,
    create_dialog_stylesheet,
    create_input_stylesheet,
    get_theme_colors,
    Theme,
)
from ui.glass_button import GlassGlowButton
import re as _re


def _extract_group_key(energy_id, equipment='', description=''):
    """Extrahiert den Gruppenschlüssel aus Energy-ID + Equipment + Description."""
    combined = (energy_id + '.' + equipment + '.' + description).upper()
    sc_match = _re.search(r'SC_(\d+)\.(\d+)', combined)
    if sc_match:
        return f"SC_{sc_match.group(1)}.{sc_match.group(2).zfill(2)}"
    ksv_match = _re.search(r'KSV(\d+)', combined)
    if ksv_match:
        n = int(ksv_match.group(1))
        return f"SC_02.{str(n).zfill(2)}"
    if 'NSHV' in combined:
        return "NSHV"
    if 'UV-H' in combined or 'WALLBOX' in combined:
        return "UV-H"
    return ""


# Vordefinierte Gruppenfarben (dezent, für helle+dunkle Themes)
_GROUP_COLORS_LIGHT = [
    "#e8f0fe", "#fce8e6", "#e6f4ea", "#fef7e0", "#f3e8fd",
    "#e8eaed", "#e0f7fa", "#fff3e0", "#fce4ec", "#e8eaf6",
    "#f1f8e9", "#fff8e1",
]
_GROUP_COLORS_DARK = [
    "#1a2733", "#33201e", "#1a2e1f", "#332e1a", "#271a33",
    "#1e2226", "#1a2e30", "#332b1a", "#331a24", "#1e1f33",
    "#222e1a", "#33301a",
]


class EquipmentImportDialog(QDialog):
    """Dialog zur Übernahme von Sticker-Items in Equipment-Daten."""

    def __init__(self, parent, items: List[Dict[str, Any]], equipment_manager):
        super().__init__(parent)
        self.items = items
        self.equipment_manager = equipment_manager
        self.selected_items: List[Dict[str, Any]] = []

        # Always light theme
        self._is_dark = False

        self.setWindowTitle("Sticker in Equipment übernehmen")
        self.resize(860, 620)
        self.setModal(True)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 22, 25, 22)
        layout.setSpacing(14)

        # Theme styling
        theme = Theme.LIGHT
        colors = get_theme_colors(theme)
        self.setStyleSheet(
            create_dialog_stylesheet(theme)
            + create_input_stylesheet(theme)
            + f"""
                QTableWidget {{
                    background-color: {colors['input_bg']};
                    color: {colors['fg']};
                    border: 1px solid {colors['border']};
                    border-radius: 8px;
                }}
                QHeaderView::section {{
                    background-color: {colors['bg']};
                    color: {colors['fg']};
                    border: none;
                    border-bottom: 1px solid {colors['border']};
                    padding: 6px;
                }}
                QTableWidget::item:selected {{
                    background-color: {colors.get('selection', '#b3d7ff')};
                    color: {colors['fg']};
                }}
            """
        )

        title = QLabel("Sticker in Equipment übernehmen")
        title.setStyleSheet(f"font-size: 18px; font-weight: 600; color: {colors['fg']};")
        layout.addWidget(title)

        # Standort/System Eingabe
        form_row = QHBoxLayout()
        form_row.setSpacing(12)

        self.location_input = QLineEdit()
        self.location_input.setPlaceholderText("Standort (manuell eingeben)")
        self.location_input.setStyleSheet("padding: 6px 10px;")
        form_row.addWidget(QLabel("Standort:"))
        form_row.addWidget(self.location_input, 1)

        self.system_input = QLineEdit()
        self.system_input.setPlaceholderText("System (manuell eingeben)")
        self.system_input.setStyleSheet("padding: 6px 10px;")
        form_row.addWidget(QLabel("System:"))
        form_row.addWidget(self.system_input, 1)

        self.group_as_system_cb = QCheckBox("Gruppe als System")
        self.group_as_system_cb.setToolTip("Jede Gruppe wird als eigenes System/Equipment angelegt")
        self.group_as_system_cb.setStyleSheet(f"color: {colors['fg']}; font-size: 12px;")
        self.group_as_system_cb.toggled.connect(self._on_group_as_system_toggled)
        form_row.addWidget(self.group_as_system_cb)

        layout.addLayout(form_row)

        # LOTO-Modus Auswahl mit LED-Icons
        loto_row = QHBoxLayout()
        loto_row.setSpacing(12)
        loto_label = QLabel("LOTO-Modus:")
        loto_row.addWidget(loto_label)
        
        self.loto_button_group = QButtonGroup(self)
        self.multi_loto_radio = QRadioButton("Multi-LOTO (1 Count für alle)")
        self.single_loto_radio = QRadioButton("Single-LOTO (1 Count pro Sticker)")
        self.loto_button_group.addButton(self.multi_loto_radio)
        self.loto_button_group.addButton(self.single_loto_radio)
        
        # LED-Style für Radio-Buttons
        led_style = f"""
            QRadioButton {{
                spacing: 8px;
                color: {colors['fg']};
            }}
            QRadioButton::indicator {{
                width: 16px;
                height: 16px;
                border-radius: 8px;
                border: 2px solid {colors['border']};
                background-color: {colors['input_bg']};
            }}
            QRadioButton::indicator:checked {{
                background-color: #22c55e;
                border-color: #16a34a;
            }}
            QRadioButton:checked {{
                color: #22c55e;
                font-weight: bold;
            }}
        """
        self.multi_loto_radio.setStyleSheet(led_style)
        self.single_loto_radio.setStyleSheet(led_style)
        
        # Default: Multi-LOTO, oder von parent übernehmen
        parent_widget = self.parent()
        if parent_widget and hasattr(parent_widget, 'single_loto_radio') and parent_widget.single_loto_radio.isChecked():
            self.single_loto_radio.setChecked(True)
        else:
            self.multi_loto_radio.setChecked(True)
        
        loto_row.addWidget(self.multi_loto_radio)
        loto_row.addWidget(self.single_loto_radio)
        loto_row.addStretch()
        layout.addLayout(loto_row)

        # Mapping Section
        mapping_row = QHBoxLayout()
        mapping_row.setSpacing(12)
        mapping_row.addWidget(QLabel("Feldzuordnung:"))

        fields = ["Energy ID", "Equipment", "Beschreibung", "Symbol-Typ"]

        self.map_energy = QComboBox()
        self.map_energy.addItems(fields)
        self.map_energy.setCurrentText("Energy ID")
        mapping_row.addWidget(QLabel("Energy ID:"))
        mapping_row.addWidget(self.map_energy)

        self.map_equipment = QComboBox()
        self.map_equipment.addItems(fields)
        self.map_equipment.setCurrentText("Equipment")
        mapping_row.addWidget(QLabel("Equipment:"))
        mapping_row.addWidget(self.map_equipment)

        self.map_symbol = QComboBox()
        self.map_symbol.addItems(fields)
        self.map_symbol.setCurrentText("Symbol-Typ")
        mapping_row.addWidget(QLabel("Symbol-Typ:"))
        mapping_row.addWidget(self.map_symbol)

        layout.addLayout(mapping_row)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Übernehmen", "Energy ID", "Equipment", "Beschreibung", "Symbol-Typ", "Gruppe"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSortingEnabled(True)
        self.table.setRowCount(len(self.items))

        # Gruppen sammeln für Farbzuordnung
        group_keys_list = []
        for item in self.items:
            provided_group = str(item.get("group", "") or "").strip()
            if provided_group:
                group_keys_list.append(provided_group)
                continue
            eid = item.get("energy_id", "")
            eq = item.get("equipment", "")
            desc = item.get("description", "")
            gk = _extract_group_key(eid, eq, desc)
            group_keys_list.append(gk)
        unique_groups = list(dict.fromkeys(g for g in group_keys_list if g))
        palette = _GROUP_COLORS_LIGHT
        group_color_map = {g: QColor(palette[i % len(palette)]) for i, g in enumerate(unique_groups)}

        # Sortierung: Gruppe aufsteigend, dann Energy-ID-Nummer aufsteigend
        def _sort_key(idx):
            gk = group_keys_list[idx]
            item = self.items[idx]
            eid = item.get("energy_id", "")
            # Numerischen Teil der Energy-ID extrahieren (E1->1, E13->13)
            m = _re.match(r'[EPMC](\d+)', eid, _re.IGNORECASE)
            num = int(m.group(1)) if m else 999
            return (gk or "ZZZZ", num, eid)

        sorted_indices = sorted(range(len(self.items)), key=_sort_key)

        for row, orig_idx in enumerate(sorted_indices):
            item = self.items[orig_idx]
            # Checkbox
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            chk.setCheckState(Qt.CheckState.Checked)
            chk.setData(Qt.ItemDataRole.UserRole, orig_idx)
            self.table.setItem(row, 0, chk)

            # Automatische Trennung von Energy-ID und Equipment
            energy_id = item.get("energy_id", "")
            equipment = item.get("equipment", "")
            
            # Wenn Equipment leer ist, versuche aus Energy-ID zu extrahieren
            if energy_id and not equipment:
                energy_id, equipment = self._split_energy_equipment(energy_id)
            
            self.table.setItem(row, 1, QTableWidgetItem(energy_id))
            self.table.setItem(row, 2, QTableWidgetItem(equipment))
            self.table.setItem(row, 3, QTableWidgetItem(item.get("description", "")))
            self.table.setItem(row, 4, QTableWidgetItem(item.get("symbol_type", "")))

            # Gruppe
            gk = group_keys_list[orig_idx]
            grp_item = QTableWidgetItem(gk)
            grp_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row, 5, grp_item)

            # Zeile farblich markieren nach Gruppe
            if gk and gk in group_color_map:
                bg = group_color_map[gk]
                for col in range(self.table.columnCount()):
                    cell = self.table.item(row, col)
                    if cell:
                        cell.setBackground(bg)

        layout.addWidget(self.table, 1)

        # Gruppen-Info Label
        grp_info = QLabel(f"{len(unique_groups)} Gruppen erkannt: {', '.join(unique_groups) if unique_groups else 'keine'}")
        grp_info.setStyleSheet(f"font-size: 11px; color: {colors['border']}; padding: 2px 0;")
        layout.addWidget(grp_info)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = GlassGlowButton("Abbrechen", dark_mode=False)
        cancel_btn.setMinimumWidth(120)
        cancel_btn.setMinimumHeight(44)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        ok_btn = GlassGlowButton("Übernehmen", dark_mode=False)
        ok_btn.setMinimumWidth(140)
        ok_btn.setMinimumHeight(44)
        ok_btn.clicked.connect(self._on_accept)
        ok_btn.setDefault(True)
        btn_row.addWidget(ok_btn)

        layout.addLayout(btn_row)

    def _on_group_as_system_toggled(self, checked):
        self.system_input.setEnabled(not checked)
        if checked:
            self.system_input.setPlaceholderText("(wird aus Gruppe übernommen)")
        else:
            self.system_input.setPlaceholderText("System (manuell eingeben)")

    def _split_energy_equipment(self, value: str) -> tuple:
        """
        Trennt einen kombinierten String in Energy-ID und Equipment.
        
        Beispiele:
        - "E1.ASML.1.PLUG" -> ("E1", "ASML.1.PLUG")
        - "P1.PUMP.MAIN" -> ("P1", "PUMP.MAIN")
        - "G1.VALVE" -> ("G1", "VALVE")
        - "E14" -> ("E14", "")
        - "ASML.PLUG" -> ("", "ASML.PLUG")
        """
        import re
        
        if not value:
            return ("", "")
        
        # Pattern: E1, E14, P1, P12, G1, G2, H1, etc. am Anfang
        # Gefolgt von einem Punkt und dem Rest
        match = re.match(r'^([EPGHWCSL]\d+)\.(.+)$', value, re.IGNORECASE)
        if match:
            return (match.group(1).upper(), match.group(2))
        
        # Pattern: Nur Energy-ID ohne Equipment (z.B. "E1", "P2")
        match_only_id = re.match(r'^([EPGHWCSL]\d+)$', value, re.IGNORECASE)
        if match_only_id:
            return (match_only_id.group(1).upper(), "")
        
        # Kein Energy-ID Pattern erkannt - alles als Equipment
        return ("", value)

    def _on_accept(self):
        location = self.location_input.text().strip().upper()
        system = self.system_input.text().strip().upper()
        use_group_as_system = self.group_as_system_cb.isChecked()

        if not location:
            QMessageBox.warning(self, "Fehlende Angabe", "Bitte Standort eingeben.")
            return
        if not system and not use_group_as_system:
            QMessageBox.warning(self, "Fehlende Angabe", "Bitte System eingeben oder 'Gruppe als System' aktivieren.")
            return

        # Check/ask to create location if missing
        if self.equipment_manager:
            if location not in self.equipment_manager.equipment_data:
                reply = QMessageBox.question(
                    self,
                    "Standort anlegen",
                    f"Standort '{location}' existiert nicht. Anlegen?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    return
                self.equipment_manager.add_location(location)

            if not use_group_as_system:
                if system not in self.equipment_manager.get_system_names(location):
                    reply = QMessageBox.question(
                        self,
                        "System anlegen",
                        f"System '{system}' existiert nicht. Anlegen?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    if reply == QMessageBox.StandardButton.No:
                        return
                    self.equipment_manager.add_system(location, system, symbol_type="")

        # Build selected items list — Tabelle kann sortiert sein!
        self.selected_items = []
        created_systems = set()

        # Bei "Gruppe als System": gemeinsamen Equipment-Namen pro Gruppe ermitteln
        group_equipment_prefix = {}
        if use_group_as_system:
            group_equips = {}  # group -> [equipment_names]
            for vis_row in range(self.table.rowCount()):
                chk_item = self.table.item(vis_row, 0)
                if chk_item is None or chk_item.checkState() != Qt.CheckState.Checked:
                    continue
                grp_cell = self.table.item(vis_row, 5)
                grp = grp_cell.text().strip() if grp_cell else ""
                eq_cell = self.table.item(vis_row, 2)
                eq_name = eq_cell.text().strip().upper() if eq_cell else ""
                if grp:
                    group_equips.setdefault(grp, []).append(eq_name)
            # Gemeinsamen Equipment-Prefix pro Gruppe bestimmen
            for grp, equips in group_equips.items():
                if not equips:
                    continue
                # Alle Equipment-Namen gleich? → direkt verwenden
                unique = list(dict.fromkeys(equips))
                if len(unique) == 1:
                    group_equipment_prefix[grp] = unique[0].rstrip(".")
                else:
                    # Längsten gemeinsamen Prefix finden
                    prefix = unique[0]
                    for s in unique[1:]:
                        while not s.startswith(prefix) and prefix:
                            dot_pos = prefix.rfind(".")
                            prefix = prefix[:dot_pos] if dot_pos > 0 else ""
                    group_equipment_prefix[grp] = prefix.rstrip(".") if prefix else ""

        for vis_row in range(self.table.rowCount()):
            chk_item = self.table.item(vis_row, 0)
            if chk_item is None or chk_item.checkState() != Qt.CheckState.Checked:
                continue

            # Gruppe aus Spalte 5 lesen
            grp_cell = self.table.item(vis_row, 5)
            row_group = grp_cell.text().strip() if grp_cell else ""

            # System bestimmen
            row_system = system
            if use_group_as_system and row_group:
                # System-Name: EQUIPMENT_GRUPPENNAME (z.B. "COMPRESSORS_GRUPPE 1")
                eq_prefix = group_equipment_prefix.get(row_group, "")
                grp_clean = row_group.strip().upper().replace(" ", "")
                if eq_prefix:
                    row_system = f"{eq_prefix}_{grp_clean}"
                else:
                    row_system = grp_clean
                # System automatisch anlegen falls nötig
                if self.equipment_manager and row_system not in created_systems:
                    if row_system not in self.equipment_manager.get_system_names(location):
                        self.equipment_manager.add_system(location, row_system, symbol_type="")
                    created_systems.add(row_system)
            elif use_group_as_system and not row_group:
                row_system = (system or "UNGROUPED").strip().upper()
                if self.equipment_manager and row_system not in created_systems:
                    if row_system not in self.equipment_manager.get_system_names(location):
                        self.equipment_manager.add_system(location, row_system, symbol_type="")
                    created_systems.add(row_system)

            orig_idx = chk_item.data(Qt.ItemDataRole.UserRole)
            source_item = self.items[orig_idx] if isinstance(orig_idx, int) and 0 <= orig_idx < len(self.items) else {}

            mapped = self._map_item_from_table(vis_row, source_item)
            if mapped:
                mapped["location"] = location
                mapped["system"] = row_system
                mapped["group"] = row_group
                # Gruppe in sticker_config speichern, damit sie beim Laden erhalten bleibt
                if row_group and isinstance(mapped.get("sticker_config"), dict):
                    mapped["sticker_config"]["loto_group"] = row_group
                self.selected_items.append(mapped)

        self.accept()

    def _map_item_from_table(self, vis_row: int, source_item: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """Liest Tabellenwerte direkt aus der (evtl. sortierten) Zeile."""
        def get_cell(col: int) -> str:
            cell = self.table.item(vis_row, col)
            return cell.text().strip() if cell else ""

        energy_id = get_cell(1)
        equipment = get_cell(2)
        description = get_cell(3)
        symbol_type = get_cell(4)

        sources = {
            "Energy ID": energy_id,
            "Equipment": equipment,
            "Beschreibung": description,
            "Symbol-Typ": symbol_type,
        }

        mapped_energy = sources.get(self.map_energy.currentText(), "")
        mapped_equipment = sources.get(self.map_equipment.currentText(), "")
        mapped_symbol = sources.get(self.map_symbol.currentText(), "")

        source_item = source_item or {}
        sticker_cfg = source_item.get("sticker_config", {}).copy() if source_item.get("sticker_config") else {}
        sticker_cfg["loto_mode_single"] = self.single_loto_radio.isChecked()
        
        return {
            "energy_id": mapped_energy.strip(),
            "equipment": mapped_equipment.strip(),
            "symbol_type": mapped_symbol.strip() or "ELECTRICAL",
            "description": description.strip(),
            "qr_path": source_item.get("qr_path", ""),
            "sticker_config": sticker_cfg,
        }

    def _map_item(self, row: int, item: Dict[str, Any]) -> Dict[str, Any]:
        # Read possibly edited table values
        def get_cell(col: int, fallback: str) -> str:
            cell = self.table.item(row, col)
            return cell.text().strip() if cell else fallback

        energy_id = get_cell(1, item.get("energy_id", ""))
        equipment = get_cell(2, item.get("equipment", ""))
        description = get_cell(3, item.get("description", ""))
        symbol_type = get_cell(4, item.get("symbol_type", ""))

        sources = {
            "Energy ID": energy_id,
            "Equipment": equipment,
            "Beschreibung": description,
            "Symbol-Typ": symbol_type,
        }

        mapped_energy = sources.get(self.map_energy.currentText(), "")
        mapped_equipment = sources.get(self.map_equipment.currentText(), "")
        mapped_symbol = sources.get(self.map_symbol.currentText(), "")

        # LOTO-Modus: Dialog-Auswahl überschreibt immer (User hat explizit gewählt)
        sticker_cfg = item.get("sticker_config", {}).copy() if item.get("sticker_config") else {}
        sticker_cfg["loto_mode_single"] = self.single_loto_radio.isChecked()
        
        return {
            "energy_id": mapped_energy.strip(),
            "equipment": mapped_equipment.strip(),
            "symbol_type": mapped_symbol.strip() or "ELECTRICAL",
            "description": description.strip(),
            "qr_path": item.get("qr_path", ""),  # QR-Code Pfad beibehalten
            "sticker_config": sticker_cfg,  # Sticker-Config mit LOTO-Modus
        }
