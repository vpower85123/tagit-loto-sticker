from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFileDialog, QProgressBar, QFrame, QWidget, QTableWidget, 
    QTableWidgetItem, QHeaderView, QMessageBox, QApplication, QTextEdit
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QColor
from ui.glass_button import GlassGlowButton
import fitz
import re
import tempfile
import os
import logging
import datetime
from pathlib import Path
from PIL import Image, ImageStat, ImageFilter, ImageDraw
try:
    import cv2  # type: ignore
    import numpy as np  # type: ignore
except Exception:
    cv2 = None
    np = None

# pyzbar für zuverlässige QR-Erkennung
try:
    from pyzbar import pyzbar  # type: ignore
except Exception:
    pyzbar = None

logger = logging.getLogger(__name__)

class PDFImportDialog(QDialog):
    def __init__(self, parent=None, sticker_config=None):
        super().__init__(parent)
        self.setWindowTitle("Sticker aus PDF importieren")
        self.setMinimumSize(900, 700)
        self.selected_file = None
        self.extracted_data = []
        self.count_sticker_groups = []  # Erkannte Count-Sticker Gruppen aus PDF
        self.import_qr_path = None
        self._temp_qr_files = []
        self.sticker_config = sticker_config
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Header
        header = QLabel("PDF Import")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #333;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Info Text
        info = QLabel("Wählen Sie eine PDF-Datei aus. Das Tool versucht automatisch, mehrere Sticker pro Seite zu erkennen.")
        info.setWordWrap(True)
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)
        
        # File Selection Area
        self.file_frame = QFrame()
        self.file_frame.setStyleSheet("""
            QFrame {
                border: 2px dashed #ccc;
                border-radius: 10px;
                background-color: rgba(255, 255, 255, 0.5);
            }
            QFrame:hover {
                border-color: #1E90FF;
                background-color: rgba(30, 144, 255, 0.1);
            }
        """)
        file_layout = QVBoxLayout(self.file_frame)
        file_layout.setContentsMargins(20, 20, 20, 20)
        
        self.file_label = QLabel("Keine Datei ausgewählt")
        self.file_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.file_label.setStyleSheet("color: #666;")
        file_layout.addWidget(self.file_label)
        
        select_btn = GlassGlowButton("PDF auswählen", dark_mode=False)
        select_btn.setFixedWidth(200)
        select_btn.setMinimumHeight(44)
        select_btn.clicked.connect(self.select_file)
        file_layout.addWidget(select_btn, 0, Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(self.file_frame)
        
        # Preview Table (Ablage)
        self.preview_label = QLabel("Gefundene Sticker:")
        self.preview_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        self.preview_label.setVisible(False)
        layout.addWidget(self.preview_label)
        
        self.preview_table = QTableWidget()
        self.preview_table.setColumnCount(3)
        self.preview_table.setHorizontalHeaderLabels(["Energy ID", "Equipment", "Beschreibung"])
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.preview_table.setVisible(False)
        self.preview_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 4px;
                border: none;
                border-bottom: 1px solid #ddd;
            }
        """)
        self.preview_table.itemChanged.connect(self.on_item_changed)
        layout.addWidget(self.preview_table)
        
        # Progress (Hidden initially)
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        cancel_btn = GlassGlowButton("Abbrechen", dark_mode=False)
        cancel_btn.setMinimumWidth(120)
        cancel_btn.setMinimumHeight(44)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        self.import_btn = GlassGlowButton("Importieren", dark_mode=False)
        self.import_btn.setMinimumWidth(120)
        self.import_btn.setMinimumHeight(44)
        self.import_btn.clicked.connect(self.accept)
        self.import_btn.setEnabled(False)
        btn_layout.addWidget(self.import_btn)
        
        # Debug Button
        debug_btn = GlassGlowButton("Debug", dark_mode=False)
        debug_btn.setMinimumWidth(100)
        debug_btn.setMinimumHeight(44)
        debug_btn.setToolTip("Zeigt den extrahierten Text der ersten Seite zur Analyse")
        debug_btn.clicked.connect(self.debug_first_page)
        btn_layout.addWidget(debug_btn)
        
        # QR-Code Auswahl Button
        self.qr_btn = GlassGlowButton("QR-Code", dark_mode=False)
        self.qr_btn.setMinimumWidth(120)
        self.qr_btn.setMinimumHeight(44)
        self.qr_btn.setToolTip("QR-Code Bilddatei auswählen (optional)")
        self.qr_btn.clicked.connect(self.select_qr_image)
        btn_layout.addWidget(self.qr_btn)
        
        layout.addLayout(btn_layout)
        
        # QR Status Label
        self.qr_status_label = QLabel("")
        self.qr_status_label.setStyleSheet("color: #17a2b8; font-style: italic;")
        layout.addWidget(self.qr_status_label)
        
        # Styling
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
        """)

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "PDF auswählen", "", "PDF Dateien (*.pdf)"
        )
        if file_path:
            self.selected_file = file_path
            self.file_label.setText(file_path.split('/')[-1])
            self.file_label.setStyleSheet("color: #333; font-weight: bold;")
            self.extract_data()

    def select_qr_image(self):
        """Manuell eine QR-Code Bilddatei auswählen."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "QR-Code Bild auswählen", 
            "", 
            "Bilddateien (*.png *.jpg *.jpeg *.bmp *.gif);;Alle Dateien (*.*)"
        )
        if file_path:
            self.import_qr_path = file_path
            filename = file_path.split('/')[-1].split('\\')[-1]
            self.qr_status_label.setText(f"✓ QR-Code: {filename}")
            self.qr_btn.setText(f"✓ {filename}")

    def debug_first_page(self):
        """Shows raw text of first page for debugging."""
        if not self.selected_file:
            QMessageBox.warning(self, "Info", "Bitte erst eine Datei auswählen.")
            return
            
        try:
            doc = fitz.open(self.selected_file)
            if len(doc) > 0:
                page = doc[0]
                text = page.get_text("text", sort=True)
                
                # Show in a dialog
                msg = QDialog(self)
                msg.setWindowTitle("Debug: Seite 1 Text")
                msg.resize(600, 800)
                l = QVBoxLayout(msg)
                t = QTextEdit()
                t.setPlainText(text)
                t.setReadOnly(True)
                l.addWidget(t)
                msg.exec()
            doc.close()
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))
    
    def extract_qr_code_from_sticker(self, page, bbox):
        """Extrahiert den QR-Code Bereich aus einem Sticker im PDF.
        
        Args:
            page: fitz Page object
            bbox: Bounding box des Stickers {'x0', 'y0', 'x1', 'y1'}
            
        Returns:
            Pfad zur temporären QR-Code Bilddatei oder None
        """
        try:
            # QR-Code Position basierend auf Sticker-Vorgabe (rechts oben)
            sticker_width = bbox['x1'] - bbox['x0']
            sticker_height = bbox['y1'] - bbox['y0']
            
            # QR-Code ist ca. so groß wie die Sticker-Höhe und rechts positioniert
            # Basierend auf dem Sticker-Layout: QR hat etwa die gleiche Größe wie die Höhe
            qr_size = sticker_height * 0.85  # 85% der Höhe für den QR-Code
            
            # Margins: minimal vom Rand (der Sticker hat bereits Padding)
            margin_right = sticker_height * 0.08  # 8% vom rechten Rand
            margin_top = sticker_height * 0.08   # 8% vom oberen Rand
            
            # QR-Code Bereich definieren (rechts oben im Sticker)
            qr_x0 = bbox['x1'] - qr_size - margin_right
            qr_y0 = bbox['y0'] + margin_top
            qr_x1 = bbox['x1'] - margin_right
            qr_y1 = qr_y0 + qr_size
            
            # Bereich aus PDF als Bild rendern (höhere Auflösung für bessere Qualität)
            mat = fitz.Matrix(4.0, 4.0)  # 4x zoom für bessere QR-Code Qualität
            qr_rect = fitz.Rect(qr_x0, qr_y0, qr_x1, qr_y1)
            pix = page.get_pixmap(matrix=mat, clip=qr_rect, alpha=True)
            
            # Als PIL Image konvertieren
            img_mode = "RGBA" if pix.alpha else "RGB"
            img = Image.frombytes(img_mode, (pix.width, pix.height), pix.samples)
            
            # Prüfen ob der extrahierte Bereich nicht nur weiß/leer ist
            # (einfacher Check: wenn >95% der Pixel ähnlich sind, wahrscheinlich kein QR-Code)
            extrema = img.convert('L').getextrema()
            if extrema[1] - extrema[0] < 30:  # Sehr geringer Kontrast
                return None
            
            # Temporäre Datei erstellen
            temp_fd, temp_path = tempfile.mkstemp(suffix='.png', prefix='qr_code_')
            os.close(temp_fd)
            
            # Bild speichern
            img.save(temp_path, 'PNG')
            self.temp_qr_files.append(temp_path)
            
            return temp_path
            
        except Exception as e:
            print(f"QR-Code Extraktion fehlgeschlagen: {e}")
            return None
    
    def cleanup_temp_files(self):
        """Löscht temporäre QR-Code Dateien."""
        for temp_file in self.temp_qr_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except Exception as e:
                print(f"Konnte temporäre Datei nicht löschen {temp_file}: {e}")
        self.temp_qr_files.clear()

    def extract_data(self):
        """Extracts data from the selected PDF and populates the table."""
        if not self.selected_file:
            return
            
        self.progress.setVisible(True)
        self.progress.setRange(0, 0) # Indeterminate
        QApplication.processEvents()
        
        try:
            doc = fitz.open(self.selected_file)
            self.extracted_data = []
            self.count_sticker_groups = []  # Reset bei erneutem Parsen
            
            print(f"\n*** PDF hat {len(doc)} Seiten ***\n")
            
            for page_num, page in enumerate(doc):
                print(f"\n*** Verarbeite Seite {page_num + 1}/{len(doc)} ***")
                
                # ALTE METHODE: Verwende einfache Text-Extraktion mit dict
                text_dict = page.get_text("dict")
                
                stickers_data = []
                current_sticker = {}
                current_count_sticker_items = []  # Sammelt Energy-IDs eines Count-Stickers
                in_count_sticker = False  # Sind wir gerade innerhalb eines Count-Stickers?
                
                # Gelbe Rechtecke erkennen (LOTO-Sticker Hintergrund)
                yellow_rects = []
                try:
                    drawings = page.get_drawings()
                    for d in drawings:
                        fill = d.get("fill")
                        if fill and len(fill) >= 3:
                            r, g, b = fill[0], fill[1], fill[2]
                            # Gelb-Erkennung: hoher Rot- & Grün-Anteil, niedriger Blau-Anteil
                            if r > 0.7 and g > 0.5 and b < 0.4:
                                yellow_rects.append(d["rect"])
                    if yellow_rects:
                        print(f"DEBUG: {len(yellow_rects)} gelbe Rechtecke erkannt auf Seite {page_num + 1}")
                except Exception as e:
                    print(f"DEBUG: get_drawings fehlgeschlagen: {e} - akzeptiere alle Sticker")
                    yellow_rects = []
                
                # Durchsuche alle Textblöcke
                for block in text_dict.get("blocks", []):
                    if block.get("type") != 0:  # Skip non-text blocks
                        continue
                    
                    for line in block.get("lines", []):
                        line_text = ""
                        for span in line.get("spans", []):
                            line_text += span.get("text", "")
                        
                        line_text = line_text.strip()
                        if not line_text:
                            continue
                        
                        # Überspringe Header-Zeilen
                        if line_text.startswith('# LOTO POINT'):
                            continue
                        
                        # Count-Sticker erkennen: "TOTAL COUNT OF LOTO POINTS"
                        if 'TOTAL COUNT OF LOTO POINTS' in line_text:
                            # Wenn vorher ein Count-Sticker lief, speichere ihn
                            if in_count_sticker and current_count_sticker_items:
                                self.count_sticker_groups.append(list(current_count_sticker_items))
                                print(f"DEBUG: Count-Sticker Gruppe gespeichert ({len(current_count_sticker_items)} Items): {current_count_sticker_items}")
                                current_count_sticker_items = []
                            in_count_sticker = True
                            # Vorherigen regulären Sticker abschließen
                            if current_sticker.get("energy_id"):
                                stickers_data.append(current_sticker)
                                current_sticker = {}
                            continue
                        
                        # Wenn wir innerhalb eines Count-Stickers sind:
                        # Zeilen enthalten volle Energy-IDs getrennt durch ; oder ,
                        # z.B. "E1.ELEC.DP.KSV1.SC_02.01; E2.ELEC.DP.SC_02.01.DHE6_0014;"
                        if in_count_sticker:
                            # Prüfe ob Zeile Energy-IDs enthält (am Zeilenanfang nach [EPMC])
                            if re.match(r'^[EPMC]\d+', line_text, re.IGNORECASE):
                                # Splitte nach ; oder , und extrahiere volle Energy-IDs
                                entries = re.split(r'[;,]', line_text)
                                for entry in entries:
                                    entry = entry.strip().rstrip('.')
                                    if not entry:
                                        continue
                                    # Validiere: Muss mit Energy-ID Pattern beginnen
                                    if re.match(r'^[EPMC]\d+', entry, re.IGNORECASE):
                                        current_count_sticker_items.append(entry.upper())
                                        print(f"DEBUG: Count-Sticker Entry: '{entry.upper()}'")
                                continue
                            else:
                                # Nicht-Energy-ID Text beendet den Count-Sticker
                                if current_count_sticker_items:
                                    self.count_sticker_groups.append(list(current_count_sticker_items))
                                    print(f"DEBUG: Count-Sticker Gruppe gespeichert ({len(current_count_sticker_items)} Items)")
                                    current_count_sticker_items = []
                                in_count_sticker = False
                        
                        print(f"DEBUG: Textzeile gefunden: '{line_text}'")
                        
                        # Prüfe auf Energy ID Pattern - verschiedene Formate:
                        # Format 1: "E1 ADTA.D.IF.RC01" - Energy ID + Leerzeichen + Equipment
                        # Format 2: "E1.ASML.1.PLUG" - Energy ID als ganzer Text (mit Punkten)
                        
                        # Pattern für Format 1: E1, E2, P1 etc. gefolgt von Leerzeichen und Equipment
                        energy_match = re.match(r'^([EPMC]\d+)\s+(.+)$', line_text, re.IGNORECASE)
                        
                        # Pattern für Format 2: E1.xxx.xxx - Energy ID mit Punkten (ganzer Text ist die ID)
                        # z.B. "E1.ASML.1.PLUG" - hier ist E1 die Energy ID und der Rest ist Equipment
                        energy_dot_match = None
                        if not energy_match:
                            energy_dot_match = re.match(r'^([EPMC]\d+)\.(.+)$', line_text, re.IGNORECASE)
                        
                        # Fallback: Nummer ohne Präfix (z.B. "10 ADTA..." statt "E10 ADTA...")
                        # Dies passiert wenn PDF den Buchstaben E separat rendert
                        number_only_match = None
                        if not energy_match and not energy_dot_match:
                            number_only_match = re.match(r'^(\d+)\s+(.+)$', line_text)
                            if number_only_match:
                                # Prüfe ob die Nummer plausibel ist (1-99)
                                num = int(number_only_match.group(1))
                                if num >= 1 and num <= 99:
                                    print(f"DEBUG: Nummer ohne Präfix gefunden: {num} - wird als E{num} interpretiert")
                        
                        if energy_match:
                            # Energy ID mit Equipment auf gleicher Zeile (Leerzeichen-Trennung)
                            print(f"DEBUG: Energy ID + Equipment gefunden: {energy_match.group(1)} - {energy_match.group(2)}")
                            # Neuer Sticker beginnt
                            if current_sticker.get("energy_id"):
                                stickers_data.append(current_sticker)
                                print(f"DEBUG: Vorheriger Sticker gespeichert: {current_sticker['energy_id']}")
                            
                            eid = energy_match.group(1).upper()
                            equipment = energy_match.group(2).strip()
                            current_sticker = {"energy_id": eid, "equipment": equipment, "_bbox": line["bbox"]}
                            
                            # Symbol-Typ basierend auf Präfix
                            if eid[0] == 'P':
                                current_sticker["symbol_type"] = "PNEUMATIC"
                            elif eid[0] == 'M':
                                current_sticker["symbol_type"] = "MECHANICAL"
                            elif eid[0] == 'C':
                                current_sticker["symbol_type"] = "CHEMICAL"
                            else:
                                current_sticker["symbol_type"] = "ELECTRICAL"
                        
                        elif energy_dot_match:
                            # Format 2: E1.ASML.1.PLUG - Punkt-getrennt
                            # Die komplette Zeile ist die Energy ID (z.B. "E1.ASML.1.PLUG")
                            eid = line_text.upper()
                            equipment = ""  # Equipment ist leer bei diesem Format
                            
                            print(f"DEBUG: Energy ID (Punkt-Format) gefunden: {eid}")
                            
                            if current_sticker.get("energy_id"):
                                stickers_data.append(current_sticker)
                                print(f"DEBUG: Vorheriger Sticker gespeichert: {current_sticker['energy_id']}")
                            
                            current_sticker = {"energy_id": eid, "equipment": equipment, "_bbox": line["bbox"]}
                            
                            # Symbol-Typ basierend auf erstem Buchstaben
                            prefix = energy_dot_match.group(1).upper()[0]
                            if prefix == 'P':
                                current_sticker["symbol_type"] = "PNEUMATIC"
                            elif prefix == 'M':
                                current_sticker["symbol_type"] = "MECHANICAL"
                            elif prefix == 'C':
                                current_sticker["symbol_type"] = "CHEMICAL"
                            else:
                                current_sticker["symbol_type"] = "ELECTRICAL"
                        
                        elif number_only_match:
                            # Nummer ohne Präfix - interpretiere als E-Nummer
                            num = number_only_match.group(1)
                            equipment = number_only_match.group(2).strip()
                            eid = f"E{num}"
                            
                            print(f"DEBUG: Energy ID (aus Nummer) + Equipment gefunden: {eid} - {equipment}")
                            
                            if current_sticker.get("energy_id"):
                                stickers_data.append(current_sticker)
                                print(f"DEBUG: Vorheriger Sticker gespeichert: {current_sticker['energy_id']}")
                            
                            current_sticker = {"energy_id": eid, "equipment": equipment, "symbol_type": "ELECTRICAL", "_bbox": line["bbox"]}
                        
                        # Prüfe ob NUR Energy ID (z.B. "E1" allein)
                        elif re.match(r'^([EPMC]\d+)$', line_text, re.IGNORECASE):
                            energy_only = re.match(r'^([EPMC]\d+)$', line_text, re.IGNORECASE)
                            print(f"DEBUG: Energy ID Match gefunden: {energy_only.group(1)}")
                            # Neuer Sticker beginnt
                            if current_sticker.get("energy_id"):
                                stickers_data.append(current_sticker)
                                print(f"DEBUG: Vorheriger Sticker gespeichert: {current_sticker['energy_id']}")
                            
                            eid = energy_only.group(1).upper()
                            current_sticker = {"energy_id": eid}
                            current_sticker["_bbox"] = line["bbox"]
                            
                            # Symbol-Typ basierend auf Präfix
                            if eid[0] == 'P':
                                current_sticker["symbol_type"] = "PNEUMATIC"
                            elif eid[0] == 'M':
                                current_sticker["symbol_type"] = "MECHANICAL"
                            elif eid[0] == 'C':
                                current_sticker["symbol_type"] = "CHEMICAL"
                            else:
                                current_sticker["symbol_type"] = "ELECTRICAL"
                        
                        elif current_sticker.get("energy_id"):
                            # Sammle Equipment/Description für aktuellen Sticker
                            if "equipment" not in current_sticker:
                                current_sticker["equipment"] = line_text
                            elif "description" not in current_sticker:
                                current_sticker["description"] = line_text
                            else:
                                # Füge zur Description hinzu
                                current_sticker["description"] += " " + line_text
                
                # Letzten Sticker hinzufügen
                if current_sticker.get("energy_id"):
                    stickers_data.append(current_sticker)
                
                # Letzten Count-Sticker speichern
                if current_count_sticker_items:
                    self.count_sticker_groups.append(list(current_count_sticker_items))
                    print(f"DEBUG: Letzte Count-Sticker Gruppe gespeichert: {current_count_sticker_items}")
                    current_count_sticker_items = []
                
                # Gelb-Filter: Nur Sticker innerhalb gelber Rechtecke behalten
                if yellow_rects:
                    filtered = []
                    for s in stickers_data:
                        bbox = s.get("_bbox")
                        if not bbox:
                            filtered.append(s)
                            continue
                        sx, sy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
                        in_yellow = False
                        for yr in yellow_rects:
                            if yr.x0 <= sx <= yr.x1 and yr.y0 <= sy <= yr.y1:
                                in_yellow = True
                                break
                        if in_yellow:
                            filtered.append(s)
                        else:
                            print(f"DEBUG: Sticker '{s.get('energy_id', '')}' nicht in gelbem Bereich → übersprungen")
                    stickers_data = filtered
                
                # Entferne interne bbox-Daten
                for s in stickers_data:
                    s.pop("_bbox", None)
                
                # Entferne Duplikate: Normalisiere equipment+description zu einem Schlüssel
                # z.B. "DOCKS.01." + "DOOR.LEVELER" und "DOCKS.01.DOOR.LEVELER," sind identisch
                def _dedup_key(s):
                    eid = s.get("energy_id", "").strip().upper()
                    eq = s.get("equipment", "").strip().rstrip(".,; ")
                    desc = s.get("description", "").strip().rstrip(".,; ")
                    if desc:
                        combined = f"{eq}.{desc}".strip(".")
                    else:
                        combined = eq.strip(".")
                    return (eid, combined.upper())
                
                unique_stickers = {}
                for sticker in stickers_data:
                    key = _dedup_key(sticker)
                    if key not in unique_stickers:
                        unique_stickers[key] = sticker
                    else:
                        # Bevorzuge Version mit separater Description (besser strukturiert)
                        existing = unique_stickers[key]
                        if sticker.get("description") and not existing.get("description"):
                            unique_stickers[key] = sticker
                        print(f"DEBUG: Duplikat entfernt: {key}")
                
                stickers_data = list(unique_stickers.values())
                
                # Hinzufügen zur extracted_data mit automatischer Trennung
                for sticker in stickers_data:
                    if "energy_id" in sticker:
                        # Count-Sticker überspringen (Beschreibung enthält "LOTO POINTS")
                        desc = sticker.get("description", "")
                        if "LOTO POINTS" in desc.upper():
                            print(f"DEBUG: Count-Sticker übersprungen: {sticker.get('energy_id', '')} - {desc}")
                            continue
                        
                        # Automatische Trennung von Energy-ID und Equipment
                        energy_id = sticker.get("energy_id", "")
                        equipment = sticker.get("equipment", "")
                        
                        # Wenn Equipment leer ist, versuche aus Energy-ID zu extrahieren
                        if energy_id and not equipment:
                            energy_id, equipment = self._split_energy_equipment(energy_id)
                            sticker["energy_id"] = energy_id
                            sticker["equipment"] = equipment
                        
                        self.extracted_data.append(sticker)
                        eq = sticker.get("equipment", "")[:30]
                        print(f"*** Sticker hinzugefügt: {sticker['energy_id']} - {eq} ***")
                
                print(f"*** Seite {page_num + 1} abgeschlossen: {len(self.extracted_data)} Sticker insgesamt ***")
                
                # QR-Code einmal pro Import extrahieren (von erster Seite mit Stickern)
                qr_path_for_page = None
                if self.import_qr_path is None and stickers_data:
                    try:
                        # Verwende ganze Seite für QR-Extraktion
                        bbox = {
                            'x0': 0,
                            'y0': 0,
                            'x1': page.rect.width,
                            'y1': page.rect.height
                        }
                        qr_path_for_page = self._extract_qr_from_sticker(page, bbox)
                        self.import_qr_path = qr_path_for_page  # Globaler Fallback
                        if qr_path_for_page:
                            logger.info(f"*** QR-Code erfolgreich extrahiert: {qr_path_for_page} ***")
                        else:
                            logger.warning("*** QR-Code Extraktion fehlgeschlagen (None zurückgegeben) ***")
                    except Exception as e:
                        logger.error(f"*** QR-Code Extraktion Exception: {e} ***")
                        qr_path_for_page = None
                
                # QR-Code-Pfad zu jedem Sticker hinzufügen
                if qr_path_for_page:
                    for sticker in stickers_data:
                        if "energy_id" in sticker:
                            sticker["qr_path"] = qr_path_for_page
                            logger.info(f"QR-Code zugewiesen zu Sticker: {sticker['energy_id']} -> {qr_path_for_page}")
                
                # Add separator
                # Add separator
                self.extracted_data.append({"is_separator": True, "page_num": page_num + 1})
            
            doc.close()
            
            # Globaler Dedup-Pass über alle Seiten hinweg
            # Normalisiert equipment+description um identische Sticker in verschiedenen
            # Textformaten zu erkennen (z.B. "DOCKS.01." + "DOOR.LEVELER" vs "DOCKS.01.DOOR.LEVELER")
            def _global_dedup_key(s):
                eid = s.get("energy_id", "").strip().upper()
                eq = s.get("equipment", "").strip().rstrip(".,; ")
                desc = s.get("description", "").strip().rstrip(".,; ")
                # Kombiniere equipment + description zu normalisierten Schlüssel
                parts = []
                if eq:
                    parts.append(eq)
                if desc:
                    parts.append(desc)
                combined = ".".join(parts).replace("..", ".").strip(".")
                return (eid, combined.upper())
            
            seen_keys = set()
            deduped_data = []
            global_dupes = 0
            for entry in self.extracted_data:
                if entry.get("is_separator"):
                    deduped_data.append(entry)
                    continue
                key = _global_dedup_key(entry)
                if key in seen_keys:
                    global_dupes += 1
                    print(f"DEBUG GLOBAL: Duplikat entfernt: {key}")
                    continue
                seen_keys.add(key)
                deduped_data.append(entry)
            
            if global_dupes:
                print(f"*** GLOBAL DEDUP: {global_dupes} Duplikate entfernt ***")
            self.extracted_data = deduped_data
            
            self.update_table()
            
            if not [d for d in self.extracted_data if not d.get("is_separator")]:
                QMessageBox.warning(self, "Import", "Keine Sticker gefunden. Bitte prüfen Sie das Format.")
            
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Fehler beim Lesen der PDF:\n{str(e)}")
        finally:
            self.progress.setVisible(False)

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

    def _extract_qr_from_sticker(self, page, bbox):
        """Extrahiert den QR-Code aus der PDF-Seite.
        
        Scannt die ganze Seite nach QR-Codes und extrahiert den ersten gefundenen.
        Der extrahierte QR wird auf weißem Hintergrund mit Padding gespeichert.
        Jeder Import bekommt einen eindeutigen Dateinamen basierend auf Zeitstempel.
        """
        print("=== _extract_qr_from_sticker AUFGERUFEN ===")
        
        # Generiere eindeutigen Dateinamen für diesen Import
        import time
        self._current_qr_filename = f"import_qr_{int(time.time() * 1000)}.png"
        
        try:
            logger.info("QR-Extraktion gestartet - scanne ganze Seite")
            print("QR-Extraktion gestartet")
            
            # Rendere die GANZE SEITE in hoher Auflösung
            pix = page.get_pixmap(matrix=fitz.Matrix(4, 4))
            
            # Konvertiere zu numpy array für OpenCV
            import numpy as np
            import cv2
            
            # Verwende samples statt tobytes für korrekte Array-Konvertierung
            img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            
            print(f"DEBUG QR: Bild-Shape: {img_array.shape}, pix.n={pix.n}")
            
            # Konvertiere zu BGR für OpenCV
            if pix.n == 4:
                img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
            elif pix.n == 3:
                img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            else:
                img_cv = img_array
            
            # Erkenne QR-Codes mit OpenCV - mit Vorverarbeitung für bessere Erkennung
            qr_content = None
            qr_points = None  # Speichere die QR-Position
            
            # Konvertiere zu Graustufen für bessere QR-Erkennung
            img_gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            
            # Versuche verschiedene Threshold-Methoden
            detector = cv2.QRCodeDetector()
            
            # Methode 1: Direktes Bild
            retval, decoded_info, points, _ = detector.detectAndDecodeMulti(img_cv)
            if decoded_info:
                for idx, info in enumerate(decoded_info):
                    if info and len(info) > 0:
                        qr_content = info
                        qr_points = points[idx] if points is not None and len(points) > idx else None
                        print(f"*** QR gefunden (direkt): {qr_content[:50]}... ***")
                        break
            
            # Methode 2: Graustufen + Threshold
            if not qr_content:
                _, img_thresh = cv2.threshold(img_gray, 127, 255, cv2.THRESH_BINARY)
                retval, decoded_info, points, _ = detector.detectAndDecodeMulti(img_thresh)
                if decoded_info:
                    for idx, info in enumerate(decoded_info):
                        if info and len(info) > 0:
                            qr_content = info
                            qr_points = points[idx] if points is not None and len(points) > idx else None
                            print(f"*** QR gefunden (threshold): {qr_content[:50]}... ***")
                            break
            
            # Methode 3: Adaptive Threshold
            if not qr_content:
                img_adaptive = cv2.adaptiveThreshold(img_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
                retval, decoded_info, points, _ = detector.detectAndDecodeMulti(img_adaptive)
                if decoded_info:
                    for idx, info in enumerate(decoded_info):
                        if info and len(info) > 0:
                            qr_content = info
                            qr_points = points[idx] if points is not None and len(points) > idx else None
                            print(f"*** QR gefunden (adaptive): {qr_content[:50]}... ***")
                            break
            
            # Methode 4: Einzelner QR-Detektor
            if not qr_content:
                data, pts, _ = detector.detectAndDecode(img_gray)
                if data:
                    qr_content = data
                    qr_points = pts
                    print(f"*** QR gefunden (single): {qr_content[:50]}... ***")
            
            if qr_content:
                print(f"*** QR-Code Inhalt: {qr_content[:80]}... ***")
                
                # Extrahiere das Original QR-Bild aus der PDF
                try:
                    import os
                    
                    if qr_points is not None:
                        pts = qr_points.astype(int)
                        
                        # Bounding Box mit großzügigem Padding
                        padding = 20
                        qr_x = max(0, pts[:, 0].min() - padding)
                        qr_y = max(0, pts[:, 1].min() - padding)
                        qr_x_max = min(img_cv.shape[1], pts[:, 0].max() + padding)
                        qr_y_max = min(img_cv.shape[0], pts[:, 1].max() + padding)
                        
                        print(f"*** QR-Position: x={qr_x}-{qr_x_max}, y={qr_y}-{qr_y_max} ***")
                        
                        # Extrahiere QR-Bereich
                        qr_crop = img_cv[qr_y:qr_y_max, qr_x:qr_x_max]
                        
                        # Konvertiere BGR zu RGB für PIL
                        qr_crop_rgb = cv2.cvtColor(qr_crop, cv2.COLOR_BGR2RGB)
                        
                        # Speichere als PNG
                        from PIL import Image
                        qr_pil = Image.fromarray(qr_crop_rgb)
                        
                        # Skaliere auf einheitliche Größe
                        qr_pil = qr_pil.resize((400, 400), Image.Resampling.LANCZOS)
                        
                        qr_dir = os.path.join(os.path.dirname(__file__), "..", "temp_qr")
                        qr_dir = os.path.normpath(qr_dir)
                        os.makedirs(qr_dir, exist_ok=True)
                        qr_path = os.path.join(qr_dir, self._current_qr_filename)
                        qr_path = os.path.normpath(qr_path)
                        qr_pil.save(qr_path, "PNG")
                        
                        print(f"*** Original QR-Code extrahiert und gespeichert: {qr_path} ***")
                        logger.info(f"Original QR-Code extrahiert: {qr_path}")
                        return qr_path
                    else:
                        print("*** Keine QR-Points vorhanden, verwende Fallback ***")
                    
                except Exception as extract_err:
                    print(f"*** Fehler beim Extrahieren des Original-QR: {extract_err} ***")
                
                # Fallback: Generiere neuen QR-Code
                try:
                    import qrcode
                    from PIL import Image
                    
                    qr = qrcode.QRCode(
                        version=1,
                        error_correction=qrcode.constants.ERROR_CORRECT_M,
                        box_size=10,
                        border=4,
                    )
                    qr.add_data(qr_content)
                    qr.make(fit=True)
                    
                    qr_img = qr.make_image(fill_color="black", back_color="white")
                    
                    import os
                    qr_dir = os.path.join(os.path.dirname(__file__), "..", "temp_qr")
                    qr_dir = os.path.normpath(qr_dir)
                    os.makedirs(qr_dir, exist_ok=True)
                    qr_path = os.path.join(qr_dir, self._current_qr_filename)
                    qr_path = os.path.normpath(qr_path)
                    qr_img.save(qr_path)
                    
                    print(f"*** Neuer QR-Code generiert und gespeichert: {qr_path} ***")
                    logger.info(f"QR-Code neu generiert und gespeichert: {qr_path}")
                    return qr_path
                    
                    print(f"*** Neuer QR-Code generiert und gespeichert: {qr_path} ***")
                    logger.info(f"QR-Code neu generiert und gespeichert: {qr_path}")
                    return qr_path
                    
                except ImportError:
                    print("*** qrcode library nicht installiert, verwende extrahiertes Bild ***")
                    # Fallback: Extrahiere Bild wie vorher
                    qr_idx = 0
                    pts = points[qr_idx]
                    pts = pts.astype(int)
                    
                    qr_x = pts[:, 0].min()
                    qr_y = pts[:, 1].min()
                    qr_x_max = pts[:, 0].max()
                    qr_y_max = pts[:, 1].max()
                    
                    padding = 20
                    qr_crop = img_cv[max(0, qr_y - padding):min(img_cv.shape[0], qr_y_max + padding),
                                     max(0, qr_x - padding):min(img_cv.shape[1], qr_x_max + padding)]
                    
                    qr_gray = cv2.cvtColor(qr_crop, cv2.COLOR_BGR2GRAY)
                    _, qr_bw = cv2.threshold(qr_gray, 127, 255, cv2.THRESH_BINARY)
                    
                    import os
                    qr_dir = os.path.join(os.path.dirname(__file__), "..", "temp_qr")
                    os.makedirs(qr_dir, exist_ok=True)
                    qr_path = os.path.join(qr_dir, self._current_qr_filename)
                    cv2.imwrite(qr_path, qr_bw)
                    return qr_path
                
                print(f"*** QR-Code gespeichert: {qr_path} ***")
                logger.info(f"QR-Code extrahiert und gespeichert: {qr_path}")
                return qr_path
            else:
                print("*** Keine QR-Codes gefunden ***")
                logger.warning("Keine QR-Codes in der PDF gefunden")
                return None
        
        except Exception as e:
            print(f"*** QR-Extraktion fehlgeschlagen: {e} ***")
            logger.error(f"QR-Extraktion fehlgeschlagen: {e}")
            return None

    def cleanup_temp_files(self):
        """Temporäre Dateien werden jetzt dauerhaft in temp_qr/ gespeichert."""
        # Keine temporären Dateien mehr - QR-Codes bleiben erhalten
        pass

    def update_table(self):
        """Updates the preview table with extracted data."""
        self.preview_table.blockSignals(True)
        self.preview_table.setRowCount(len(self.extracted_data))
        
        for i, data in enumerate(self.extracted_data):
            if data.get("is_separator"):
                self.preview_table.setSpan(i, 0, 1, 3)
                item = QTableWidgetItem(f"--- Seite {data.get('page_num', '?')} ---")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setBackground(QColor("#FFEB3B")) # Yellow
                item.setForeground(QColor("#000000"))
                item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                self.preview_table.setItem(i, 0, item)
            else:
                self.preview_table.setItem(i, 0, QTableWidgetItem(data.get("energy_id", "")))
                self.preview_table.setItem(i, 1, QTableWidgetItem(data.get("equipment", "")))
                self.preview_table.setItem(i, 2, QTableWidgetItem(data.get("description", "")))
        
        self.preview_table.blockSignals(False)
        self.preview_table.setVisible(True)
        self.preview_label.setVisible(True)
        
        real_stickers = [d for d in self.extracted_data if not d.get("is_separator")]
        
        if real_stickers:
            self.import_btn.setEnabled(True)
            self.import_btn.setText(f"{len(real_stickers)} Sticker importieren")
        else:
            self.import_btn.setEnabled(False)
            self.import_btn.setText("Importieren")

    def on_item_changed(self, item):
        """Updates extracted_data when table cell is edited."""
        row = item.row()
        col = item.column()
        
        if row < 0 or row >= len(self.extracted_data):
            return
            
        data = self.extracted_data[row]
        if data.get("is_separator"):
            return
            
        text = item.text()
        if col == 0:
            data["energy_id"] = text
        elif col == 1:
            data["equipment"] = text
        elif col == 2:
            data["description"] = text

