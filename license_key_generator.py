#!/usr/bin/env python3
"""
Lizenzschlüssel Generator für TAG!T LOTO Sticker App
Eigenständiges Tool zum Generieren und Verwalten von Lizenzschlüsseln
"""

import sys
import json
import random
import string
import datetime
import hashlib
import base64
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QSpinBox, QDateEdit,
    QGroupBox, QMessageBox, QFileDialog, QTableWidget, QTableWidgetItem,
    QHeaderView, QComboBox
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor


class LicenseKeyGenerator(QMainWindow):
    """Hauptfenster für Lizenzschlüssel-Generator"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TAG!T Lizenzschlüssel Generator")
        self.setMinimumSize(800, 600)
        self.resize(900, 700)
        
        # Pfad zur Schlüsseldatenbank
        self.keys_db_path = Path(__file__).parent / "generated_keys.json"
        self.generated_keys = self.load_keys_database()
        
        self.init_ui()
        self.load_keys_to_table()
    
    def init_ui(self):
        """UI aufbauen"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Titel
        title = QLabel("🔑 Lizenzschlüssel Generator")
        title_font = QFont("Arial", 18, QFont.Weight.Bold)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)
        
        # Generator-Bereich
        generator_group = QGroupBox("Neuen Schlüssel generieren")
        generator_layout = QVBoxLayout()
        
        # Anzahl Schlüssel
        count_layout = QHBoxLayout()
        count_layout.addWidget(QLabel("Anzahl:"))
        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 100)
        self.count_spin.setValue(1)
        self.count_spin.setFixedWidth(100)
        count_layout.addWidget(self.count_spin)
        count_layout.addStretch()
        generator_layout.addLayout(count_layout)
        
        # Gültigkeitsdauer
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("Gültigkeitsdauer (Tage):"))
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 3650)
        self.duration_spin.setValue(365)
        self.duration_spin.setFixedWidth(100)
        duration_layout.addWidget(self.duration_spin)
        duration_layout.addStretch()
        generator_layout.addLayout(duration_layout)
        
        # Notiz
        note_layout = QHBoxLayout()
        note_layout.addWidget(QLabel("Notiz (optional):"))
        self.note_input = QLineEdit()
        self.note_input.setPlaceholderText("z.B. Kunde, Projekt, etc.")
        note_layout.addWidget(self.note_input)
        generator_layout.addLayout(note_layout)
        
        # Generate Button
        generate_btn = QPushButton("🔑 Schlüssel generieren")
        generate_btn.setMinimumHeight(40)
        generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border-radius: 8px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
        """)
        generate_btn.clicked.connect(self.generate_keys)
        generator_layout.addWidget(generate_btn)
        
        generator_group.setLayout(generator_layout)
        main_layout.addWidget(generator_group)
        
        # Tabelle für generierte Schlüssel
        table_group = QGroupBox("Generierte Schlüssel")
        table_layout = QVBoxLayout()
        
        self.keys_table = QTableWidget()
        self.keys_table.setColumnCount(5)
        self.keys_table.setHorizontalHeaderLabels([
            "Lizenzschlüssel", "Erstellt am", "Gültig bis", "Status", "Notiz"
        ])
        self.keys_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.keys_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.keys_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.keys_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.keys_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.keys_table.setAlternatingRowColors(True)
        self.keys_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.keys_table.setSelectionMode(QTableWidget.SelectionMode.MultiSelection)
        
        table_layout.addWidget(self.keys_table)
        
        # Buttons für Tabelle
        table_buttons = QHBoxLayout()
        
        copy_btn = QPushButton("Kopieren")
        copy_btn.clicked.connect(self.copy_selected_key)
        table_buttons.addWidget(copy_btn)
        
        export_btn = QPushButton("Als Text exportieren")
        export_btn.clicked.connect(self.export_keys)
        table_buttons.addWidget(export_btn)
        
        delete_btn = QPushButton("Löschen")
        delete_btn.setStyleSheet("QPushButton { background-color: #dc2626; color: white; }")
        delete_btn.clicked.connect(self.delete_selected_key)
        table_buttons.addWidget(delete_btn)
        
        table_buttons.addStretch()
        
        table_layout.addLayout(table_buttons)
        table_group.setLayout(table_layout)
        main_layout.addWidget(table_group)
        
        # Status Label
        self.status_label = QLabel("Bereit")
        self.status_label.setStyleSheet("color: #6b7280; font-style: italic;")
        main_layout.addWidget(self.status_label)
    
    def generate_license_key(self, duration_days):
        """Generiert einen signierten Lizenzschlüssel mit eingebetteter Gültigkeitsdauer"""
        # Secret für Signatur (WICHTIG: Geheim halten!)
        SECRET = "TAGIT_LICENSE_MASTER_KEY_2026_SECURE"
        
        # Erstelle Schlüssel-Daten
        # Format: DAYS-RANDOM-RANDOM-SIGNATURE
        
        # Teil 1: Tage kodiert (base36, 4 chars)
        days_hex = format(duration_days, 'X').zfill(4)
        
        # Teil 2+3: Zufällige IDs für Eindeutigkeit
        chars = string.ascii_uppercase + string.digits
        random_part1 = ''.join(random.choices(chars, k=4))
        random_part2 = ''.join(random.choices(chars, k=4))
        
        # Kombiniere Daten für Signatur
        data_to_sign = f"{days_hex}-{random_part1}-{random_part2}"
        
        # Teil 4: HMAC Signatur (erste 4 chars)
        signature = hashlib.sha256(f"{data_to_sign}|{SECRET}".encode()).hexdigest()[:4].upper()
        
        # Vollständiger Schlüssel
        return f"{days_hex}-{random_part1}-{random_part2}-{signature}"
    
    def generate_keys(self):
        """Generiert mehrere Lizenzschlüssel"""
        count = self.count_spin.value()
        duration_days = self.duration_spin.value()
        note = self.note_input.text().strip()
        
        generated = []
        for _ in range(count):
            key = self.generate_license_key(duration_days)
            created_date = datetime.datetime.now()
            expiry_date = created_date + datetime.timedelta(days=duration_days)
            
            key_data = {
                "key": key,
                "created_at": created_date.isoformat(),
                "expiry_date": expiry_date.isoformat(),
                "duration_days": duration_days,
                "note": note,
                "status": "Aktiv"
            }
            
            self.generated_keys.append(key_data)
            generated.append(key)
        
        # Speichern
        self.save_keys_database()
        
        # Tabelle aktualisieren
        self.load_keys_to_table()
        
        # Status
        self.status_label.setText(f"{count} Schlüssel generiert!")
        self.status_label.setStyleSheet("color: #16a34a; font-weight: bold;")
        
        # Notiz-Feld leeren
        self.note_input.clear()
        
        # Info-Dialog
        QMessageBox.information(
            self,
            "Erfolg",
            f"{count} Lizenzschlüssel wurden erfolgreich generiert!\n\n"
            f"Gültig für {duration_days} Tage."
        )
    
    def load_keys_to_table(self):
        """Lädt alle Schlüssel in die Tabelle"""
        self.keys_table.setRowCount(0)
        
        for key_data in self.generated_keys:
            row = self.keys_table.rowCount()
            self.keys_table.insertRow(row)
            
            # Schlüssel
            key_item = QTableWidgetItem(key_data["key"])
            key_item.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
            self.keys_table.setItem(row, 0, key_item)
            
            # Erstellt am
            created = datetime.datetime.fromisoformat(key_data["created_at"])
            self.keys_table.setItem(row, 1, QTableWidgetItem(created.strftime("%d.%m.%Y")))
            
            # Gültig bis
            expiry = datetime.datetime.fromisoformat(key_data["expiry_date"])
            expiry_item = QTableWidgetItem(expiry.strftime("%d.%m.%Y"))
            
            # Färbe abgelaufene Schlüssel rot
            if datetime.datetime.now() > expiry:
                expiry_item.setForeground(QColor("#dc2626"))
                key_data["status"] = "Abgelaufen"
            
            self.keys_table.setItem(row, 2, expiry_item)
            
            # Status
            status_item = QTableWidgetItem(key_data.get("status", "Aktiv"))
            if key_data.get("status") == "Abgelaufen":
                status_item.setForeground(QColor("#dc2626"))
            else:
                status_item.setForeground(QColor("#16a34a"))
            self.keys_table.setItem(row, 3, status_item)
            
            # Notiz
            self.keys_table.setItem(row, 4, QTableWidgetItem(key_data.get("note", "")))
        
        # Update Status
        total = len(self.generated_keys)
        active = sum(1 for k in self.generated_keys if k.get("status") == "Aktiv")
        self.status_label.setText(f"Insgesamt: {total} Schlüssel ({active} aktiv)")
        self.status_label.setStyleSheet("color: #6b7280;")
    
    def copy_selected_key(self):
        """Kopiert den ausgewählten Schlüssel in die Zwischenablage"""
        selected_rows = self.keys_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "Warnung", "Bitte wählen Sie einen Schlüssel aus.")
            return
        
        row = self.keys_table.currentRow()
        key = self.keys_table.item(row, 0).text()
        
        clipboard = QApplication.clipboard()
        clipboard.setText(key)
        
        self.status_label.setText(f"Schlüssel kopiert: {key}")
        self.status_label.setStyleSheet("color: #16a34a;")
    
    def export_keys(self):
        """Exportiert alle Schlüssel als Textdatei"""
        if not self.generated_keys:
            QMessageBox.warning(self, "Warnung", "Keine Schlüssel zum Exportieren vorhanden.")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Schlüssel exportieren",
            "lizenzschluessel.txt",
            "Text Files (*.txt);;All Files (*)"
        )
        
        if not filename:
            return
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("TAG!T LOTO Sticker - Lizenzschlüssel\n")
                f.write("=" * 80 + "\n\n")
                
                for idx, key_data in enumerate(self.generated_keys, 1):
                    expiry = datetime.datetime.fromisoformat(key_data["expiry_date"])
                    f.write(f"Schlüssel #{idx}:\n")
                    f.write(f"  Lizenzschlüssel: {key_data['key']}\n")
                    f.write(f"  Gültig bis: {expiry.strftime('%d.%m.%Y')}\n")
                    if key_data.get("note"):
                        f.write(f"  Notiz: {key_data['note']}\n")
                    f.write("\n")
            
            QMessageBox.information(self, "Erfolg", f"Schlüssel wurden exportiert nach:\n{filename}")
            
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Fehler beim Exportieren:\n{str(e)}")
    
    def delete_selected_key(self):
        """Löscht die ausgewählten Schlüssel"""
        selected_rows = self.keys_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Warnung", "Bitte wählen Sie mindestens einen Schlüssel aus.")
            return
        
        # Sammle alle ausgewählten Schlüssel
        keys_to_delete = []
        for index in selected_rows:
            row = index.row()
            key = self.keys_table.item(row, 0).text()
            keys_to_delete.append(key)
        
        # Bestätigungsdialog
        count = len(keys_to_delete)
        if count == 1:
            message = f"Schlüssel wirklich löschen?\n\n{keys_to_delete[0]}"
        else:
            message = f"{count} Schlüssel wirklich löschen?\n\n" + "\n".join(keys_to_delete[:5])
            if count > 5:
                message += f"\n... und {count - 5} weitere"
        
        reply = QMessageBox.question(
            self,
            "Bestätigung",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Lösche alle ausgewählten Schlüssel
            self.generated_keys = [k for k in self.generated_keys if k["key"] not in keys_to_delete]
            self.save_keys_database()
            self.load_keys_to_table()
            
            self.status_label.setText(f"{count} Schlüssel gelöscht")
            self.status_label.setStyleSheet("color: #dc2626;")
    
    def load_keys_database(self):
        """Lädt die Schlüsseldatenbank"""
        if not self.keys_db_path.exists():
            return []
        
        try:
            with open(self.keys_db_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    
    def save_keys_database(self):
        """Speichert die Schlüsseldatenbank"""
        try:
            with open(self.keys_db_path, 'w', encoding='utf-8') as f:
                json.dump(self.generated_keys, f, indent=4, ensure_ascii=False)
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Fehler beim Speichern:\n{str(e)}")


def main():
    app = QApplication(sys.argv)
    
    # Setze App-Style
    app.setStyle("Fusion")
    
    window = LicenseKeyGenerator()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
