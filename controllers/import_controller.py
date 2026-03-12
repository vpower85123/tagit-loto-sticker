"""
Import Controller
Verwaltet PDF-Import, LOTO-Gruppierung, fehlende Sticker-Erkennung und Equipment-Import.
"""

import math
import re
import logging
from typing import Optional, Any, TYPE_CHECKING

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QWidget, QLineEdit, QCheckBox,
    QScrollArea, QAbstractItemView, QRadioButton,
    QButtonGroup, QMessageBox, QApplication, QMenu
)
from PyQt6.QtCore import QObject, Qt, QSize
from PyQt6.QtGui import QColor

from PIL import Image
import qtawesome as qta

if TYPE_CHECKING:
    from sticker_app_pyqt6 import StickerApp

logger = logging.getLogger(__name__)


class ImportController(QObject):
    """Controller für PDF-Import und Equipment-Import-Operationen."""

    def __init__(self, parent: 'StickerApp'):
        super().__init__(parent)
        self.app = parent

    # ── Property-Shortcuts ──────────────────────────────────────────

    @property
    def collection(self):
        return self.app.collection

    @property
    def collection_service(self):
        return self.app.collection_service

    @property
    def sticker_service(self):
        return self.app.sticker_service

    @property
    def count_generator(self):
        return self.app.count_generator

    @property
    def sticker_config(self):
        return self.app.sticker_service.generator.cfg

    @property
    def count_config(self):
        return self.app.count_config

    @property
    def equipment_service(self):
        return self.app.equipment_service

    @property
    def status_bar(self):
        return self.app.status_bar

    def _create_styled_msgbox(self, *args, **kwargs):
        return self.app._create_styled_msgbox(*args, **kwargs)

    # ── Static Helpers ──────────────────────────────────────────────

    @staticmethod
    def _extract_group_key(energy_id, equipment='', description=''):
        """Extrahiert den Gruppenschlüssel aus Energy-ID + Equipment + Description.

        Prüft nacheinander: SC_XX.XX → KSV{N}→SC_02.0{N} → NSHV → UV-H/WALLBOX
        Bezieht alle Felder ein (für Split-IDs über mehrere Zeilen im PDF).
        """
        combined = (energy_id + '.' + equipment + '.' + description).upper()

        # 1. SC-Pattern direkt vorhanden
        sc_match = re.search(r'SC_(\d+)\.(\d+)', combined)
        if sc_match:
            return f"SC_{sc_match.group(1)}.{sc_match.group(2).zfill(2)}"

        # 2. KSV{N} → abgeleitetes SC-Pattern
        ksv_match = re.search(r'KSV(\d+)', combined)
        if ksv_match:
            n = int(ksv_match.group(1))
            return f"SC_02.{str(n).zfill(2)}"

        # 3. NSHV-Sticker
        if 'NSHV' in combined:
            return "NSHV"

        # 4. UV-H / WALLBOX
        if 'UV-H' in combined or 'WALLBOX' in combined:
            return "UV-H"

        return None

    # ── Missing Sticker Detection ───────────────────────────────────

    def _detect_missing_stickers(self, extracted_data, count_sticker_groups):
        """Erkennt fehlende Sticker durch Vergleich von Count-Sticker-Einträgen mit extrahierten Stickern.

        Verwendet Multi-Pass-Matching:
        1. Full-ID Match (exakt und Prefix)
        2. SC-Key + Energy-Prefix Match
        3. Energy-Prefix-Only Match (Last Resort)

        Returns:
            list: Liste der fehlenden Count-Sticker-Einträge (Strings)
        """
        if not count_sticker_groups:
            return []

        # Alle Count-Sticker-Einträge flach sammeln
        all_count_entries = []
        for group in count_sticker_groups:
            for entry in group:
                normalized = entry.strip().strip(".").upper()
                if normalized:
                    all_count_entries.append(normalized)

        if not all_count_entries:
            return []

        # Sticker-Informationen aufbauen
        sticker_infos = []
        for i, sticker in enumerate(extracted_data):
            eid = sticker.get("energy_id", "").strip().strip(".")
            eq = sticker.get("equipment", "").strip().strip(".")
            desc = sticker.get("description", "").strip().strip(".")
            parts = [p for p in [eid, eq, desc] if p]
            full_id = ".".join(parts).upper()

            key = self._extract_group_key(eid, eq, desc)

            sticker_infos.append({
                "index": i,
                "energy_id": eid.upper(),
                "full_id": full_id,
                "key": key,
                "claimed": False,
            })

        matched_entries = set()

        # Pass 1: Full-ID-Matching (exakt und Prefix)
        for entry in all_count_entries:
            for info in sticker_infos:
                if info["claimed"]:
                    continue
                if info["full_id"] == entry:
                    info["claimed"] = True
                    matched_entries.add(entry)
                    break
                if entry.startswith(info["full_id"]) or info["full_id"].startswith(entry):
                    info["claimed"] = True
                    matched_entries.add(entry)
                    break

        # Pass 2: SC-Key + Energy-Prefix
        for entry in all_count_entries:
            if entry in matched_entries:
                continue
            m = re.match(r'^([EPMC]\d+)', entry)
            entry_prefix = m.group(1).upper() if m else ""
            entry_key = self._extract_group_key(entry)

            if entry_key and entry_prefix:
                for info in sticker_infos:
                    if info["claimed"]:
                        continue
                    if info["energy_id"] == entry_prefix and info["key"] == entry_key:
                        info["claimed"] = True
                        matched_entries.add(entry)
                        break

        # Pass 3: Energy-Prefix Only (Last Resort)
        for entry in all_count_entries:
            if entry in matched_entries:
                continue
            m = re.match(r'^([EPMC]\d+)', entry)
            entry_prefix = m.group(1).upper() if m else ""

            if entry_prefix:
                for info in sticker_infos:
                    if info["claimed"]:
                        continue
                    if info["energy_id"] == entry_prefix:
                        info["claimed"] = True
                        matched_entries.add(entry)
                        break

        # Nicht gematchte Einträge sind fehlend
        missing = [entry for entry in all_count_entries if entry not in matched_entries]

        if missing:
            logger.info(f"Fehlende Sticker erkannt: {missing}")

        return missing

    def _detect_missing_from_group_gaps(self, extracted_data, count_sticker_groups=None):
        """Erkennt fehlende Sticker durch Lücken in E-Nummern-Sequenzen innerhalb von Gruppen.

        Analysiert Gruppen, die NICHT durch Count-Sticker-Daten abgedeckt sind,
        und sucht nach fehlenden sequentiellen E-Nummern (z.B. E2 vorhanden aber E1 fehlt).

        Returns:
            list: Liste der wahrscheinlich fehlenden Sticker-IDs (Strings)
        """
        # Bestimme welche Gruppen durch Count-Sticker abgedeckt sind
        covered_keys = set()
        if count_sticker_groups:
            for group_entries in count_sticker_groups:
                for entry in group_entries:
                    key = self._extract_group_key(entry)
                    if key:
                        covered_keys.add(key)

        # Sticker nach Gruppe gruppieren
        groups = {}  # key -> list of (num, prefix_char, rest_equipment)
        for sticker in extracted_data:
            eid = sticker.get('energy_id', '').strip().strip('.')
            eq = sticker.get('equipment', '').strip().strip('.')
            desc = sticker.get('description', '').strip().strip('.')

            key = self._extract_group_key(eid, eq, desc)
            if not key or key in covered_keys:
                continue

            # E-Nummer aus dem Anfang parsen
            full_combined = '.'.join(p for p in [eid, eq, desc] if p).upper()
            m = re.match(r'^([EPMC])(\d+)', full_combined)
            if not m:
                continue

            prefix_char = m.group(1)
            num = int(m.group(2))
            rest = full_combined[len(m.group(0)):].lstrip('.')

            if key not in groups:
                groups[key] = []
            groups[key].append((num, prefix_char, rest))

        missing = []

        for key, members in groups.items():
            if not members:
                continue

            nums = set(m[0] for m in members)
            prefix_char = members[0][1]
            max_num = max(nums)

            # Nur Lücken erkennen wenn max > 1
            if max_num <= 1:
                continue

            missing_nums = sorted(set(range(1, max_num + 1)) - nums)
            if not missing_nums:
                continue

            # Equipment-Basis ableiten: Schlüssel im Equipment suchen
            eq_base = None
            for _, _, rest in members:
                rest_upper = rest.upper()
                idx = rest_upper.find(key)
                if idx >= 0:
                    after_key = rest_upper[idx + len(key):]
                    extra = re.match(r'[\d.]+', after_key)
                    if extra:
                        end_pos = idx + len(key) + extra.end()
                    else:
                        end_pos = idx + len(key)
                    base = rest[:end_pos].rstrip('.')
                    if eq_base is None or len(base) < len(eq_base):
                        eq_base = base

            if not eq_base:
                shortest = min(members, key=lambda m: len(m[2]))
                eq_base = shortest[2].rstrip('.')

            for num in missing_nums:
                entry = f"{prefix_char}{num}.{eq_base}"
                missing.append(entry)

        if missing:
            logger.info(f"Fehlende Sticker aus Lückenanalyse: {missing}")

        return missing

    # ── Dialogs ─────────────────────────────────────────────────────

    def _show_missing_stickers_dialog(self, missing_entries):
        """Zeigt Dialog mit fehlenden Stickern und bietet deren Erstellung an.

        Args:
            missing_entries: Liste der fehlenden Energy-ID-Strings

        Returns:
            list: Ausgewählte Einträge die erstellt werden sollen (oder leere Liste)
        """
        from ui.glass_button import GlassGlowButton
        from ui.theme import Theme, get_theme_colors, create_dialog_stylesheet

        theme = getattr(self.app, 'theme', Theme.LIGHT)
        colors = get_theme_colors(theme)
        text_color = colors["fg"]
        accent = colors["accent"]
        card_bg = "rgba(0,0,0,0.03)"
        border_color = "rgba(0,0,0,0.08)"

        dialog = QDialog(self.app)
        dialog.setWindowTitle("Fehlende Sticker erkannt")
        dialog.setModal(True)
        dialog.setMinimumWidth(520)
        dialog.setStyleSheet(create_dialog_stylesheet(theme))

        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 20, 24, 20)

        # Header mit Icon
        header_layout = QHBoxLayout()
        header_icon = QLabel()
        header_icon.setPixmap(qta.icon('ph.warning', color=accent).pixmap(QSize(22, 22)))
        header_layout.addWidget(header_icon)

        header = QLabel("Fehlende Sticker erkannt")
        header.setStyleSheet(f"color: {text_color}; font-size: 15px; font-weight: 600; border: none;")
        header_layout.addWidget(header)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        info = QLabel(
            f"Die folgenden {len(missing_entries)} Sticker sind in den Count-Stickern aufgeführt, "
            f"wurden aber nicht als eigene Sticker im PDF gefunden.\n"
            f"Möglicherweise wurden sie vom Ersteller vergessen.\n\n"
            f"Wähle die Sticker aus, die erstellt werden sollen:"
        )
        info.setWordWrap(True)
        info.setStyleSheet(f"color: {text_color}; font-size: 12px; border: none; padding-bottom: 4px;")
        layout.addWidget(info)

        # Scroll-Bereich mit Checkboxen
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(300)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: 1px solid {border_color};
                border-radius: 8px;
            }}
        """)

        scroll_widget = QWidget()
        scroll_widget.setStyleSheet("background: transparent;")
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(4)
        scroll_layout.setContentsMargins(8, 8, 8, 8)

        checkboxes = []
        for entry in missing_entries:
            cb = QCheckBox(entry)
            cb.setChecked(True)
            cb.setStyleSheet(f"""
                QCheckBox {{
                    color: {text_color};
                    font-size: 13px;
                    font-family: 'Consolas', 'Courier New', monospace;
                    padding: 6px 8px;
                    background: {card_bg};
                    border-radius: 6px;
                    border: none;
                }}
                QCheckBox::indicator {{
                    width: 16px;
                    height: 16px;
                    border-radius: 4px;
                    border: 1.5px solid rgba(128,128,128,0.3);
                }}
                QCheckBox::indicator:checked {{
                    background: {accent};
                    border: 1.5px solid {accent};
                }}
                QCheckBox::indicator:hover {{
                    border: 1.5px solid {accent};
                }}
            """)
            scroll_layout.addWidget(cb)
            checkboxes.append((cb, entry))

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        button_layout.addStretch()

        skip_btn = GlassGlowButton("Überspringen")
        skip_btn.setMinimumHeight(40)
        skip_btn.setMinimumWidth(130)
        skip_btn.setIcon(qta.icon('ph.skip-forward', color=text_color))
        skip_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(skip_btn)

        create_btn = GlassGlowButton("Ausgewählte erstellen")
        create_btn.setMinimumHeight(40)
        create_btn.setMinimumWidth(180)
        create_btn.setIcon(qta.icon('ph.plus-circle', color=text_color))
        create_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(create_btn)

        layout.addLayout(button_layout)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return []

        return [entry for cb, entry in checkboxes if cb.isChecked()]

    def _create_stickers_from_entries(self, extracted_data, entries):
        """Erstellt Sticker-Dicts aus Count-Sticker-Einträgen und fügt sie zu extracted_data hinzu.

        Args:
            extracted_data: Liste der extrahierten Sticker (wird in-place erweitert)
            entries: Liste der zu erstellenden Energy-ID-Strings

        Returns:
            int: Anzahl der erstellten Sticker
        """
        created = 0
        for entry in entries:
            # Split: "E1.ELEC.DP.UV-H0.1" → energy_id="E1", rest="ELEC.DP.UV-H0.1"
            match = re.match(r'^([EPMC]\d+)\.(.+)$', entry, re.IGNORECASE)
            if match:
                energy_id = match.group(1).upper()
                equipment = match.group(2)
            else:
                energy_id = entry.upper()
                equipment = ""

            # Symbol-Typ basierend auf Präfix
            prefix = energy_id[0] if energy_id else 'E'
            symbol_map = {'P': "PNEUMATIC", 'M': "MECHANICAL", 'C': "CHEMICAL"}
            symbol_type = symbol_map.get(prefix, "ELECTRICAL")

            new_sticker = {
                "energy_id": energy_id,
                "equipment": equipment,
                "symbol_type": symbol_type,
                "description": "",
                "_created_from_count": True,  # Markierung für nachträglich erstellte Sticker
            }

            extracted_data.append(new_sticker)
            created += 1
            logger.info(f"Fehlender Sticker erstellt: {energy_id} / {equipment}")

        return created

    def _show_loto_grouping_dialog(self, extracted_data, count_sticker_groups=None):
        """Zeigt einen Dialog zur manuellen Gruppierung von Stickern für Multi-LOTO.

        Args:
            extracted_data: Liste der extrahierten Sticker-Daten
            count_sticker_groups: Liste von Listen mit Energy-IDs aus erkannten Count-Stickern

        Returns:
            dict: {sticker_index: group_name} oder None bei Abbruch
        """
        from ui.spinboxes import StyledSpinBox
        from ui.glass_button import GlassGlowButton
        from ui.theme import Theme, get_theme_colors, create_dialog_stylesheet

        theme = getattr(self.app, 'theme', Theme.LIGHT)
        colors = get_theme_colors(theme)

        dialog = QDialog(self.app)
        dialog.setWindowTitle("LOTO Gruppen zuweisen")
        dialog.setModal(True)
        dialog.setMinimumSize(750, 500)
        dialog.setStyleSheet(create_dialog_stylesheet(theme))

        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header = QLabel("Multi-LOTO Gruppierung")
        header.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {colors['fg']};")
        layout.addWidget(header)

        info = QLabel("Weisen Sie jedem Sticker eine Gruppe zu. Sticker mit der gleichen Gruppe erhalten einen gemeinsamen Count-Sticker.\nGruppe 0 = Single LOTO (eigener Count-Sticker pro Sticker).")
        info.setWordWrap(True)
        info.setStyleSheet(f"font-size: 11px; color: {colors['fg']}; opacity: 0.8;")
        layout.addWidget(info)

        # Gruppen-Anzahl Steuerung
        group_ctrl_layout = QHBoxLayout()
        group_ctrl_label = QLabel("Anzahl Gruppen:")
        group_ctrl_label.setStyleSheet(f"font-size: 12px; color: {colors['fg']};")
        group_ctrl_layout.addWidget(group_ctrl_label)

        group_spin = StyledSpinBox()
        group_spin.setRange(1, 20)
        group_spin.setValue(2)
        group_spin.setFixedWidth(80)
        group_spin.setFixedHeight(36)
        group_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Light theme Farben für die SpinBox
        spin_bg = "#ffffff"
        spin_fg = "#1f2937"
        spin_border = "#d1d5db"
        group_spin.setStyleSheet(f"""
            QSpinBox {{
                padding: 2px 2px 2px 2px;
                border: 2px solid {spin_border};
                border-radius: 8px;
                background: {spin_bg};
                color: {spin_fg};
                font-size: 16px;
                font-weight: 700;
                min-height: 0px;
            }}
            QSpinBox:hover {{
                border-color: #FFC000;
                background: {spin_bg};
            }}
            QSpinBox:focus {{
                border-color: #3498db;
                background: {spin_bg};
            }}
            QSpinBox::up-button {{
                width: 0px; border: none; background: none;
            }}
            QSpinBox::down-button {{
                width: 0px; border: none; background: none;
            }}
        """)
        group_ctrl_layout.addWidget(group_spin)

        auto_btn = GlassGlowButton("Auto-Zuweisen")
        auto_btn.setFixedHeight(32)
        auto_btn.setMinimumWidth(160)
        group_ctrl_layout.addWidget(auto_btn)

        add_missing_btn = GlassGlowButton("  Fehlenden Sticker +")
        add_missing_btn.setFixedHeight(32)
        add_missing_btn.setMinimumWidth(170)
        add_missing_btn.setIcon(qta.icon('ph.plus-circle', color='#374151'))
        add_missing_btn.setIconSize(QSize(16, 16))
        group_ctrl_layout.addWidget(add_missing_btn)

        group_ctrl_layout.addStretch()
        layout.addLayout(group_ctrl_layout)

        class RowDragTableWidget(QTableWidget):
            """QTableWidget mit stabilem Zeilen-Drag&Drop inkl. Cell-Widgets."""

            def __init__(self, parent=None):
                super().__init__(parent)
                self._rows_changed_callback = None
                self._group_widget_factory = None
                self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                self.customContextMenuRequested.connect(self._show_context_menu)

            def _show_context_menu(self, pos):
                row = self.rowAt(pos.y())
                if row < 0:
                    return
                menu = QMenu(self)
                delete_action = menu.addAction("Zeile löschen")
                action = menu.exec(self.viewport().mapToGlobal(pos))
                if action == delete_action:
                    self._delete_selected_rows()

            def _delete_selected_rows(self):
                rows = sorted(set(idx.row() for idx in self.selectedIndexes()), reverse=True)
                for row in rows:
                    self.removeRow(row)
                if callable(self._rows_changed_callback):
                    self._rows_changed_callback()

            def keyPressEvent(self, event):
                if event.key() == Qt.Key.Key_Delete:
                    self._delete_selected_rows()
                else:
                    super().keyPressEvent(event)

            def set_rows_changed_callback(self, callback):
                self._rows_changed_callback = callback

            def set_group_widget_factory(self, factory):
                self._group_widget_factory = factory

            def _move_row(self, source_row, target_row):
                if source_row < 0 or source_row >= self.rowCount():
                    return

                if target_row < 0:
                    target_row = self.rowCount()

                if target_row > self.rowCount():
                    target_row = self.rowCount()

                if target_row == source_row or target_row == source_row + 1:
                    return

                source_items = []
                for col in range(3):
                    src = self.item(source_row, col)
                    source_items.append(src.clone() if src is not None else None)

                source_group_idx = 0
                source_combo = self.cellWidget(source_row, 3)
                if isinstance(source_combo, QComboBox):
                    source_group_idx = source_combo.currentIndex()

                self.removeRow(source_row)

                if target_row > source_row:
                    target_row -= 1

                self.insertRow(target_row)

                for col, item in enumerate(source_items):
                    if item is not None:
                        self.setItem(target_row, col, item)

                if callable(self._group_widget_factory):
                    group_combo = self._group_widget_factory(source_group_idx)
                    self.setCellWidget(target_row, 3, group_combo)

                self.setCurrentCell(target_row, 0)

                if callable(self._rows_changed_callback):
                    self._rows_changed_callback()

            def dropEvent(self, event):
                if event.source() is self:
                    source_row = self.currentRow()
                    target_row = self.rowAt(int(event.position().y()))
                    self._move_row(source_row, target_row)
                    event.setDropAction(Qt.DropAction.CopyAction)
                    event.accept()
                    return

                super().dropEvent(event)

        # Tabelle
        # Filtere Separator-Items heraus
        sticker_items = [(i, d) for i, d in enumerate(extracted_data) if not d.get("is_separator")]

        table = RowDragTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Energy ID", "Equipment", "Beschreibung", "Gruppe"])
        table.setRowCount(len(sticker_items))
        role_orig_idx = Qt.ItemDataRole.UserRole
        role_sticker_pos = Qt.ItemDataRole.UserRole + 1
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        table.horizontalHeader().resizeSection(3, 100)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked |
            QTableWidget.EditTrigger.EditKeyPressed |
            QTableWidget.EditTrigger.AnyKeyPressed
        )
        table.setDragEnabled(True)
        table.viewport().setAcceptDrops(True)
        table.setDropIndicatorShown(True)
        table.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        table.setDefaultDropAction(Qt.DropAction.CopyAction)
        table.setDragDropOverwriteMode(False)
        table.setAlternatingRowColors(False)

        table_bg = "#ffffff"
        table_alt = "#f7f8fa"
        table_header_bg = "#f0f0f0"
        table_border = "#e0e0e0"
        table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {table_bg};
                color: {colors['fg']};
                border: 1px solid {table_border};
                border-radius: 6px;
                gridline-color: {table_border};
                font-size: 11px;
            }}
            QTableWidget::item {{
                padding: 4px 8px;
                color: {colors['fg']};
            }}
            QHeaderView::section {{
                background-color: {table_header_bg};
                color: {colors['fg']};
                padding: 6px;
                border: none;
                border-bottom: 1px solid {table_border};
                font-weight: 600;
                font-size: 11px;
            }}
        """)

        # Gruppen-Farben für visuelle Unterscheidung (kräftig & eindeutig)
        group_colors_light = ["#ffffff",   # 0 = Single (weiß/neutral)
                              "#bbdefb",   # Gruppe 1 - Blau
                              "#c8e6c9",   # Gruppe 2 - Grün
                              "#ffe0b2",   # Gruppe 3 - Orange
                              "#f8bbd0",   # Gruppe 4 - Rosa
                              "#d1c4e9",   # Gruppe 5 - Lila
                              "#b2ebf2",   # Gruppe 6 - Cyan
                              "#fff9c4",   # Gruppe 7 - Gelb
                              "#d7ccc8",   # Gruppe 8 - Braun
                              "#c5cae9",   # Gruppe 9 - Indigo
                              "#dcedc8"]   # Gruppe 10 - Limette

        def get_group_color(group_idx):
            """Liefert Hintergrundfarbe für eine Gruppe"""
            return group_colors_light[group_idx % len(group_colors_light)]

        combo_style_base = f"""
            QComboBox {{
                background-color: {spin_bg};
                color: {spin_fg};
                border: 1px solid {spin_border};
                border-radius: 3px;
                padding: 2px 6px;
                font-size: 11px;
                font-weight: 600;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {spin_bg};
                color: {spin_fg};
                border: 1px solid {spin_border};
                selection-background-color: {colors['accent']};
                selection-color: white;
            }}
        """

        def build_group_combo(current_index=0):
            combo = QComboBox()
            combo.setStyleSheet(combo_style_base)
            n = group_spin.value()
            for g in range(n + 1):
                combo.addItem(f"Gruppe {g}" if g > 0 else "0 (Single)")
            combo.setCurrentIndex(max(0, min(current_index, combo.count() - 1)))
            combo.currentIndexChanged.connect(update_row_colors)
            return combo

        def update_row_colors():
            """Aktualisiert die Zeilenfarben basierend auf der Gruppenzuordnung"""
            for row_idx in range(table.rowCount()):
                combo = table.cellWidget(row_idx, 3)
                if combo is None:
                    continue
                grp = combo.currentIndex()
                bg_color = get_group_color(grp)
                for col in range(3):
                    cell = table.item(row_idx, col)
                    if cell:
                        cell.setBackground(QColor(bg_color))

        for row, (orig_idx, data) in enumerate(sticker_items):
            energy_id = data.get("energy_id", "")
            equipment = data.get("equipment", "")
            description = data.get("description", "")

            e_item = QTableWidgetItem(energy_id)
            e_item.setData(role_orig_idx, orig_idx)
            e_item.setData(role_sticker_pos, row)
            table.setItem(row, 0, e_item)

            eq_item = QTableWidgetItem(equipment)
            eq_item.setData(role_orig_idx, orig_idx)
            eq_item.setData(role_sticker_pos, row)
            table.setItem(row, 1, eq_item)

            d_item = QTableWidgetItem(description)
            d_item.setData(role_orig_idx, orig_idx)
            d_item.setData(role_sticker_pos, row)
            table.setItem(row, 2, d_item)

            combo = build_group_combo(1 if group_spin.value() > 1 else 0)
            table.setCellWidget(row, 3, combo)

        # Interne Qt-Sortierung deaktivieren, damit Drag&Drop-Reihenfolge stabil bleibt.
        # Sortierung erfolgt stattdessen manuell per Header-Klick.
        table.setSortingEnabled(False)
        header = table.horizontalHeader()
        header.setSortIndicatorShown(True)
        header.setSectionsClickable(True)
        sort_state = {"column": 0, "order": Qt.SortOrder.AscendingOrder}

        def sort_by_column(column):
            if sort_state["column"] == column:
                sort_state["order"] = (
                    Qt.SortOrder.DescendingOrder
                    if sort_state["order"] == Qt.SortOrder.AscendingOrder
                    else Qt.SortOrder.AscendingOrder
                )
            else:
                sort_state["column"] = column
                sort_state["order"] = Qt.SortOrder.AscendingOrder

            table.sortItems(sort_state["column"], sort_state["order"])
            header.setSortIndicator(sort_state["column"], sort_state["order"])
            update_row_colors()

        header.sectionClicked.connect(sort_by_column)
        table.set_rows_changed_callback(update_row_colors)
        table.set_group_widget_factory(build_group_combo)

        # Initial nach Energy ID sortieren.
        table.sortItems(0, Qt.SortOrder.AscendingOrder)
        header.setSortIndicator(0, Qt.SortOrder.AscendingOrder)

        layout.addWidget(table, 1)

        def update_group_count():
            """Aktualisiert die Gruppen-Auswahl in allen ComboBoxes"""
            n = group_spin.value()
            for row_idx in range(table.rowCount()):
                combo = table.cellWidget(row_idx, 3)
                if combo is None:
                    continue
                current = combo.currentIndex()
                combo.blockSignals(True)
                combo.clear()
                for g in range(n + 1):  # 0 = Single, 1..n = Gruppen
                    combo.addItem(f"Gruppe {g}" if g > 0 else "0 (Single)")
                combo.setCurrentIndex(min(current, n))
                combo.blockSignals(False)
            update_row_colors()

        # Verwende die statische Methode als lokale Funktion
        extract_group_key = self._extract_group_key

        def auto_assign_groups():
            """Verteilt Sticker auf Gruppen basierend auf:
            1. Count-Sticker aus PDF (SC-Key je Gruppe)
            2. Fallback: SC-Key aus Energy-ID + Equipment der einzelnen Sticker
            Gruppen werden aufsteigend nach SC-Nummer sortiert."""

            # === Schritt 1: Alle verfügbaren Gruppen-Keys sammeln ===

            # Count-Sticker-Gruppen → SC-Key extrahieren
            cs_group_keys = {}  # SC-Key → group entries list
            if count_sticker_groups:
                for group_entries in count_sticker_groups:
                    # Bestimme den SC-Key dieser Gruppe (häufigster Key)
                    key_counts = {}
                    for entry in group_entries:
                        key = extract_group_key(entry)
                        if key:
                            key_counts[key] = key_counts.get(key, 0) + 1
                    if key_counts:
                        group_key = max(key_counts, key=key_counts.get)
                        cs_group_keys[group_key] = group_entries

            # === Schritt 2: Sticker ihren Gruppen zuordnen ===
            sticker_key_map = {}  # row → SC-Key
            all_keys = set()

            for row, (orig_idx, data) in enumerate(sticker_items):
                energy_id = data.get("energy_id", "").strip()
                equipment = data.get("equipment", "").strip()
                description = data.get("description", "").strip()
                key = extract_group_key(energy_id, equipment, description)
                if key:
                    sticker_key_map[row] = key
                    all_keys.add(key)
                else:
                    sticker_key_map[row] = None

            # === Schritt 3: Alle Gruppen-Keys sortieren (aufsteigend) ===
            def key_sort(k):
                sc_match = re.match(r'SC_(\d+)\.(\d+)', k)
                if sc_match:
                    return (0, int(sc_match.group(1)), int(sc_match.group(2)))
                # NSHV, UV-H etc. nach SC-Gruppen
                return (1, 0, hash(k) % 1000)

            sorted_keys = sorted(all_keys, key=key_sort)

            # Key → Gruppen-Index (1-basiert)
            key_to_group = {key: idx + 1 for idx, key in enumerate(sorted_keys)}
            num_groups = len(sorted_keys)

            if num_groups < 1:
                return

            # === Schritt 4: Gruppenanzahl setzen und zuweisen ===
            group_spin.setValue(num_groups)
            update_group_count()

            for row, (orig_idx, data) in enumerate(sticker_items):
                key = sticker_key_map.get(row)
                group_idx = key_to_group.get(key, 0) if key else 0
                target_row = None
                for r in range(table.rowCount()):
                    energy_item = table.item(r, 0)
                    if energy_item and energy_item.data(role_sticker_pos) == row:
                        target_row = r
                        break
                if target_row is not None:
                    combo = table.cellWidget(target_row, 3)
                    if combo is not None:
                        combo.setCurrentIndex(min(group_idx, combo.count() - 1))

            # Logging
            cs_keys_found = set(cs_group_keys.keys()) & all_keys
            fallback_keys = all_keys - set(cs_group_keys.keys())
            logger.info(f"Auto-Zuweisen: {num_groups} Gruppen gesamt "
                       f"({len(cs_keys_found)} aus Count-Stickern, {len(fallback_keys)} aus Sticker-Analyse)")
            logger.info(f"  Gruppen: {sorted_keys}")

            update_row_colors()

        def add_missing_sticker():
            """Öffnet Dialog mit erkannten fehlenden Stickern + manueller Eingabe."""

            # Fehlende Sticker berechnen (Count-Sticker-Einträge ohne passenden Sticker)
            missing_entries = []
            if count_sticker_groups:
                missing_entries = self._detect_missing_stickers(extracted_data, count_sticker_groups)
            # Auch Lücken in E-Nummern-Sequenzen erkennen (für Gruppen ohne Count-Sticker-Daten)
            gap_missing = self._detect_missing_from_group_gaps(extracted_data, count_sticker_groups)
            for entry in gap_missing:
                if entry not in missing_entries:
                    missing_entries.append(entry)

            # Gestylter Dialog
            input_dlg = QDialog(dialog)
            input_dlg.setWindowTitle("Fehlende Sticker hinzufügen")
            input_dlg.setModal(True)
            input_dlg.setFixedWidth(520)
            input_dlg.setStyleSheet(create_dialog_stylesheet(theme))

            dlg_layout = QVBoxLayout(input_dlg)
            dlg_layout.setSpacing(10)
            dlg_layout.setContentsMargins(24, 20, 24, 20)

            input_bg = "#ffffff"
            input_fg = "#111111"
            input_border = "#b0b0b0"
            card_bg = "rgba(0,0,0,0.02)"
            card_border = "rgba(0,0,0,0.08)"

            # --- Abschnitt: Erkannte fehlende Sticker ---
            checkboxes = []
            if missing_entries:
                sec_label = QLabel(f"Erkannte fehlende Sticker ({len(missing_entries)}):")
                sec_label.setStyleSheet(f"color: {colors['fg']}; font-size: 13px; font-weight: 600; border: none;")
                dlg_layout.addWidget(sec_label)

                scroll = QScrollArea()
                scroll.setWidgetResizable(True)
                scroll.setMaximumHeight(min(len(missing_entries) * 36 + 16, 200))
                scroll.setStyleSheet(f"""
                    QScrollArea {{
                        background: transparent;
                        border: 1px solid {card_border};
                        border-radius: 6px;
                    }}
                """)
                scroll_w = QWidget()
                scroll_w.setStyleSheet("background: transparent;")
                scroll_lay = QVBoxLayout(scroll_w)
                scroll_lay.setSpacing(2)
                scroll_lay.setContentsMargins(6, 6, 6, 6)

                for entry in missing_entries:
                    cb = QCheckBox(entry)
                    cb.setChecked(True)
                    cb.setStyleSheet(f"""
                        QCheckBox {{
                            color: {colors['fg']};
                            font-size: 12px;
                            font-family: 'Consolas', 'Courier New', monospace;
                            padding: 4px 6px;
                            background: {card_bg};
                            border-radius: 4px;
                            border: none;
                        }}
                        QCheckBox::indicator {{
                            width: 14px; height: 14px;
                            border-radius: 3px;
                            border: 1.5px solid rgba(128,128,128,0.3);
                        }}
                        QCheckBox::indicator:checked {{
                            background: {colors['accent']};
                            border: 1.5px solid {colors['accent']};
                        }}
                        QCheckBox::indicator:hover {{
                            border: 1.5px solid {colors['accent']};
                        }}
                    """)
                    scroll_lay.addWidget(cb)
                    checkboxes.append((cb, entry))

                scroll_lay.addStretch()
                scroll.setWidget(scroll_w)
                dlg_layout.addWidget(scroll)

                # Trenner
                sep = QLabel("")
                sep.setFixedHeight(1)
                sep.setStyleSheet(f"background: {card_border}; border: none;")
                dlg_layout.addWidget(sep)

            # --- Abschnitt: Manuelle Eingabe ---
            man_label = QLabel("Manuell hinzufügen:")
            man_label.setStyleSheet(f"color: {colors['fg']}; font-size: 13px; font-weight: 600; border: none;")
            dlg_layout.addWidget(man_label)

            input_field = QLineEdit()
            input_field.setPlaceholderText("z.B. E1.ELEC.DP.XYZ")
            input_field.setReadOnly(False)
            input_field.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {input_bg};
                    color: {input_fg};
                    border: 1.5px solid {input_border};
                    border-radius: 6px;
                    padding: 8px 12px;
                    font-size: 13px;
                    font-family: 'Consolas', 'Courier New', monospace;
                    selection-background-color: {colors['accent']};
                    selection-color: white;
                }}
                QLineEdit:focus {{
                    border-color: {colors['accent']};
                }}
            """)
            dlg_layout.addWidget(input_field)

            # --- Buttons ---
            dlg_btns = QHBoxLayout()
            dlg_btns.addStretch()
            cancel_b = GlassGlowButton("Abbrechen")
            cancel_b.setFixedHeight(34)
            cancel_b.clicked.connect(input_dlg.reject)
            dlg_btns.addWidget(cancel_b)
            add_b = GlassGlowButton("  Hinzufügen")
            add_b.setFixedHeight(34)
            add_b.setIcon(qta.icon('ph.plus-circle', color='#374151'))
            add_b.setIconSize(QSize(15, 15))
            add_b.clicked.connect(input_dlg.accept)
            dlg_btns.addWidget(add_b)
            dlg_layout.addLayout(dlg_btns)

            input_field.returnPressed.connect(input_dlg.accept)
            if not missing_entries:
                input_field.setFocus()

            if input_dlg.exec() != QDialog.DialogCode.Accepted:
                return

            # Alle zu erstellenden Einträge sammeln
            entries_to_add = []

            # Aus Checkboxen
            for cb, entry in checkboxes:
                if cb.isChecked():
                    entries_to_add.append(entry)

            # Aus manuellem Feld
            manual_text = input_field.text().strip().upper()
            if manual_text:
                entries_to_add.append(manual_text)

            if not entries_to_add:
                return

            # Sticker erstellen und zur Tabelle hinzufügen
            for entry_text in entries_to_add:
                match = re.match(r'^([EPMC]\d+)\.(.+)$', entry_text, re.IGNORECASE)
                if match:
                    energy_id = match.group(1).upper()
                    equipment = match.group(2)
                else:
                    energy_id = entry_text
                    equipment = ""

                prefix = energy_id[0] if energy_id else 'E'
                sym_map = {'P': 'PNEUMATIC', 'M': 'MECHANICAL', 'C': 'CHEMICAL'}
                symbol_type = sym_map.get(prefix, 'ELECTRICAL')

                new_sticker = {
                    'energy_id': energy_id,
                    'equipment': equipment,
                    'symbol_type': symbol_type,
                    'description': '',
                    '_created_from_count': True,
                }

                # Zur extracted_data hinzufügen
                extracted_data.append(new_sticker)
                orig_idx = len(extracted_data) - 1
                sticker_items.append((orig_idx, new_sticker))

                # Neue Zeile in Tabelle
                new_row = table.rowCount()
                table.setRowCount(new_row + 1)

                e_item = QTableWidgetItem(energy_id)
                sticker_pos = len(sticker_items) - 1
                e_item.setData(role_orig_idx, orig_idx)
                e_item.setData(role_sticker_pos, sticker_pos)
                table.setItem(new_row, 0, e_item)

                eq_item = QTableWidgetItem(equipment)
                eq_item.setData(role_orig_idx, orig_idx)
                eq_item.setData(role_sticker_pos, sticker_pos)
                table.setItem(new_row, 1, eq_item)

                d_item = QTableWidgetItem('')
                d_item.setData(role_orig_idx, orig_idx)
                d_item.setData(role_sticker_pos, sticker_pos)
                table.setItem(new_row, 2, d_item)

                combo = build_group_combo(0)
                table.setCellWidget(new_row, 3, combo)

                logger.info(f'Fehlender Sticker hinzugefuegt: {energy_id} / {equipment}')

            # Auto-Zuweisen neu ausführen, um die Sticker richtig einzuordnen
            auto_assign_groups()

        group_spin.valueChanged.connect(update_group_count)
        auto_btn.clicked.connect(auto_assign_groups)
        add_missing_btn.clicked.connect(add_missing_sticker)

        # Initial: Gruppierung initialisieren
        update_group_count()
        update_row_colors()

        # Automatisch zuweisen wenn Count-Sticker-Gruppen vorhanden
        if count_sticker_groups:
            auto_assign_groups()

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        button_layout.addStretch()

        cancel_btn = GlassGlowButton("Abbrechen")
        cancel_btn.setMinimumHeight(44)
        cancel_btn.setMinimumWidth(140)
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)

        ok_btn = GlassGlowButton("Übernehmen")
        ok_btn.setMinimumHeight(44)
        ok_btn.setMinimumWidth(160)
        ok_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(ok_btn)

        layout.addLayout(button_layout)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None

        # Geaenderte Tabellenwerte ins Datenmodell uebernehmen.
        for row in range(table.rowCount()):
            energy_item = table.item(row, 0)
            if energy_item is None:
                continue

            orig_idx = energy_item.data(role_orig_idx)
            if not isinstance(orig_idx, int) or not (0 <= orig_idx < len(extracted_data)):
                continue

            equipment_item = table.item(row, 1)
            description_item = table.item(row, 2)

            energy_id = (energy_item.text() if energy_item else "").strip()
            equipment = (equipment_item.text() if equipment_item else "").strip()
            description = (description_item.text() if description_item else "").strip()

            extracted_data[orig_idx]["energy_id"] = energy_id
            extracted_data[orig_idx]["equipment"] = equipment
            extracted_data[orig_idx]["description"] = description

            # Symboltyp konsistent zur ggf. geaenderten Energy-ID halten.
            prefix = energy_id[:1].upper()
            symbol_map = {
                'P': 'PNEUMATIC',
                'M': 'MECHANICAL',
                'C': 'CHEMICAL',
                'E': 'ELECTRICAL',
            }
            if prefix in symbol_map:
                extracted_data[orig_idx]["symbol_type"] = symbol_map[prefix]

        # Ergebnis zusammenbauen: sticker_index -> group_name
        result = {}
        single_members = []  # (sticker_idx, equipment)

        # Erst Gruppen-Zuordnung sammeln (group_idx -> list of (sticker_idx, equipment))
        group_members = {}
        for row in range(table.rowCount()):
            energy_item = table.item(row, 0)
            combo = table.cellWidget(row, 3)
            if energy_item is None or combo is None:
                continue

            sticker_idx = energy_item.data(role_sticker_pos)
            if not isinstance(sticker_idx, int):
                continue

            eq_item = table.item(row, 1)
            eq_text = (eq_item.text() if eq_item else "").strip()

            group_idx = combo.currentIndex()
            if group_idx == 0:
                single_members.append((sticker_idx, eq_text))
            else:
                group_members.setdefault(group_idx, []).append((sticker_idx, eq_text))

        # Gruppenname aus gemeinsamem Equipment-Prefix ableiten
        def _common_prefix(strings):
            if not strings:
                return ""
            prefix = strings[0]
            for s in strings[1:]:
                while not s.startswith(prefix) and prefix:
                    # Am letzten Punkt oder Ende abschneiden
                    dot_pos = prefix.rfind(".")
                    if dot_pos > 0:
                        prefix = prefix[:dot_pos]
                    else:
                        prefix = ""
            return prefix.rstrip(".")

        # Gruppenname pro Gruppe bestimmen (erste Runde)
        group_name_map = {}
        for group_idx, members in group_members.items():
            equips = [eq for _, eq in members if eq]
            common = _common_prefix(equips)
            group_name_map[group_idx] = common if common else f"Gruppe {group_idx}"

        # Duplikate erkennen: wenn mehrere Gruppen denselben Namen hätten, Fallback auf "Gruppe N"
        name_counts = {}
        for name in group_name_map.values():
            name_counts[name] = name_counts.get(name, 0) + 1
        for group_idx in group_name_map:
            if name_counts[group_name_map[group_idx]] > 1:
                group_name_map[group_idx] = f"Gruppe {group_idx}"

        for group_idx, members in group_members.items():
            group_name = group_name_map[group_idx]
            for sticker_idx, _ in members:
                result[sticker_idx] = group_name

        # Single-Items: alle in eine gemeinsame Gruppe "Single LOTO Count"
        for sticker_idx, eq_text in single_members:
            result[sticker_idx] = "SINGLE_Single LOTO Count"

        return result

    # ── Main Import ─────────────────────────────────────────────────

    def import_stickers_from_pdf(self):
        """Importiert Sticker aus einer PDF-Datei."""
        from ui.glass_button import GlassGlowButton
        from ui.theme import Theme, get_theme_colors, create_dialog_stylesheet
        from dialogs.pdf_import_dialog import PDFImportDialog
        from controllers import CollectionController

        dialog = PDFImportDialog(self.app, sticker_config=self.sticker_service.generator.cfg)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Data is already extracted in the dialog
            extracted_data = dialog.extracted_data
            import_qr_path = getattr(dialog, "import_qr_path", None)
            count_sticker_groups = getattr(dialog, "count_sticker_groups", [])

            if count_sticker_groups:
                logger.info(f"PDF Import: {len(count_sticker_groups)} Count-Sticker-Gruppen erkannt: {count_sticker_groups}")

            # Fehlende Sticker erkennen und optional erstellen
            if count_sticker_groups and extracted_data:
                missing = self._detect_missing_stickers(extracted_data, count_sticker_groups)
                if missing:
                    selected = self._show_missing_stickers_dialog(missing)
                    if selected:
                        created = self._create_stickers_from_entries(extracted_data, selected)
                        logger.info(f"PDF Import: {created} fehlende Sticker erstellt")

            if not extracted_data:
                msg = self._create_styled_msgbox("Info", "Keine Daten zum Importieren gefunden.", QMessageBox.Icon.Warning)
                msg.exec()
                return

            # Frage nach Single/Multi LOTO Modus mit gestyltem Dialog

            mode_dialog = QDialog(self.app)
            mode_dialog.setWindowTitle("LOTO Modus wählen")
            mode_dialog.setModal(True)
            mode_dialog.setFixedWidth(450)

            # Theme-basiertes Styling
            theme = getattr(self.app, 'theme', Theme.LIGHT)
            colors = get_theme_colors(theme)
            text_color = colors["fg"]
            radio_accent = colors["accent"]
            mode_dialog.setStyleSheet(create_dialog_stylesheet(theme))

            layout = QVBoxLayout(mode_dialog)
            layout.setSpacing(15)
            layout.setContentsMargins(25, 20, 25, 20)

            # Titel
            title = QLabel("Welchen LOTO Modus möchten Sie verwenden?")
            title.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {text_color}; padding-bottom: 5px;")
            layout.addWidget(title)

            # Radio Buttons mit Phosphor Icons
            radio_layout = QVBoxLayout()
            radio_layout.setSpacing(10)

            button_group = QButtonGroup(mode_dialog)

            single_radio = QRadioButton("  Single LOTO")
            single_radio.setToolTip("Ein Count-Sticker pro LOTO-Point")
            single_radio.setIcon(qta.icon('ph.lock', color=text_color))
            single_radio.setIconSize(QSize(18, 18))

            multi_radio = QRadioButton("  Multi LOTO")
            multi_radio.setToolTip("Ein Count-Sticker für alle LOTO-Points")
            multi_radio.setIcon(qta.icon('ph.lock-open', color=text_color))
            multi_radio.setIconSize(QSize(18, 18))

            custom_radio = QRadioButton("  Selbstauswahl")
            custom_radio.setToolTip("Sticker manuell in Multi-LOTO Gruppen einteilen")
            custom_radio.setIcon(qta.icon('ph.wrench', color=text_color))
            custom_radio.setIconSize(QSize(18, 18))

            button_group.addButton(single_radio)
            button_group.addButton(multi_radio)
            button_group.addButton(custom_radio)

            # Setze Standard basierend auf aktueller Auswahl
            current_is_single = getattr(self.app, 'single_loto_radio', None) and self.app.single_loto_radio.isChecked()
            if current_is_single:
                single_radio.setChecked(True)
            else:
                multi_radio.setChecked(True)

            radio_style = f"""
                QRadioButton {{
                    color: {text_color};
                    font-size: 13px;
                    font-weight: 400;
                    spacing: 10px;
                    padding: 6px 12px;
                }}
                QRadioButton::indicator {{
                    width: 16px;
                    height: 16px;
                    border-radius: 8px;
                    border: 1.5px solid rgba(128, 128, 128, 0.3);
                    background: transparent;
                }}
                QRadioButton::indicator:hover {{
                    border: 1.5px solid {radio_accent};
                }}
                QRadioButton::indicator:checked {{
                    border: 1.5px solid {radio_accent};
                    background: qradialgradient(cx:0.5, cy:0.5, radius:0.5,
                        fx:0.5, fy:0.5,
                        stop:0 {radio_accent},
                        stop:0.4 {radio_accent},
                        stop:0.5 transparent,
                        stop:1 transparent);
                }}
            """
            single_radio.setStyleSheet(radio_style)
            multi_radio.setStyleSheet(radio_style)
            custom_radio.setStyleSheet(radio_style)

            radio_layout.addWidget(single_radio)
            radio_layout.addWidget(multi_radio)
            radio_layout.addWidget(custom_radio)
            layout.addLayout(radio_layout)

            layout.addSpacing(10)

            # Buttons
            button_layout = QHBoxLayout()
            button_layout.setSpacing(10)
            button_layout.addStretch()

            cancel_btn = GlassGlowButton("Abbrechen")
            cancel_btn.setMinimumHeight(44)
            cancel_btn.setMinimumWidth(140)
            cancel_btn.clicked.connect(mode_dialog.reject)
            button_layout.addWidget(cancel_btn)

            ok_btn = GlassGlowButton("Importieren")
            ok_btn.setMinimumHeight(44)
            ok_btn.setMinimumWidth(160)
            ok_btn.clicked.connect(mode_dialog.accept)
            button_layout.addWidget(ok_btn)

            layout.addLayout(button_layout)

            # Dialog ausführen
            if mode_dialog.exec() != QDialog.DialogCode.Accepted:
                return  # Abgebrochen

            # Modus bestimmen
            is_single_mode = single_radio.isChecked()
            is_multi_mode = multi_radio.isChecked()
            is_custom_mode = custom_radio.isChecked()

            # Bei Selbstauswahl: Gruppierungs-Dialog anzeigen
            custom_groups = None
            if is_custom_mode:
                custom_groups = self._show_loto_grouping_dialog(extracted_data, count_sticker_groups)
                if custom_groups is None:
                    return  # Abgebrochen

            # Mapping fuer spaetere Uebergabe an Equipment-Import: extracted_data-index -> Gruppenname
            custom_group_by_extracted_index = {}
            if is_custom_mode and custom_groups:
                filtered_indices = [idx for idx, d in enumerate(extracted_data) if not d.get("is_separator")]
                for sticker_pos, group_name in custom_groups.items():
                    if isinstance(sticker_pos, int) and 0 <= sticker_pos < len(filtered_indices):
                        custom_group_by_extracted_index[filtered_indices[sticker_pos]] = group_name
                logger.info(f"custom_group_by_extracted_index: {len(custom_group_by_extracted_index)} Eintraege, "
                           f"custom_groups: {len(custom_groups)} Eintraege, "
                           f"filtered_indices: {len(filtered_indices)} Eintraege")

            imported_count = 0

            # Use embedded progress bar from Magic Menu
            progress_bar = None
            if hasattr(self.app, 'magic_menu'):
                progress_bar = self.app.magic_menu.progress_bar
                progress_bar.setRange(0, len(extracted_data))
                progress_bar.setValue(0)
                progress_bar.setVisible(True)

            # PDF-Import: Neuen Generator mit QR aus PDF (falls gefunden)
            from generators.sticker_generator import StickerGenerator
            from core.models import StickerConfig

            # Komplett neue Config ohne QR erstellen (nicht replace, sondern neue Instanz)
            orig_cfg = self.sticker_service.generator.cfg
            import_cfg = StickerConfig(
                width_mm=orig_cfg.width_mm,
                height_mm=orig_cfg.height_mm,
                dpi=orig_cfg.dpi,
                corner_radius=orig_cfg.corner_radius,
                outline_width=orig_cfg.outline_width,
                font_path=orig_cfg.font_path,
                auto_adjust=orig_cfg.auto_adjust,
                sticker_color=orig_cfg.sticker_color,
                font_size_mm=orig_cfg.font_size_mm,
                line_height_mm=orig_cfg.line_height_mm,
                symbols_dir=orig_cfg.symbols_dir,
                symbol_corner_radius=orig_cfg.symbol_corner_radius,
                symbol_size_mm=orig_cfg.symbol_size_mm,
                symbol_offset_x_mm=orig_cfg.symbol_offset_x_mm,
                symbol_offset_y_mm=orig_cfg.symbol_offset_y_mm,
                text_offset_x=orig_cfg.text_offset_x,
                text_offset_y=orig_cfg.text_offset_y,
                qr_mode_enabled=bool(import_qr_path),
                qr_placeholder_text="QR",
                qr_placeholder_bg="#FFFFFF",
                qr_image_path=import_qr_path,
                preview_scale=orig_cfg.preview_scale,
                export_exact_three_rows=orig_cfg.export_exact_three_rows,
                export_margin_mm=orig_cfg.export_margin_mm,
                export_gap_mm=orig_cfg.export_gap_mm,
                export_min_scale=orig_cfg.export_min_scale
            )

            # Neuen Generator für Import erstellen
            import_generator = StickerGenerator(import_cfg)
            import_generator._qr_cache.clear()  # Cache leeren
            logger.info(f"PDF Import: qr_mode_enabled={import_cfg.qr_mode_enabled}, qr_image_path={import_cfg.qr_image_path}")

            # WICHTIG: Setze QR auch für den Haupt-Generator, damit Vorschau funktioniert
            if import_qr_path:
                logger.info(f"Setze QR auch für Haupt-Generator: {import_qr_path}")
                self.sticker_service.generator.cfg.qr_mode_enabled = True
                self.sticker_service.generator.cfg.qr_image_path = import_qr_path
                # Cache leeren, damit der neue QR geladen wird
                self.sticker_service.generator._qr_cache.clear()

            try:
                for i, data in enumerate(extracted_data):
                    if data.get("is_separator"):
                        if progress_bar: progress_bar.setValue(i + 1)
                        continue

                    # Bei Selbstauswahl: gelöschte Zeilen überspringen
                    if is_custom_mode and custom_group_by_extracted_index and i not in custom_group_by_extracted_index:
                        if progress_bar: progress_bar.setValue(i + 1)
                        continue

                    energy_id = data.get("energy_id", "UNKNOWN")
                    equipment = data.get("equipment", "Imported")
                    description = data.get("description", "")
                    symbol_type = data.get("symbol_type", "ELECTRICAL")
                    sticker_qr_path = data.get("qr_path", "") or import_qr_path or ""  # Individueller QR pro Sticker

                    # Generate sticker image mit Import-Generator
                    try:
                        # Individuellen QR-Pfad für diesen Sticker setzen
                        if sticker_qr_path:
                            import_cfg.qr_mode_enabled = True
                            import_cfg.qr_image_path = sticker_qr_path
                        else:
                            import_cfg.qr_mode_enabled = False
                            import_cfg.qr_image_path = None
                        import_generator._qr_cache.clear()
                        import_generator._img_cache.clear()

                        # Symbol-Typ ermitteln
                        from core.models import SymbolType
                        sym_type = SymbolType.ELECTRICAL
                        try:
                            sym_type = SymbolType[symbol_type.upper()]
                        except (KeyError, AttributeError):
                            sym_type = SymbolType.ELECTRICAL

                        lines = [energy_id, equipment]
                        if description:
                            lines.append(description)

                        # Direkt mit Import-Generator generieren
                        image = import_generator.generate(sym_type, lines)
                        logger.info(f"Sticker generiert für {energy_id}: QR-Mode={import_cfg.qr_mode_enabled}, QR-Path={import_cfg.qr_image_path}")

                        # Add to collection service
                        self.collection_service.add_item(
                            energy_id=energy_id,
                            equipment=equipment,
                            symbol_type=symbol_type,
                            description=description,
                            image=image
                        )

                        # Add to legacy collection list (required for UI update)
                        custom_group = custom_group_by_extracted_index.get(i, "")
                        # SINGLE_-Prefix nur intern für Count-Sticker-Logik, nicht für Equipment-Manager
                        equipment_group = custom_group.replace("SINGLE_", "") if custom_group.startswith("SINGLE_") else custom_group
                        full_info = {
                            "text": f"{energy_id} {equipment} {description}".strip(),
                            "qr_path": sticker_qr_path,  # Individueller QR-Pfad pro Sticker!
                            "group": equipment_group,
                        }
                        self.app._add_to_collection_with_thumbnail(
                            image,
                            symbol_type,
                            energy_id,
                            equipment,
                            description,
                            full_info
                        )

                        # Bei Single LOTO: Count Sticker pro Item hinzufügen
                        if is_single_mode:
                            try:
                                count_detail = full_info.get("text", f"{energy_id} {equipment} {description}".strip())
                                count_img = self.count_generator.generate(count_detail, 1)
                                self.collection.append([count_img, "COUNT_SINGLE", f"C_{energy_id}", "", count_detail, "count_single", count_img])
                            except Exception as e:
                                logger.warning(f"Count Sticker konnte nicht generiert werden (PDF Import): {e}")

                        imported_count += 1
                    except Exception as e:
                        logger.error(f"Error generating sticker for {energy_id}: {e}")

                    if progress_bar:
                        progress_bar.setValue(i + 1)
                    QApplication.processEvents()

                if progress_bar:
                    progress_bar.setVisible(False)

                if imported_count > 0:
                    # Bei Multi-LOTO Modus: Count-Sticker per Gruppe hinzufügen
                    if is_multi_mode:
                        try:
                            self.app._regenerate_multi_count_sticker()
                        except Exception as e:
                            logger.warning(f"Multi Count Sticker konnte nicht erstellt werden: {e}")

                    # Bei Selbstauswahl: Count-Sticker pro Gruppe
                    if is_custom_mode and custom_groups:
                        try:
                            # Entferne alte Count Sticker
                            i = len(self.collection) - 1
                            while i >= 0:
                                item = self.collection[i]
                                if CollectionController._is_count_multi(item) or CollectionController._is_count_single(item):
                                    self.collection.pop(i)
                                i -= 1

                            # Baue Gruppen-Zuordnung: group_name -> [sticker indices]
                            # custom_groups ist dict: row_index (in sticker_items) -> group_name
                            groups = {}
                            for idx, group_name in custom_groups.items():
                                if group_name not in groups:
                                    groups[group_name] = []
                                groups[group_name].append(idx)

                            # Filtere sticker_items (ohne Separatoren) für den Zugriff
                            filtered_sticker_items = [(i, d) for i, d in enumerate(extracted_data) if not d.get("is_separator")]

                            # Für jede Gruppe einen Count-Sticker generieren
                            for group_name, sticker_indices in sorted(groups.items()):
                                group_details = []
                                for idx in sticker_indices:
                                    if idx < len(filtered_sticker_items):
                                        _, data_item = filtered_sticker_items[idx]
                                        item_energy = data_item.get("energy_id", "")
                                        item_equipment = data_item.get("equipment", "")
                                        item_description = data_item.get("description", "")
                                        detail = f"{item_energy} {item_equipment} {item_description}".strip()
                                        if detail:
                                            group_details.append(detail)

                                if group_details:
                                    import re as _re_sort
                                    group_details.sort(key=lambda s: [int(t) if t.isdigit() else t.lower() for t in _re_sort.split(r'(\d+)', s)])
                                    group_count = len(group_details)
                                    detail_str = ', '.join(group_details)

                                    if group_name.startswith("SINGLE_"):
                                        # Single LOTO: Ein Count-Sticker PRO Item
                                        for detail in group_details:
                                            first_energy = detail.split()[0] if detail else "UNKNOWN"
                                            logger.info(f"Custom Single Count für '{first_energy}': {detail[:80]}")
                                            count_img = self.count_generator.generate(detail, 1)
                                            self.collection.append([
                                                count_img, "COUNT_SINGLE", f"C_{first_energy}", "", detail,
                                                {"type": "count_single", "copies": 1}, count_img
                                            ])
                                    else:
                                        # Multi-LOTO Gruppe
                                        logger.info(f"Custom Group '{group_name}': {group_count} Items, Details: {detail_str[:100]}...")
                                        count_img = self.count_generator.generate(detail_str, group_count)
                                        self.collection.append([
                                            count_img, "COUNT_MULTI", f"TOTAL_{group_name}", "", "",
                                            {"type": "count_multi", "details": detail_str, "group": group_name},
                                            count_img
                                        ])
                        except Exception as e:
                            logger.warning(f"Custom Group Count Sticker konnte nicht erstellt werden: {e}")

                    self.app.update_collection_list()  # Ensure UI is updated

            except Exception as e:
                logger.error(f"PDF Import fehlgeschlagen: {e}")
                msg = self._create_styled_msgbox("Fehler", f"PDF-Import fehlgeschlagen:\n{e}", QMessageBox.Icon.Critical)
                msg.exec()
            finally:
                if hasattr(dialog, "cleanup_temp_files"):
                    dialog.cleanup_temp_files()
                if progress_bar:
                    progress_bar.setVisible(False)

    # ── Config Serialization ────────────────────────────────────────

    def _serialize_current_sticker_config(self) -> dict:
        """Serialisiert die aktuelle Sticker-Konfiguration zu einem Dict."""
        cfg = self.sticker_service.generator.cfg
        count_cfg = self.count_config

        return {
            # LOTO Sticker Config
            "width_mm": cfg.width_mm,
            "height_mm": cfg.height_mm,
            "dpi": cfg.dpi,
            "corner_radius": cfg.corner_radius,
            "outline_width": cfg.outline_width,
            "font_path": cfg.font_path,
            "auto_adjust": cfg.auto_adjust,
            "sticker_color": cfg.sticker_color,
            "font_size_mm": cfg.font_size_mm,
            "line_height_mm": cfg.line_height_mm,
            "symbol_corner_radius": cfg.symbol_corner_radius,
            "symbol_size_mm": cfg.symbol_size_mm,
            "symbol_offset_x_mm": cfg.symbol_offset_x_mm,
            "symbol_offset_y_mm": cfg.symbol_offset_y_mm,
            "text_offset_x": cfg.text_offset_x,
            "text_offset_y": cfg.text_offset_y,
            "qr_mode_enabled": cfg.qr_mode_enabled,
            "qr_placeholder_text": cfg.qr_placeholder_text,
            "qr_placeholder_bg": cfg.qr_placeholder_bg,
            "qr_image_path": cfg.qr_image_path,
            "preview_scale": cfg.preview_scale,
            "export_exact_three_rows": cfg.export_exact_three_rows,
            "export_margin_mm": cfg.export_margin_mm,
            "export_gap_mm": cfg.export_gap_mm,
            "export_min_scale": cfg.export_min_scale,
            "loto_mode_single": getattr(self.app, 'single_loto_radio', None) and self.app.single_loto_radio.isChecked(),

            # Count Sticker Config
            "count_width_mm": count_cfg.width_mm,
            "count_height_mm": count_cfg.height_mm,
            "count_dpi": count_cfg.dpi,
            "count_corner_radius": count_cfg.corner_radius,
            "count_outline_width": count_cfg.outline_width,
            "count_font_path": count_cfg.font_path,
            "count_auto_adjust": count_cfg.auto_adjust,
            "count_font_size_mm": count_cfg.font_size_mm,
            "count_line_height_mm": count_cfg.line_height_mm,
            "count_header_text": count_cfg.header_text,
            "count_bg_color": count_cfg.bg_color,
            "count_stripe_color": count_cfg.stripe_color,
            "count_show_stripes": count_cfg.show_stripes,
            "count_header_margin_mm": count_cfg.header_margin_mm,
            "count_text_spacing_mm": count_cfg.text_spacing_mm
        }

    def _sync_settings_to_equipment_manager(self):
        """Schreibt die aktuelle Sticker-/Count-Config zurück in den Equipment-Manager
        für alle Items, die aus dem Equipment-Manager in der Collection geladen wurden."""
        try:
            if not hasattr(self.app, 'equipment_service'):
                return
            equipment_manager = self.equipment_service.get_manager()
            if not equipment_manager:
                return

            sticker_config = self._serialize_current_sticker_config()
            updated_count = 0

            from controllers import CollectionController
            for item in getattr(self.app, 'collection', []):
                if CollectionController._is_count_single(item) or CollectionController._is_count_multi(item):
                    continue
                if len(item) < 6:
                    continue

                full_info = item[5] if isinstance(item[5], dict) else {}
                location = full_info.get("location", "")
                system = full_info.get("system", "")
                if not location or not system:
                    continue

                energy_id = item[2] if len(item) > 2 else ""
                equipment_name = item[3] if len(item) > 3 else ""
                if not equipment_name:
                    continue

                updated = equipment_manager.update_equipment_properties(
                    location, system, equipment_name,
                    sticker_config=sticker_config,
                    match_energy_id=energy_id if energy_id else None
                )
                if updated:
                    updated_count += 1

            if updated_count > 0:
                equipment_manager.save_equipment()
                if hasattr(self.app, 'equipment_controller'):
                    self.app.equipment_controller.refresh_tree()
                logger.info(f"Sticker-Config für {updated_count} Equipment(s) im Equipment-Manager aktualisiert")
                if self.status_bar:
                    self.status_bar.showMessage(
                        f"Einstellungen für {updated_count} Equipment(s) übernommen", 3000
                    )
        except Exception as e:
            logger.error(f"Fehler beim Sync der Einstellungen zum Equipment-Manager: {e}")

    def import_collection_to_equipment_manager(self):
        """Übernimmt Sticker aus der Ablage in den Equipment-Manager (mit Abfrage)."""
        from dialogs.equipment_import_dialog import EquipmentImportDialog
        from controllers import CollectionController

        if not hasattr(self.app, 'equipment_service'):
            return

        # Sammle nur LOTO-Sticker (keine Count-Sticker)
        items = []
        for item in getattr(self.app, 'collection', []):
            if CollectionController._is_count_single(item) or CollectionController._is_count_multi(item):
                continue
            if len(item) >= 5:
                # full_info kann String oder Dict sein
                full_info = item[5] if len(item) > 5 else {}
                qr_path = ""
                group_name = ""
                if isinstance(full_info, dict):
                    qr_path = full_info.get("qr_path", "")
                    group_name = full_info.get("group", "")
                logger.info(f"DEBUG import_collection: full_info={full_info}, qr_path={qr_path}")

                # Aktuelle Sticker-Config serialisieren
                sticker_config = self._serialize_current_sticker_config()

                items.append({
                    "energy_id": item[2],
                    "equipment": item[3],
                    "description": item[4],
                    "symbol_type": item[1],
                    "qr_path": qr_path,
                    "sticker_config": sticker_config,
                    "group": group_name,
                })

        if not items:
            msg = self._create_styled_msgbox("Info", "Keine LOTO-Sticker in der Ablage gefunden.", QMessageBox.Icon.Information)
            msg.exec()
            return

        dialog = EquipmentImportDialog(self.app, items, self.equipment_service.get_manager())
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        selected_items = dialog.selected_items
        if not selected_items:
            return

        equipment_manager = self.equipment_service.get_manager()
        imported = 0

        def _normalize_equipment_name(name: str) -> str:
            """Entfernt alle Energy-ID Suffixe [Exx] aus dem Namen.
            Die Energy-ID wird separat im energy_id Feld gespeichert."""
            base = name.strip()
            # Entferne alle energy-id tokens [Exx] aus dem Namen
            base = re.sub(r"\s*\[E\d+\]\s*", " ", base, flags=re.IGNORECASE).strip()
            return base

        for it in selected_items:
            try:
                location = it["location"]
                system = it["system"]
                equipment_name = it.get("equipment", "").strip()
                energy_id = it.get("energy_id", "").strip()
                symbol_type = it.get("symbol_type", "").strip()
                description = it.get("description", "").strip()
                # Normalize name: entferne Energy-ID aus dem Namen (wird separat gespeichert)
                if equipment_name:
                    equipment_name = _normalize_equipment_name(equipment_name)
                    # Description zum Namen hinzufügen wenn vorhanden
                    if description:
                        equipment_name = f"{equipment_name} - {description}"
                if not equipment_name:
                    equipment_name = energy_id
                if not equipment_name:
                    continue

                qr_path = it.get("qr_path", "")
                sticker_config = it.get("sticker_config", {})
                logger.debug(f"Füge Equipment hinzu: name={equipment_name}, qr_path={qr_path}")
                added = equipment_manager.add_equipment(
                    location, system, equipment_name,
                    energy_id=energy_id,
                    symbol_type=symbol_type,
                    description="",  # Description ist bereits im Namen
                    qr_path=qr_path,
                    sticker_config=sticker_config
                )

                if added:
                    imported += 1
                else:
                    # Equipment mit Name+Energy-ID existiert bereits, aktualisiere Eigenschaften
                    updated = equipment_manager.update_equipment_properties(
                        location, system, equipment_name,
                        symbol_type=symbol_type,
                        description="",  # Description ist bereits im Namen
                        qr_path=qr_path,
                        sticker_config=sticker_config,
                        match_energy_id=energy_id
                    )
                    if updated:
                        imported += 1
            except Exception:
                continue

        if imported > 0:
            self.equipment_service.save()
            if hasattr(self.app, 'equipment_controller'):
                self.app.equipment_controller.refresh_tree()
            if self.status_bar:
                self.status_bar.showMessage(f"{imported} Einträge in Equipment übernommen", 3000)
            msg = self._create_styled_msgbox(
                "Gespeichert",
                f"{imported} Einträge wurden in den Equipment‑Manager übernommen.",
                QMessageBox.Icon.Information
            )
            msg.exec()
        else:
            msg = self._create_styled_msgbox(
                "Hinweis",
                "Keine Einträge übernommen.",
                QMessageBox.Icon.Warning
            )
            msg.exec()
