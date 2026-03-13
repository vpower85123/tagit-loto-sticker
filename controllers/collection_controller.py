"""
Collection Controller
Verwaltet alle Collection-Operationen (Hinzufügen, Entfernen, Sortieren, Vorschau)
"""

import math
import re
import time
import logging
from collections import Counter, OrderedDict
from typing import Optional, Any, TYPE_CHECKING

from PyQt6.QtWidgets import (
    QListWidget, QListWidgetItem, QMenu, QMessageBox, QLabel,
    QDialog, QVBoxLayout, QHBoxLayout, QInputDialog, QSpinBox,
    QDialogButtonBox, QApplication
)
from PyQt6.QtCore import QObject, pyqtSignal, Qt, QTimer, QSize
from PyQt6.QtGui import QAction, QPixmap

from PIL import Image, ImageQt
import qtawesome as qta
from ui.spinboxes import StyledSpinBox

if TYPE_CHECKING:
    from sticker_app_pyqt6 import StickerApp

logger = logging.getLogger(__name__)


class CollectionController(QObject):
    """Controller für Collection-Management"""

    # Signals
    collection_updated = pyqtSignal()

    def __init__(self, parent: "StickerApp"):
        super().__init__(parent)
        self.app = parent

    # ---- helper shortcuts ------------------------------------------------
    @property
    def collection(self):
        return self.app.collection

    @collection.setter
    def collection(self, value):
        self.app.collection = value

    @property
    def collection_list(self) -> QListWidget:
        return self.app.collection_list

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
        return self.app.sticker_config

    @property
    def count_config(self):
        return getattr(self.app, 'count_config', None)

    @property
    def status_bar(self):
        return getattr(self.app, 'status_bar', None)

    def _create_styled_msgbox(self, *args, **kwargs):
        return self.app._create_styled_msgbox(*args, **kwargs)

    # ---- type checks -----------------------------------------------------

    @staticmethod
    def _is_count_multi(item):
        """Prüft ob ein Item ein Count-Multi Sticker ist"""
        if len(item) < 6:
            return False
        marker = item[5]
        if isinstance(marker, dict):
            return marker.get("type") == "count_multi"
        return marker == "count_multi"

    @staticmethod
    def _is_count_single(item):
        """Prüft ob ein Item ein Count-Single Sticker ist"""
        if len(item) < 6:
            return False
        marker = item[5]
        if isinstance(marker, dict):
            return marker.get("type") == "count_single"
        return marker == "count_single"

    # ---- add / remove / duplicate ----------------------------------------

    def add_to_collection(self, auto_add_count: bool = True):
        """Sticker zur Sammlung hinzufügen - nutzt Services"""
        try:
            energy_id = self.app.energy_entry.text().strip()
            equipment = self.app.equipment_entry.text().strip()

            is_welcome_sticker = (energy_id == "WELCOME TO" and equipment == "TAG!T")

            if is_welcome_sticker:
                description = ""
            else:
                description = self.app.description_entry.text().strip() if hasattr(self.app, 'description_entry') else ""
                if not description and getattr(self.app, '_saved_description_locked', False):
                    description = getattr(self.app, '_saved_description', "")

            logger.info(f"add_to_collection: energy_id='{energy_id}', equipment='{equipment}', description='{description}'")

            is_valid, error_msg = self.sticker_service.validate_input(energy_id, equipment)
            if not is_valid:
                msg = self._create_styled_msgbox("Fehler", error_msg, QMessageBox.Icon.Warning)
                msg.exec()
                return

            symbol_name = self.app.symbol_combo.currentText().upper()

            img = self.sticker_service.generate_sticker(
                energy_id=energy_id,
                equipment=equipment,
                symbol_name=symbol_name,
                description=description
            )
            if img is None:
                return

            img_thumbnail = img.copy()
            img_thumbnail.thumbnail((400, 300), Image.Resampling.LANCZOS)

            sticker_exists = any(
                not (self._is_count_single(item) or self._is_count_multi(item)) and
                len(item) > 3 and item[2] == energy_id and item[3] == equipment
                for item in self.collection
            )
            if sticker_exists:
                logger.info(f"Sticker {energy_id} {equipment} bereits in Collection - übersprungen")
                return

            self.collection_service.add_item(
                energy_id=energy_id,
                equipment=equipment,
                symbol_type=symbol_name,
                description=description,
                image=img,
                thumbnail=img_thumbnail
            )

            qr_path = ""
            if hasattr(self.sticker_service.generator, 'cfg'):
                cfg = self.sticker_service.generator.cfg
                if getattr(cfg, 'qr_mode_enabled', False) and getattr(cfg, 'qr_image_path', None):
                    qr_path = cfg.qr_image_path
                    logger.info(f"QR-Code-Pfad aus Generator übernommen: {qr_path}")

            current_group = getattr(self.app, '_current_collection_group', '') or ''
            current_location = getattr(self.app, '_current_collection_location', '') or ''
            current_system = getattr(self.app, '_current_collection_system', '') or ''
            full_info = {
                "text": f"{energy_id} {equipment} {description}".strip(),
                "qr_path": qr_path,
                "group": current_group,
                "location": current_location,
                "system": current_system
            }
            self.collection.append([img_thumbnail, symbol_name, energy_id, equipment, description, full_info, img])

            is_single_mode = getattr(self.app, 'single_loto_radio', None) and self.app.single_loto_radio.isChecked()
            is_multi_mode = getattr(self.app, 'multi_loto_radio', None) and self.app.multi_loto_radio.isChecked()
            is_no_count_mode = getattr(self.app, 'no_count_radio', None) and self.app.no_count_radio.isChecked()

            logger.info(f"LOTO Mode: single={is_single_mode}, multi={is_multi_mode}, no_count={is_no_count_mode}, auto_add_count={auto_add_count}")

            if auto_add_count and not is_no_count_mode:
                if is_single_mode:
                    try:
                        count_detail = f"{energy_id} {equipment} {description}".strip()
                        count_id = f"C_{energy_id}"

                        existing_count_ids_m1 = [item[2] for item in self.collection if self._is_count_single(item) and len(item) > 2]
                        existing_count_ids_m2 = [item[2] for item in self.collection if len(item) > 2 and item[1] == "COUNT_SINGLE"]
                        all_existing = set(existing_count_ids_m1) | set(existing_count_ids_m2)

                        logger.debug(f"COUNT CHECK: count_id={count_id}, existing_m1={existing_count_ids_m1}, existing_m2={existing_count_ids_m2}")

                        if count_id not in all_existing:
                            count_img = self.count_generator.generate(count_detail, 1)
                            count_copies_default = max(1, int(getattr(self.count_config, 'count_print_copies', 1)))
                            self.collection.append([count_img, "COUNT_SINGLE", count_id, "", count_detail, {"type": "count_single", "copies": count_copies_default}, count_img])
                            logger.debug(f"COUNT ADDED: {count_id}, collection size: {len(self.collection)}")
                        else:
                            logger.debug(f"COUNT SKIPPED: {count_id} already exists")
                    except Exception as e:
                        logger.warning(f"Count Sticker konnte nicht generiert werden: {e}")
                        import traceback
                        logger.warning(traceback.format_exc())

                elif is_multi_mode:
                    self._regenerate_multi_count_sticker()

            self._remove_duplicate_count_stickers()
            self.update_collection_list()

        except Exception as e:
            msg = self._create_styled_msgbox("Fehler", f"Fehler beim Hinzufügen:\n{e}", QMessageBox.Icon.Critical)
            msg.exec()

    def _remove_duplicate_count_stickers(self):
        """Entfernt doppelte Count-Sticker aus der Collection"""
        seen_count_ids = set()
        items_to_remove = []

        for i, item in enumerate(self.collection):
            if len(item) > 2 and (self._is_count_single(item) or item[1] == "COUNT_SINGLE"):
                count_id = item[2]
                if count_id in seen_count_ids:
                    items_to_remove.append(i)
                    logger.debug(f"REMOVING DUPLICATE COUNT: {count_id} at index {i}")
                else:
                    seen_count_ids.add(count_id)

        for i in reversed(items_to_remove):
            self.collection.pop(i)

        if items_to_remove:
            logger.debug(f"REMOVED {len(items_to_remove)} DUPLICATE COUNT STICKERS")

    def _add_to_collection_with_thumbnail(self, img, symbol_type_name, energy_id, equipment_name, description, full_info):
        """Helper: Füge Sticker zur Collection mit Thumbnail hinzu"""
        img_thumbnail = img.copy()
        img_thumbnail.thumbnail((400, 300), Image.Resampling.LANCZOS)
        self.collection.append([img_thumbnail, symbol_type_name, energy_id, equipment_name, description, full_info, img])

    def _duplicate_collection_item(self, row):
        """Dupliziere ein Collection Item"""
        if row < 0 or row >= len(self.collection):
            return

        item = self.collection[row]
        if not item or len(item) < 5:
            return

        symbol_type = item[1] if len(item) > 1 else "ELECTRICAL"
        energy_id = item[2] if len(item) > 2 else ""
        equipment_name = item[3] if len(item) > 3 else ""
        description = item[4] if len(item) > 4 else ""
        full_info = item[5] if len(item) > 5 else ""

        try:
            img = self.sticker_service.generate_sticker(
                energy_id=energy_id,
                equipment=equipment_name,
                symbol_name=symbol_type,
                description=description
            )

            if img is None:
                msg = self._create_styled_msgbox("Fehler", "Sticker konnte nicht generiert werden", QMessageBox.Icon.Warning)
                msg.exec()
                return

            img_thumbnail = img.copy()
            img_thumbnail.thumbnail((400, 300), Image.Resampling.LANCZOS)

            self.collection_service.add_item(
                energy_id=energy_id,
                equipment=equipment_name,
                symbol_type=symbol_type,
                description=description,
                image=img,
                thumbnail=img_thumbnail
            )

            self.collection.append([img_thumbnail, symbol_type, energy_id, equipment_name, description, full_info, img])
            self.update_collection_list()
            msg = self._create_styled_msgbox("Erfolg", "Sticker zur Sammlung hinzugefügt")
            msg.exec()

        except Exception as e:
            logger.error(f"Fehler beim Duplizieren: {e}")
            msg = self._create_styled_msgbox("Fehler", f"Fehler beim Duplizieren: {e}", QMessageBox.Icon.Warning)
            msg.exec()

    def _remove_collection_item(self, row):
        """Entferne ein Collection Item"""
        if row < 0 or row >= len(self.collection):
            return

        item = self.collection[row]
        if not item or len(item) < 3:
            return

        energy_id = item[2] if len(item) > 2 else "Unknown"
        equipment_name = item[3] if len(item) > 3 else "Unknown"

        reply = QMessageBox.question(
            self.app, "Bestätigung",
            f"Sticker '{energy_id} / {equipment_name}' wirklich löschen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.collection_service.remove_item(row)
        if row < len(self.collection):
            del self.collection[row]

        logger.info(f"Sticker gelöscht. Collection hat jetzt {len(self.collection)} Items")
        self.update_collection_list()

        logger.info("Aktualisiere Count-Sticker nach Löschung...")
        self._regenerate_multi_count_sticker()

    def _remove_multiple_collection_items(self, rows: list):
        """Entferne mehrere Collection Items"""
        if not rows:
            return

        reply = QMessageBox.question(
            self.app, "Bestätigung",
            f"{len(rows)} Sticker wirklich löschen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        rows_sorted = sorted(rows, reverse=True)
        for row in rows_sorted:
            if row < 0 or row >= len(self.collection):
                continue
            try:
                self.collection_service.remove_item(row)
            except Exception:
                pass
            if row < len(self.collection):
                del self.collection[row]

        logger.info(f"{len(rows)} Sticker gelöscht. Collection hat jetzt {len(self.collection)} Items")
        self.update_collection_list()

        logger.info("Aktualisiere Count-Sticker nach Mehrfach-Löschung...")
        self._regenerate_multi_count_sticker()
        logger.info("Count-Sticker aktualisiert")

        msg = self._create_styled_msgbox("Erfolg", "Sticker entfernt")
        msg.exec()

    def clear_collection(self):
        """Sammlung leeren"""
        if self.collection_service.is_empty():
            msg = self._create_styled_msgbox("Info", "Sammlung ist bereits leer", QMessageBox.Icon.Information)
            msg.exec()
            return

        count = self.collection_service.get_count()
        msg_box = self._create_styled_msgbox(
            "Bestätigung",
            f"Alle {count} Sticker löschen?",
            QMessageBox.Icon.Question,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        reply = msg_box.exec()

        if reply == QMessageBox.StandardButton.Yes:
            self.collection_service.clear()
            self.collection.clear()
            self.app.collection_export_sources.clear()
            self.update_collection_list()
            if self.status_bar:
                self.status_bar.showMessage("Sammlung geleert", 2000)

    def register_collection_source(self, source: str):
        if source:
            self.app.collection_export_sources.add(str(source).strip())

    def regenerate_all_stickers(self):
        """Alle Sticker in der Sammlung mit aktuellen Einstellungen neu generieren"""
        if not self.collection:
            msg = self._create_styled_msgbox("Info", "Keine Sticker zum Regenerieren.")
            msg.exec()
            return

        msg = self._create_styled_msgbox(
            "Bestätigung",
            f"Alle {len(self.collection)} Sticker mit aktuellen Einstellungen (inkl. QR-Code) neu generieren?",
            QMessageBox.Icon.Question,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if msg.exec() != QMessageBox.StandardButton.Yes:
            return

        progress_bar = None
        if hasattr(self.app, 'magic_menu'):
            progress_bar = self.app.magic_menu.progress_bar
            progress_bar.setRange(0, len(self.collection))
            progress_bar.setValue(0)
            progress_bar.setVisible(True)

        regenerated_count = 0
        errors = []

        try:
            for i, item in enumerate(self.collection):
                try:
                    if len(item) < 5:
                        continue

                    symbol_type = item[1] if len(item) > 1 else "ELECTRICAL"
                    energy_id = item[2] if len(item) > 2 else ""
                    equipment = item[3] if len(item) > 3 else ""
                    description = item[4] if len(item) > 4 else ""

                    if len(item) >= 6 and (item[5] == 'count_single' or item[5] == 'count_multi'):
                        if progress_bar:
                            progress_bar.setValue(i + 1)
                        continue

                    new_img = self.sticker_service.generate_sticker(
                        energy_id=energy_id,
                        equipment=equipment,
                        symbol_name=symbol_type,
                        description=description
                    )

                    if new_img:
                        new_thumbnail = new_img.copy()
                        new_thumbnail.thumbnail((400, 300), Image.Resampling.LANCZOS)
                        item[0] = new_thumbnail
                        if len(item) > 6:
                            item[6] = new_img
                        self.collection_service.update_item_image(i, new_img, new_thumbnail)
                        regenerated_count += 1

                except Exception as e:
                    errors.append(f"Sticker {i+1}: {str(e)}")
                    logger.error(f"Error regenerating sticker {i}: {e}")

                if progress_bar:
                    progress_bar.setValue(i + 1)
                QApplication.processEvents()

            self.update_collection_list()

        finally:
            if progress_bar:
                progress_bar.setVisible(False)

        if errors:
            error_msg = f"{regenerated_count} Sticker regeneriert.\n\nFehler:\n" + "\n".join(errors[:5])
            if len(errors) > 5:
                error_msg += f"\n... und {len(errors) - 5} weitere Fehler"
            msg = self._create_styled_msgbox("Abgeschlossen", error_msg, QMessageBox.Icon.Warning)
        else:
            msg = self._create_styled_msgbox("Erfolg", f"{regenerated_count} Sticker erfolgreich regeneriert!")
        msg.exec()

    # ---- update UI list --------------------------------------------------

    def update_collection_list(self, skip_sort: bool = False):
        """Sammlungsliste aktualisieren"""
        current_row = self.collection_list.currentRow()
        self.collection_list.clear()

        manual_mode = getattr(self.app, "_manual_sort_mode", None)
        effective_skip_sort = skip_sort or manual_mode == "energy_id"
        count_copies = max(1, int(getattr(self.count_config, 'count_print_copies', 1)))

        if effective_skip_sort:
            multi_count = 0
            skipped_items = 0
            for idx, item in enumerate(self.collection, start=1):
                if len(item) < 4:
                    logger.warning(f"Item {idx} übersprungen (len={len(item)})")
                    skipped_items += 1
                    continue

                symbol_type = item[1] if len(item) > 1 else "?"
                energy_id = item[2] if len(item) > 2 else f"IDX{idx}"
                equipment = item[3] if len(item) > 3 else ""
                description = item[4] if len(item) > 4 else ""

                is_count_single = self._is_count_single(item)
                is_count_multi = self._is_count_multi(item)

                if is_count_single:
                    marker = item[5] if len(item) > 5 else {}
                    copies = marker.get("copies", 1) if isinstance(marker, dict) else 1
                    text = f"{idx:02d} | C | {energy_id} | 1 LOTOPOINT | x{copies}"
                elif is_count_multi:
                    marker = item[5] if len(item) > 5 else {}
                    copies = 1
                    count_group = ""
                    if isinstance(marker, dict):
                        copies = marker.get("copies", 1)
                        count_group = marker.get("group", "")
                    regular_count = sum(
                        1 for it in self.collection
                        if not (self._is_count_single(it) or self._is_count_multi(it))
                        and (isinstance(it[5], dict) and it[5].get("group", "") == count_group if len(it) > 5 else count_group == "")
                    )
                    group_label = count_group if count_group else "TOTAL"
                    text = f"{idx:02d} | C | {group_label} | {regular_count} LOTOPOINTS | x{copies}"
                else:
                    multi_count += 1
                    base = getattr(symbol_type, 'name', str(symbol_type))
                    symbol_short = (base[:1].upper() or "?")
                    if description:
                        text = f"{idx:02d} | {symbol_short} | {energy_id} | {equipment} | {description} | #{multi_count}"
                    else:
                        text = f"{idx:02d} | {symbol_short} | {energy_id} | {equipment} | #{multi_count}"

                self.collection_list.addItem(text)

            if skipped_items > 0:
                logger.debug(f"TOTAL: {skipped_items} Items übersprungen, {self.collection_list.count()} Items angezeigt")

            if current_row >= 0 and current_row < self.collection_list.count():
                self.collection_list.setCurrentRow(current_row)
            return

        # ---- full sort path ----

        def _natural_key(text: str):
            parts = re.split(r"(\d+)", text.upper())
            key = []
            for part in parts:
                if part.isdigit():
                    key.append(int(part))
                else:
                    key.append(part)
            return tuple(key)

        def _normalize_equipment(equipment: str) -> str:
            if not equipment:
                return ""
            normalized = re.sub(r"\s*-\s*", "-", equipment)
            normalized = re.sub(r"\s+", "", normalized)
            normalized = re.sub(r"\.+", ".", normalized)
            return normalized.strip(".")

        def _split_segments(equipment: str) -> list:
            normalized = _normalize_equipment(equipment)
            return [seg for seg in normalized.split(".") if seg]

        def _strip_suffix(segment: str) -> str:
            return re.sub(r"[_-]?\d+$", "", segment)

        def _find_base_segment(segments: list) -> tuple:
            for idx, segment in enumerate(segments):
                if re.search(r"[A-Z]+-\d+", segment, re.IGNORECASE):
                    return idx, segment
            return None, ""

        def _extract_group_key(equipment: str, segment_counts: Counter) -> str:
            if not equipment:
                return ""
            match = re.search(r"SC[_-]?(\d+)\.?(\d*)", equipment, re.IGNORECASE)
            if match:
                sc_num = match.group(1)
                sub_num = match.group(2) if match.group(2) else "00"
                return f"SC_{sc_num}.{sub_num}"

            segments = _split_segments(equipment)
            base_index, base_segment = _find_base_segment(segments)

            if base_index is not None:
                group_parts = [base_segment]
                for i in range(base_index + 1, len(segments)):
                    candidate = _strip_suffix(segments[i])
                    if candidate and segment_counts.get(candidate, 0) > 1:
                        group_parts.append(candidate)
                return ".".join(group_parts)

            prefix = re.sub(r"[._-]\d+\.?$", "", equipment)
            while prefix != equipment:
                equipment = prefix
                prefix = re.sub(r"[._-]\d+\.?$", "", equipment)
            return prefix

        def _energy_id_sort_key(energy_id: str):
            if not energy_id:
                return (float('inf'), "")
            return _natural_key(energy_id)

        def _equipment_sort_key(item):
            equipment = item[3] if len(item) > 3 else ""
            energy_id = item[2] if len(item) > 2 else ""
            full_info = item[5] if len(item) > 5 and isinstance(item[5], dict) else {}
            group = full_info.get("group", "")
            return (_natural_key(group), _energy_id_sort_key(energy_id), _natural_key(equipment))

        regular_items = [it for it in self.collection if not (self._is_count_single(it) or self._is_count_multi(it))]
        count_singles = [it for it in self.collection if self._is_count_single(it)]
        count_multis = [it for it in self.collection if self._is_count_multi(it)]

        if not skip_sort:
            regular_items.sort(key=_equipment_sort_key)
            count_singles.sort(key=lambda it: _energy_id_sort_key(
                it[2][2:] if len(it) > 2 and it[2].startswith("C_") else (it[2] if len(it) > 2 else "")
            ))
            count_multis.sort(key=lambda it: _natural_key(
                it[5].get("group", "") if len(it) > 5 and isinstance(it[5], dict) else ""
            ))
            self.collection = regular_items + count_singles + count_multis

        multi_count = 0
        skipped_items = 0

        for idx, item in enumerate(self.collection, start=1):
            if len(item) >= 4:
                symbol_type = item[1] if len(item) > 1 else "?"
                energy_id = item[2] if len(item) > 2 else f"IDX{idx}"
                equipment = item[3] if len(item) > 3 else ""
                description = item[4] if len(item) > 4 else ""

                is_count_single = self._is_count_single(item) or (str(symbol_type) == "COUNT_SINGLE")
                is_count_multi = self._is_count_multi(item) or (str(symbol_type) == "COUNT_MULTI")

                if is_count_single:
                    marker = item[5] if len(item) > 5 else {}
                    copies = marker.get("copies", 1) if isinstance(marker, dict) else 1
                    text = f"{idx:02d} | C | {energy_id} | 1 LOTOPOINT | x{copies}"
                elif is_count_multi:
                    count_group = ""
                    marker = item[5] if len(item) > 5 else {}
                    copies = 1
                    if isinstance(marker, dict):
                        count_group = marker.get("group", "")
                        copies = marker.get("copies", 1)
                    regular_count = sum(
                        1 for it in self.collection
                        if not (self._is_count_single(it) or self._is_count_multi(it))
                        and (isinstance(it[5], dict) and it[5].get("group", "") == count_group if len(it) > 5 else count_group == "")
                    )
                    group_label = count_group if count_group else "TOTAL"
                    text = f"{idx:02d} | C | {group_label} | {regular_count} LOTOPOINTS | x{copies}"
                else:
                    multi_count += 1
                    base = getattr(symbol_type, 'name', str(symbol_type))
                    symbol_short = (base[:1].upper() or "?")
                    if description:
                        text = f"{idx:02d} | {symbol_short} | {energy_id} | {equipment} | {description} | #{multi_count}"
                    else:
                        text = f"{idx:02d} | {symbol_short} | {energy_id} | {equipment} | #{multi_count}"

                self.collection_list.addItem(text)
            else:
                logger.warning(f"Item {idx} übersprungen (sortiert, len={len(item)})")
                skipped_items += 1

        if skipped_items > 0:
            logger.debug(f"TOTAL (sortiert): {skipped_items} Items übersprungen, {self.collection_list.count()} Items angezeigt")

        if current_row >= 0 and current_row < self.collection_list.count():
            self.collection_list.setCurrentRow(current_row)

    # ---- selection & scroll handlers -------------------------------------

    def _on_collection_item_selected_trigger(self):
        """Trigger für Collection Item Selection - startet Debounce Timer"""
        current_row = self.collection_list.currentRow()
        self.app._pending_collection_preview_row = current_row

        if getattr(self.app, "_is_collection_scrolling", False):
            return

        delay = getattr(self.app, "_collection_preview_delay_ms", 150)
        self.app.collection_selection_timer.stop()
        self.app.collection_selection_timer.start(delay)

    def _on_collection_item_selected_debounced(self):
        """Debounced Collection Item Selection"""
        self._on_collection_item_selected()

    def _on_collection_scroll_value_changed(self, _value):
        """Unterdrücke Vorschauupdates während des Scrollens."""
        try:
            self.app._is_collection_scrolling = True
            if hasattr(self.app, "collection_selection_timer"):
                self.app.collection_selection_timer.stop()
            if hasattr(self.app, "collection_scroll_cooldown_timer"):
                self.app.collection_scroll_cooldown_timer.start(250)
        except Exception as exc:
            logger.debug(f"Scroll handler error: {exc}")

    def _on_collection_scroll_finished(self):
        """Reaktiviere Vorschauupdates nachdem das Scrollen gestoppt hat."""
        self.app._is_collection_scrolling = False
        row = self.app._pending_collection_preview_row
        self.app._pending_collection_preview_row = None

        list_widget = getattr(self.app, "collection_list", None)
        if list_widget is None:
            return

        count = list_widget.count()

        if row is None or row < 0 or row >= count:
            row = list_widget.currentRow()

        if row is not None and row >= 0 and row < count:
            if row != list_widget.currentRow():
                list_widget.setCurrentRow(row)
                return

            delay = getattr(self.app, "_collection_preview_delay_ms", 150)
            if hasattr(self.app, "collection_selection_timer"):
                self.app.collection_selection_timer.start(delay)

    def _clear_collection_preview_cache(self, drop_base: bool = False):
        """Leere gecachte Pixmaps für Sammlungselemente."""
        cache_index = 7
        for item in getattr(self.app, "collection", []):
            if len(item) <= cache_index:
                continue
            cache_entry = item[cache_index]

            if isinstance(cache_entry, dict):
                if drop_base:
                    cache_entry["base"] = None
                cache_entry["scaled"] = {}
            elif cache_entry is not None:
                if drop_base:
                    item[cache_index] = None
                else:
                    item[cache_index] = {"base": cache_entry, "scaled": {}}

    def _on_collection_item_selected(self):
        """Handler: Wenn ein Sticker in der Collection angewählt wird, zeige ihn in der Vorschau"""
        start_time = time.time()

        try:
            current_row = self.collection_list.currentRow()
            if current_row < 0 or current_row >= len(self.collection):
                logger.debug(f"Collection selection: invalid row {current_row}")
                return

            logger.debug(f"Collection item selected: row {current_row}")

            item = self.collection[current_row]
            if not item or len(item) < 1:
                logger.debug("Collection item is empty")
                return

            if hasattr(self.app, 'preview_label') and hasattr(self.app.preview_label, 'set_mask_pixmap'):
                self.app.preview_label.set_mask_pixmap(None)

            use_thumbnail = len(item) > 6 and item[6] is not None
            img = item[6] if use_thumbnail else item[0]

            if not img:
                return

            if len(item) >= 5:
                symbol_type = item[1] if len(item) > 1 else ""
                energy_id = item[2] if len(item) > 2 else ""
                equipment_name = item[3] if len(item) > 3 else ""
                description = item[4] if len(item) > 4 else ""

                if symbol_type and not str(symbol_type).startswith("COUNT"):
                    if hasattr(self.app, 'energy_entry'):
                        self.app.energy_entry.setText(energy_id or "")
                    if hasattr(self.app, 'equipment_entry'):
                        self.app.equipment_entry.setText(equipment_name or "")
                    if hasattr(self.app, 'description_entry'):
                        self.app.description_entry.setText(description or "")
                    if hasattr(self.app, 'symbol_combo'):
                        try:
                            symbol_display = str(symbol_type).capitalize()
                            index = self.app.symbol_combo.findText(symbol_display)
                            if index >= 0:
                                self.app.symbol_combo.setCurrentIndex(index)
                        except Exception as e:
                            logger.debug(f"Konnte Symbol-Typ nicht setzen: {e}")

            convert_start = time.time()

            display_img = item[0]

            cache_index = 7
            cache_container = None
            if len(item) > cache_index and item[cache_index] is not None:
                existing_cache = item[cache_index]
                if isinstance(existing_cache, dict):
                    cache_container = existing_cache
                else:
                    cache_container = {"base": existing_cache, "scaled": {}}
                    item[cache_index] = cache_container

            base_was_cached = bool(cache_container and cache_container.get("base") is not None)

            if not base_was_cached:
                if display_img.mode != 'RGBA':
                    display_img_rgba = display_img.convert('RGBA')
                else:
                    display_img_rgba = display_img

                qimage = ImageQt.ImageQt(display_img_rgba)
                base_pixmap = QPixmap.fromImage(qimage)
                logger.debug(f"[PERF] PIL->QPixmap Konvertierung: {time.time() - convert_start:.3f}s, size={display_img_rgba.size}")

                if cache_container is None:
                    cache_container = {"base": base_pixmap, "scaled": {}}
                else:
                    cache_container["base"] = base_pixmap
                    cache_container.setdefault("scaled", {})

                if len(item) <= cache_index:
                    while len(item) <= cache_index:
                        item.append(None)
                item[cache_index] = cache_container

            if cache_container is None or not isinstance(cache_container, dict):
                cache_container = {"base": cache_container if isinstance(cache_container, QPixmap) else None, "scaled": {}}
                if len(item) <= cache_index:
                    while len(item) <= cache_index:
                        item.append(None)
                item[cache_index] = cache_container

            base_pixmap = cache_container.get("base")
            if base_pixmap is None:
                logger.warning("[PERF] Basis-Pixmap konnte nicht erzeugt werden.")
                return
            if base_was_cached:
                logger.debug(f"[PERF] QPixmap Basis aus Cache: {time.time() - convert_start:.3f}s")

            try:
                scale = float(self.sticker_config.preview_scale or 1.0)
            except Exception:
                scale = 1.0

            if not math.isfinite(scale) or scale <= 0:
                scale = 1.0

            scale_start = time.time()
            if not isinstance(cache_container, dict):
                logger.warning("[PERF] Ungültiger Cache-Typ, breche Vorschauupdate ab.")
                return

            cache_container.setdefault("scaled", {})
            scale_key = f"{scale:.2f}"
            scaled_pixmap = cache_container["scaled"].get(scale_key)

            if scaled_pixmap is None:
                scaled_pixmap = base_pixmap.scaled(
                    int(400 * scale), int(300 * scale),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                cache_container["scaled"][scale_key] = scaled_pixmap
                logger.debug(f"[PERF] Pixmap Skalierung neu: {time.time() - scale_start:.3f}s")
            else:
                logger.debug(f"[PERF] Pixmap Skalierung aus Cache: {time.time() - scale_start:.3f}s")

            mask_pixmap = None
            is_count = isinstance(symbol_type, str) and symbol_type.startswith("COUNT")

            if is_count:
                try:
                    marker = item[5] if len(item) > 5 else None
                    if isinstance(marker, dict):
                        detail_str = marker.get("details", "")
                    else:
                        detail_str = description

                    count = 1
                    if symbol_type == "COUNT_MULTI":
                        if detail_str:
                            items = [it for it in detail_str.split(',') if it.strip()]
                            count = len(items)
                    elif symbol_type == "COUNT_SINGLE":
                        detail_str = f"{description}"

                    new_img = self.count_generator.generate(detail_str, count)
                    if new_img:
                        if new_img.mode != 'RGBA':
                            new_img = new_img.convert('RGBA')
                        qim = ImageQt.ImageQt(new_img)
                        new_pixmap = QPixmap.fromImage(qim)

                        try:
                            scale = float(self.sticker_config.preview_scale or 1.0)
                        except Exception:
                            scale = 1.0

                        scaled_new_pixmap = new_pixmap.scaled(
                            int(400 * scale), int(300 * scale),
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation
                        )

                        if hasattr(self.app, 'preview_label') and self.app.preview_label is not None:
                            self.app.preview_label.setPixmap(scaled_new_pixmap)
                            mask_image = self.count_generator.get_last_text_mask()
                            if mask_image and hasattr(self.app.preview_label, 'set_mask_pixmap'):
                                mask_rgba = Image.new("RGBA", mask_image.size, (255, 255, 255, 0))
                                mask_rgba.putalpha(mask_image)
                                qim_mask = ImageQt.ImageQt(mask_rgba)
                                mask_pm = QPixmap.fromImage(qim_mask)
                                mask_pixmap = mask_pm.scaled(
                                    scaled_new_pixmap.width(), scaled_new_pixmap.height(),
                                    Qt.AspectRatioMode.IgnoreAspectRatio,
                                    Qt.TransformationMode.SmoothTransformation
                                )
                                self.app.preview_label.set_mask_pixmap(mask_pixmap)
                    return
                except Exception as e:
                    logger.warning(f"Konnte Count-Sticker Vorschau nicht generieren: {e}")

            if hasattr(self.app, 'preview_label') and self.app.preview_label is not None:
                logger.debug(f"Setting preview pixmap, size: {scaled_pixmap.width()}x{scaled_pixmap.height()}")
                self.app.preview_label.setPixmap(scaled_pixmap)
                self.app.preview_label.update()
                logger.debug("Preview label updated successfully")
            else:
                logger.warning("preview_label not available!")

            if hasattr(self.app.preview_label, 'set_mask_pixmap'):
                self.app.preview_label.set_mask_pixmap(mask_pixmap)

            logger.info(f"[PERF] Collection item selected total: {time.time() - start_time:.3f}s, row={current_row}")
        except Exception as e:
            logger.error(f"Error displaying collection item: {e}", exc_info=True)

    # ---- context menu ----------------------------------------------------

    def _edit_count_sticker_copies(self, row: int) -> None:
        """Bearbeite Kopienanzahl für einen Count-Sticker"""
        try:
            if row < 0 or row >= len(self.collection):
                return

            coll_item = self.collection[row]
            if not coll_item or len(coll_item) < 6:
                return

            full_info = coll_item[5]
            if not isinstance(full_info, dict):
                return

            current_copies = full_info.get("copies", 1)

            dialog = QDialog(self.app)
            dialog.setWindowTitle("Kopien für Export")
            dialog.setFixedWidth(300)
            dialog.setStyleSheet("""
                QDialog { background-color: #ffffff; }
                QLabel { color: #000000; }
                QPushButton {
                    border: 1px solid #cccccc; border-radius: 4px;
                    padding: 4px 12px; background-color: #f0f0f0; color: #000000;
                }
                QPushButton:hover { background-color: #e1e1e1; }
                QPushButton:pressed { background-color: #d0d0d0; }
            """)

            layout = QVBoxLayout()
            label = QLabel("Anzahl Kopien zum Exportieren:")
            layout.addWidget(label)

            # Nutze zentrale StyledSpinBox mit stabilen Custom-Pfeilen
            spinbox = StyledSpinBox()
            spinbox.setMinimum(1)
            spinbox.setMaximum(999)
            spinbox.setValue(current_copies)
            spinbox.setFocus()
            spinbox.selectAll()
            layout.addWidget(spinbox)

            button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)
            layout.addWidget(button_box)

            dialog.setLayout(layout)

            if dialog.exec() == QDialog.DialogCode.Accepted:
                new_copies = spinbox.value()
                full_info["copies"] = new_copies
                self.update_collection_list()
                logger.info(f"Updated count sticker copies: row={row}, new_copies={new_copies}")

        except Exception as e:
            logger.error(f"Error editing count sticker copies: {e}", exc_info=True)

    def _show_collection_context_menu(self, pos):
        """Zeige Kontextmenü für Collection Items beim Rechtsklick"""
        item = self.collection_list.itemAt(pos)
        if not item:
            return

        selected_items = self.collection_list.selectedItems()
        selected_rows = sorted([self.collection_list.row(it) for it in selected_items], reverse=True)

        clicked_row = self.collection_list.row(item)
        if clicked_row not in selected_rows:
            self.collection_list.setCurrentRow(clicked_row)
            selected_rows = [clicked_row]

        menu = QMenu(self.app)
        is_multi_select = len(selected_rows) > 1

        if not is_multi_select:
            current_row = selected_rows[0]

            if current_row >= 0 and current_row < len(self.collection):
                coll_item = self.collection[current_row]
                is_cs = self._is_count_single(coll_item)
                is_cm = self._is_count_multi(coll_item)

                if is_cs or is_cm:
                    copies_action = QAction("Kopien für Export ändern…", menu)
                    menu.addAction(copies_action)
                    copies_action.triggered.connect(lambda: self._edit_count_sticker_copies(current_row))
                    menu.addSeparator()

            add_action = QAction("Zur Sammlung hinzufügen (Duplizieren)", menu)
            menu.addAction(add_action)
            add_action.triggered.connect(lambda: self._duplicate_collection_item(current_row))

            equip_action = QAction("Zum Equipment-Manager hinzufügen…", menu)
            menu.addAction(equip_action)
            equip_action.triggered.connect(lambda: self._add_collection_item_to_equipment_manager(current_row))

            menu.addSeparator()

            remove_action = QAction("Aus Sammlung entfernen", menu)
            menu.addAction(remove_action)
            remove_action.triggered.connect(lambda: self._remove_collection_item(current_row))
        else:
            remove_action = QAction(f"{len(selected_rows)} Sticker aus Sammlung entfernen", menu)
            remove_action.setIcon(qta.icon('ph.trash', color='#ef4444'))
            menu.addAction(remove_action)
            remove_action.triggered.connect(lambda: self._remove_multiple_collection_items(selected_rows))

        global_pos = self.collection_list.mapToGlobal(pos)
        menu.exec(global_pos)

    def _add_collection_item_to_equipment_manager(self, row: int) -> None:
        """Übernimmt den ausgewählten Sticker als Equipment-Eintrag"""
        from dialogs.equipment_dialog import EquipmentSelectionDialog
        from ui.theme import Theme
        from core.models import SymbolType

        try:
            if row < 0 or row >= len(self.collection):
                return

            item = self.collection[row]
            if not item or len(item) < 4:
                return

            symbol_type = item[1] if len(item) > 1 else ""
            energy_id = (item[2] if len(item) > 2 else "") or ""
            equipment_name = (item[3] if len(item) > 3 else "") or ""

            qr_path = ""
            logger.info(f"DEBUG: Item length={len(item)}, full item structure: {[type(x).__name__ for x in item]}")
            if len(item) > 5:
                full_info = item[5]
                logger.info(f"full_info type={type(full_info)}, value={full_info}")
                if isinstance(full_info, dict):
                    qr_path = full_info.get("qr_path", "")
                    logger.info(f"Extracted qr_path from dict={qr_path}")
                else:
                    logger.warning(f"full_info is not a dict, it's {type(full_info)}, value={full_info}")
            else:
                logger.warning(f"Item too short, len={len(item)}, expected at least 6")

            is_count_single = (len(item) >= 6 and item[5] == "count_single") or (str(symbol_type) == "COUNT_SINGLE")
            is_count_multi = (len(item) >= 6 and item[5] == "count_multi") or (str(symbol_type) == "COUNT_MULTI")
            if is_count_single or is_count_multi:
                msg = self._create_styled_msgbox("Info", "COUNT-Sticker können nicht in den Equipment-Manager übernommen werden.")
                msg.exec()
                return

            equipment_name = str(equipment_name).strip()
            energy_id = str(energy_id).strip()
            symbol_type_str = str(getattr(symbol_type, 'name', symbol_type)).strip().upper()

            if not equipment_name:
                equipment_name, ok = QInputDialog.getText(self.app, "Equipment", "Name für das neue Betriebsmittel:")
                if not ok or not equipment_name.strip():
                    return
                equipment_name = equipment_name.strip()

            dialog = EquipmentSelectionDialog(self.app, self.app.equipment_manager, getattr(self.app, 'theme', Theme.LIGHT))
            dialog.setWindowTitle("Ziel-System auswählen")
            if dialog.exec() != QDialog.DialogCode.Accepted or not dialog.selected_data:
                return

            sel = dialog.selected_data
            sel_type = sel.get('type')
            if sel_type == 'system':
                location = sel.get('location', '')
                system_name = sel.get('system_name', '')
            elif sel_type == 'equipment':
                location = sel.get('location', '')
                system_name = sel.get('system_name', '')
            else:
                msg = self._create_styled_msgbox("Fehler", "Bitte ein System (oder ein Equipment innerhalb eines Systems) auswählen.", QMessageBox.Icon.Warning)
                msg.exec()
                return

            if not location or not system_name:
                msg = self._create_styled_msgbox("Fehler", "Konnte Standort/System aus der Auswahl nicht ermitteln.", QMessageBox.Icon.Warning)
                msg.exec()
                return

            exists = False
            try:
                for eq in self.app.equipment_manager.get_equipment(location, system_name):
                    if eq.get('name', '') == equipment_name:
                        exists = True
                        break
            except Exception:
                exists = False

            if exists:
                ok = self.app.equipment_manager.update_equipment_properties(
                    location, system_name, equipment_name,
                    energy_id=energy_id if energy_id else None,
                    symbol_type=symbol_type_str if symbol_type_str else None,
                    qr_path=qr_path if qr_path else None
                )
                if not ok:
                    msg = self._create_styled_msgbox("Fehler", "Equipment konnte nicht aktualisiert werden.", QMessageBox.Icon.Warning)
                    msg.exec()
                    return
                success_msg = "Equipment aktualisiert (zum Speichern bitte im Equipment-Tab auf 'Speichern' klicken)."
            else:
                ok = self.app.equipment_manager.add_equipment(
                    location, system_name, equipment_name,
                    energy_id=energy_id,
                    symbol_type=symbol_type_str,
                    qr_path=qr_path
                )
                if not ok:
                    msg = self._create_styled_msgbox("Fehler", "Equipment konnte nicht hinzugefügt werden.", QMessageBox.Icon.Warning)
                    msg.exec()
                    return
                success_msg = "Equipment hinzugefügt (zum Speichern bitte im Equipment-Tab auf 'Speichern' klicken)."

            if hasattr(self.app, 'equipment_controller') and self.app.equipment_controller:
                self.app.equipment_controller.refresh_tree()

            msgbox = self._create_styled_msgbox("Erfolg", success_msg)
            msgbox.exec()

        except Exception as e:
            logger.exception("Fehler beim Übernehmen in Equipment")
            msg = self._create_styled_msgbox("Fehler", f"Fehler beim Übernehmen: {e}", QMessageBox.Icon.Warning)
            msg.exec()

    # ---- sorting & movement ----------------------------------------------

    def sort_collection_by_energy_id(self):
        """Sortiert die Sammlung nach Energie-ID (E1, E2, E3, ...)"""
        if not self.collection:
            msg = self._create_styled_msgbox("Hinweis", "Keine Sticker in der Sammlung!", QMessageBox.Icon.Warning)
            msg.exec()
            return

        regular = []
        counts = []
        for item in self.collection:
            if self._is_count_single(item) or self._is_count_multi(item):
                counts.append(item)
            else:
                regular.append(item)

        def get_energy_key(item):
            if len(item) < 3:
                return (float("inf"), "")
            eid = str(item[2]).upper()
            m = re.search(r"E(\d+)", eid)
            return (int(m.group(1)), eid) if m else (float("inf"), eid)

        regular.sort(key=get_energy_key)
        self.collection = regular + counts
        self.app._manual_sort_mode = "energy_id"

        has_count_sticker = any(self._is_count_multi(it) for it in counts)
        if has_count_sticker:
            self._regenerate_multi_count_sticker()
        else:
            self.update_collection_list(skip_sort=True)

        if self.status_bar:
            self.status_bar.showMessage(f"Nach Energie-ID sortiert ({len(regular)} Sticker)", 3000)

    def _regenerate_multi_count_sticker(self):
        """Regeneriert Multi-LOTO Count-Sticker nach Änderungen"""
        try:
            current_row = self.collection_list.currentRow()
            was_count_selected = False
            if current_row >= 0 and current_row < len(self.collection):
                item = self.collection[current_row]
                was_count_selected = self._is_count_multi(item)

            old_copies_per_group = {}
            for item in self.collection:
                if self._is_count_multi(item) and len(item) > 5 and isinstance(item[5], dict):
                    grp = item[5].get("group", "")
                    old_copies_per_group[grp] = item[5].get("copies", 1)

            i = len(self.collection) - 1
            while i >= 0:
                item = self.collection[i]
                if self._is_count_multi(item):
                    self.collection.pop(i)
                    logger.info(f"_regenerate: Entferne alten Count-Multi Sticker an Index {i}")
                i -= 1

            groups = OrderedDict()
            for item in self.collection:
                if self._is_count_single(item) or self._is_count_multi(item):
                    continue
                if len(item) < 5:
                    continue
                full_info = item[5] if len(item) > 5 else {}
                group_name = ""
                if isinstance(full_info, dict):
                    group_name = full_info.get("group", "")
                if group_name not in groups:
                    groups[group_name] = []
                groups[group_name].append(item)

            logger.info(f"_regenerate: {len(groups)} Gruppe(n) gefunden: {list(groups.keys())}")

            for group_name, group_items in groups.items():
                count = len(group_items)
                if count == 0:
                    continue

                details = []
                for item in group_items:
                    item_energy = item[2]
                    item_equipment = item[3]
                    item_description = item[4]

                    if isinstance(item_description, dict):
                        item_description = item_description.get("text", "")

                    if not item_description and len(item) > 5:
                        fi = item[5]
                        if isinstance(fi, dict) and "text" in fi:
                            full_text = fi.get("text", "")
                            parts = full_text.split()
                            if len(parts) > 2:
                                item_description = " ".join(parts[2:])

                    if item_energy.startswith("C_"):
                        item_energy = item_energy[2:]
                    detail = f"{item_energy} {item_equipment} {item_description}".strip()
                    if detail:
                        details.append(detail)

                details.sort(key=lambda s: [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s)])
                detail_str = ', '.join(details) if details else "LOTO Points"

                logger.info(f"Regenerate Count-Sticker für Gruppe '{group_name}': {count} Items")

                count_copies_default = max(1, int(getattr(self.count_config, 'count_print_copies', 1)))
                copies = old_copies_per_group.get(group_name, count_copies_default)
                count_img = self.count_generator.generate(detail_str, count)
                self.collection.append([
                    count_img, "COUNT_MULTI", "TOTAL", "", "",
                    {"type": "count_multi", "group": group_name, "details": detail_str, "copies": copies},
                    count_img
                ])

            self.update_collection_list()

            if was_count_selected:
                new_count_row = len(self.collection) - 1
                self.collection_list.setCurrentRow(new_count_row)
        except Exception as e:
            logger.warning(f"Count-Sticker konnte nicht aktualisiert werden: {e}")

    def move_item_up(self):
        """Gewähltes Element in der Sammlung nach oben verschieben"""
        current_row = self.collection_list.currentRow()
        if current_row <= 0:
            msg = self._create_styled_msgbox("Info", "Element ist bereits an der ersten Position oder nichts gewählt", QMessageBox.Icon.Information)
            msg.exec()
            return

        self.collection[current_row], self.collection[current_row - 1] = \
            self.collection[current_row - 1], self.collection[current_row]

        self.update_collection_list()
        self.collection_list.setCurrentRow(current_row - 1)
        if self.status_bar:
            self.status_bar.showMessage("Element nach oben verschoben", 2000)

    def move_item_down(self):
        """Gewähltes Element in der Sammlung nach unten verschieben"""
        current_row = self.collection_list.currentRow()
        if current_row < 0 or current_row >= len(self.collection) - 1:
            msg = self._create_styled_msgbox("Info", "Element ist bereits an der letzten Position oder nichts gewählt", QMessageBox.Icon.Information)
            msg.exec()
            return

        self.collection[current_row], self.collection[current_row + 1] = \
            self.collection[current_row + 1], self.collection[current_row]

        self.update_collection_list()
        self.collection_list.setCurrentRow(current_row + 1)
        if self.status_bar:
            self.status_bar.showMessage("Element nach unten verschoben", 2000)

    def delete_selected_items(self):
        """Gewählte Elemente aus der Sammlung löschen"""
        selected_items = self.collection_list.selectedItems()
        if not selected_items:
            msg = self._create_styled_msgbox("Info", "Keine Elemente gewählt", QMessageBox.Icon.Information)
            msg.exec()
            return

        selected_rows = []
        for item in selected_items:
            row = self.collection_list.row(item)
            if row >= 0:
                selected_rows.append(row)

        if not selected_rows:
            return

        msg = self._create_styled_msgbox(
            "Bestätigung",
            f"{len(selected_rows)} Element(e) löschen?",
            QMessageBox.Icon.Question,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        reply = msg.exec()

        if reply == QMessageBox.StandardButton.Yes:
            for row in sorted(selected_rows, reverse=True):
                if 0 <= row < len(self.collection):
                    del self.collection[row]

            self.update_collection_list()
            if self.status_bar:
                self.status_bar.showMessage(f"{len(selected_rows)} Element(e) gelöscht", 2000)
