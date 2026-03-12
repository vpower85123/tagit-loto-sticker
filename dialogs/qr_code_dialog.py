#!/usr/bin/env python3
"""
QR-Code Verwaltungsdialog für Equipment
Ermöglicht Anzeige, Bearbeitung, Löschen und Neu-Zuweisen von QR-Codes
"""

import os
import tempfile
from pathlib import Path
from typing import Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFileDialog, QMessageBox, QGroupBox, QLineEdit, QTextEdit
)
from PyQt6.QtCore import Qt, QSize
import qtawesome as qta
from PyQt6.QtGui import QPixmap, QImage
from PIL import Image
from ui.glass_button import GlassGlowButton


class QRCodeDialog(QDialog):
    """Dialog zum Anzeigen und Verwalten von QR-Codes für Equipment"""
    
    def __init__(self, parent=None, equipment_name: str = "", current_qr_path: str = ""):
        super().__init__(parent)
        self.equipment_name = equipment_name
        self.current_qr_path = current_qr_path
        self.new_qr_path: Optional[str] = None  # Geänderter QR-Pfad
        self.qr_deleted = False  # Flag ob QR gelöscht wurde
        
        self.setWindowTitle(f"QR-Code: {equipment_name}")
        self.setMinimumSize(500, 600)
        self.resize(550, 650)
        
        self.init_ui()
        self.load_qr_code()
    
    def init_ui(self):
        """UI aufbauen"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Titel
        title = QLabel(f"QR-Code für: {self.equipment_name}")
        title.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #2563eb;
                padding: 10px;
                background-color: #eff6ff;
                border-radius: 6px;
            }
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # QR-Code Anzeige
        qr_group = QGroupBox("QR-Code Vorschau")
        qr_layout = QVBoxLayout()
        
        self.qr_label = QLabel("Kein QR-Code vorhanden")
        self.qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qr_label.setMinimumSize(300, 300)
        self.qr_label.setStyleSheet("""
            QLabel {
                background-color: #f8fafc;
                border: 2px dashed #cbd5e1;
                border-radius: 8px;
                padding: 20px;
                color: #64748b;
                font-size: 14px;
            }
        """)
        qr_layout.addWidget(self.qr_label)
        
        qr_group.setLayout(qr_layout)
        layout.addWidget(qr_group)
        
        # Pfad-Anzeige
        path_group = QGroupBox("Dateipfad")
        path_layout = QVBoxLayout()
        
        self.path_display = QLineEdit()
        self.path_display.setReadOnly(True)
        self.path_display.setPlaceholderText("Kein QR-Code zugewiesen")
        self.path_display.setStyleSheet("""
            QLineEdit {
                background-color: #f1f5f9;
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Courier New', monospace;
                font-size: 11px;
            }
        """)
        path_layout.addWidget(self.path_display)
        
        path_group.setLayout(path_layout)
        layout.addWidget(path_group)
        
        # Info-Label
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #64748b; font-style: italic; padding: 5px;")
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)
        
        # Aktionsbuttons
        actions_layout = QHBoxLayout()
        
        # Neu zuweisen Button
        assign_btn = GlassGlowButton("QR-Code zuweisen")
        assign_btn.setIcon(qta.icon('ph.folder-open', color='#374151'))
        assign_btn.setFixedHeight(38)
        assign_btn.clicked.connect(self.assign_new_qr)
        actions_layout.addWidget(assign_btn)
        
        # QR-Code generieren Button
        generate_btn = GlassGlowButton("QR generieren")
        generate_btn.setIcon(qta.icon('ph.qr-code', color='#374151'))
        generate_btn.setFixedHeight(38)
        generate_btn.clicked.connect(self.generate_qr_code)
        actions_layout.addWidget(generate_btn)
        
        # Löschen Button
        self.delete_btn = GlassGlowButton("Löschen")
        self.delete_btn.setIcon(qta.icon('ph.trash', color='#374151'))
        self.delete_btn.setFixedHeight(38)
        self.delete_btn.clicked.connect(self.delete_qr)
        actions_layout.addWidget(self.delete_btn)
        
        layout.addLayout(actions_layout)
        
        # Dialog Buttons
        dialog_buttons = QHBoxLayout()
        dialog_buttons.addStretch()
        
        save_btn = GlassGlowButton("Speichern")
        save_btn.setFixedHeight(38)
        save_btn.setMinimumWidth(140)
        save_btn.clicked.connect(self.accept)
        dialog_buttons.addWidget(save_btn)
        
        cancel_btn = GlassGlowButton("Abbrechen")
        cancel_btn.setFixedHeight(38)
        cancel_btn.setMinimumWidth(140)
        cancel_btn.clicked.connect(self.reject)
        dialog_buttons.addWidget(cancel_btn)
        
        layout.addLayout(dialog_buttons)
    
    def load_qr_code(self):
        """Lädt und zeigt den aktuellen QR-Code"""
        qr_path = self.new_qr_path or self.current_qr_path
        
        if not qr_path or self.qr_deleted:
            self.qr_label.setPixmap(QPixmap())
            self.qr_label.setText("Kein QR-Code vorhanden")
            self.path_display.clear()
            self.delete_btn.setEnabled(False)
            self.info_label.setText("Kein QR-Code zugewiesen")
            return
        
        # Pfad in Path-Objekt konvertieren
        qr_path_obj = Path(qr_path)
        
        # Prüfe ob Datei existiert
        if not qr_path_obj.exists():
            self.qr_label.setPixmap(QPixmap())
            self.qr_label.setText(f"Datei nicht gefunden:\n{qr_path}")
            self.qr_label.setStyleSheet(self.qr_label.styleSheet() + "color: #dc2626;")
            self.path_display.setText(qr_path)
            self.delete_btn.setEnabled(True)
            self.info_label.setText("Datei existiert nicht mehr, aber Pfad ist gespeichert")
            return
        
        try:
            # Lade Bild mit PIL
            img = Image.open(qr_path_obj)
            
            # Konvertiere zu RGBA falls nötig
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            # Skaliere auf max 300x300 für Anzeige
            img.thumbnail((300, 300), Image.Resampling.LANCZOS)
            
            # Konvertiere zu QPixmap
            img_data = img.tobytes('raw', 'RGBA')
            qimage = QImage(img_data, img.width, img.height, QImage.Format.Format_RGBA8888)
            pixmap = QPixmap.fromImage(qimage)
            
            self.qr_label.setPixmap(pixmap)
            self.qr_label.setText("")
            self.qr_label.setStyleSheet("""
                QLabel {
                    background-color: white;
                    border: 2px solid #cbd5e1;
                    border-radius: 8px;
                    padding: 10px;
                }
            """)
            self.qr_label.setScaledContents(False)
            
            # Zeige Pfad
            self.path_display.setText(str(qr_path_obj.absolute()))
            
            # Aktiviere Löschen-Button
            self.delete_btn.setEnabled(True)
            
            # Info über Dateigröße
            file_size = qr_path_obj.stat().st_size
            size_kb = file_size / 1024
            self.info_label.setText(f"QR-Code geladen • Größe: {img.width}x{img.height}px • {size_kb:.1f} KB")
            
        except Exception as e:
            self.qr_label.setPixmap(QPixmap())
            self.qr_label.setText(f"Fehler beim Laden:\n{str(e)}")
            self.qr_label.setStyleSheet(self.qr_label.styleSheet() + "color: #dc2626;")
            self.path_display.setText(qr_path)
            self.delete_btn.setEnabled(True)
            self.info_label.setText(f"Fehler: {str(e)}")
    
    def assign_new_qr(self):
        """Öffnet Dateidialog zum Zuweisen eines neuen QR-Codes"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "QR-Code Bild auswählen",
            str(Path.home()),
            "Bilder (*.png *.jpg *.jpeg *.bmp *.gif);;PDF Dateien (*.pdf);;Alle Dateien (*)"
        )
        
        if file_path:
            self.new_qr_path = file_path
            self.qr_deleted = False
            self.load_qr_code()
            self.info_label.setText("Neuer QR-Code ausgewählt (noch nicht gespeichert)")
    
    def delete_qr(self):
        """Löscht die QR-Code Zuweisung"""
        reply = QMessageBox.question(
            self,
            "QR-Code löschen",
            f"QR-Code Zuweisung für '{self.equipment_name}' wirklich löschen?\n\n"
            "Die Bilddatei bleibt erhalten, nur die Verknüpfung wird gelöscht.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.new_qr_path = ""
            self.qr_deleted = True
            self.load_qr_code()
            self.info_label.setText("QR-Code gelöscht (wird beim Speichern wirksam)")
    
    def generate_qr_code(self):
        """Generiert einen neuen QR-Code basierend auf Equipment-Daten"""
        from PyQt6.QtWidgets import QInputDialog
        
        # Frage nach QR-Code Inhalt
        text, ok = QInputDialog.getText(
            self,
            "QR-Code generieren",
            f"Text/Daten für QR-Code von '{self.equipment_name}':\n\n"
            "Geben Sie den Inhalt ein (z.B. Equipment-ID, URL, etc.)",
            text=self.equipment_name  # Vorausfüllen mit Equipment-Name
        )
        
        if not ok or not text:
            return
        
        try:
            # Importiere qrcode Bibliothek
            import qrcode
            
            # Generiere QR-Code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=10,
                border=4,
            )
            qr.add_data(text)
            qr.make(fit=True)
            
            # Erstelle Bild
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Speichere in temp_qr Ordner
            temp_qr_dir = Path(__file__).parent.parent / "temp_qr"
            temp_qr_dir.mkdir(exist_ok=True)
            
            # Dateiname: equipment_name_YYYYMMDD_HHMMSS.png
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in self.equipment_name)
            filename = f"{safe_name}_{timestamp}.png"
            
            qr_path = temp_qr_dir / filename
            img.save(str(qr_path))
            
            # Setze neuen Pfad
            self.new_qr_path = str(qr_path)
            self.qr_deleted = False
            self.load_qr_code()
            
            QMessageBox.information(
                self,
                "QR-Code generiert",
                f"QR-Code erfolgreich generiert!\n\nInhalt: {text}\nGespeichert in: {qr_path}"
            )
            
        except ImportError:
            QMessageBox.warning(
                self,
                "Bibliothek fehlt",
                "Die 'qrcode' Bibliothek ist nicht installiert.\n\n"
                "Installieren Sie diese mit:\npip install qrcode[pil]"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Fehler",
                f"Fehler beim Generieren des QR-Codes:\n{str(e)}"
            )
    
    def get_qr_path(self) -> Optional[str]:
        """Gibt den finalen QR-Pfad zurück (None wenn gelöscht)"""
        if self.qr_deleted:
            return None
        return self.new_qr_path or self.current_qr_path
