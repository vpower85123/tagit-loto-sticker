# QR-Code Funktionalität - Implementierungsübersicht

## 📋 Zusammenfassung

Die TAG!T Sticker App unterstützt vollständige QR-Code Verwaltung für Equipment mit folgenden Funktionen:

1. ✅ **QR-Code Extraktion beim PDF-Import**
2. ✅ **QR-Code Speicherung in Equipment-Manager**
3. ✅ **QR-Code Übernahme aus Collection**
4. ✅ **QR-Code Verwaltung per Rechtsklick**

---

## 1. 🔍 QR-Code Extraktion beim PDF-Import

### Funktionsweise

**Datei:** `dialogs/pdf_import_dialog.py`  
**Methode:** `extract_qr_code_from_sticker(page, bbox)`

#### Ablauf:

1. **PDF-Seite analysieren**
   - Jeder erkannte Sticker wird gescannt
   - QR-Code Bereich wird berechnet (rechts oben, 85% der Höhe)

2. **QR-Code Region extrahieren**
   ```python
   qr_size = sticker_height * 0.85  # 85% der Höhe
   margin_right = sticker_height * 0.08  # 8% vom rechten Rand
   margin_top = sticker_height * 0.08   # 8% vom oberen Rand
   ```

3. **Als Bild speichern**
   - Temporärer Pfad in `temp_qr/` Ordner
   - Format: PNG mit 4x Zoom für bessere Qualität
   - Dateiname: `<equipment_name>_YYYYMMDD_HHMMSS.png`

4. **QR-Pfad zurückgeben**
   - Wird in `import_qr_path` gespeichert
   - Wird bei Import zur Collection hinzugefügt

### Beispiel:

```python
# PDF-Import Dialog
dialog = PDFImportDialog(self, sticker_config=config)
if dialog.exec() == QDialog.DialogCode.Accepted:
    extracted_data = dialog.extracted_data
    import_qr_path = dialog.import_qr_path  # ← QR-Code Pfad
```

---

## 2. 💾 QR-Code Speicherung in Equipment-Manager

### Datenstruktur

**Datei:** `managers/equipment_manager.py`  
**Datenmodell:** Equipment-JSON enthält `qr_path` Feld

```json
{
  "STANDORT_NAME": {
    "systems": [
      {
        "name": "SYSTEM_NAME",
        "equipment": [
          {
            "name": "BETRIEBSMITTEL_NAME",
            "energy_id": "E001",
            "symbol_type": "ELECTRICAL",
            "description": "Beschreibung",
            "qr_path": "c:/path/to/qr_code.png"  ← QR-Code Pfad
          }
        ]
      }
    ]
  }
}
```

### Methoden:

```python
# Equipment mit QR-Code hinzufügen
equipment_manager.add_equipment(
    location_name="DBE1",
    system_name="ADTA",
    equipment_name="Motor 1",
    energy_id="E001",
    symbol_type="ELECTRICAL",
    description="Hauptmotor",
    qr_path="/path/to/qr.png"  # ← QR-Code
)

# QR-Code aktualisieren
equipment_list = equipment_manager.get_equipment(location, system)
for eq in equipment_list:
    if eq['name'] == equipment_name:
        eq['qr_path'] = new_qr_path
        break
equipment_manager.save()
```

---

## 3. 📥 QR-Code Übernahme aus Collection

### Funktionsweise

**Datei:** `sticker_app_pyqt6.py`  
**Methode:** `_add_collection_item_to_equipment_manager(row)`

#### Ablauf:

1. **QR-Pfad aus Collection-Item extrahieren**
   ```python
   qr_path = ""
   if len(item) > 5:
       full_info = item[5]  # full_info ist ein Dict
       if isinstance(full_info, dict):
           qr_path = full_info.get("qr_path", "")
   ```

2. **Equipment mit QR-Pfad anlegen**
   ```python
   equipment_manager.add_equipment(
       location, system_name, equipment_name,
       energy_id=energy_id,
       symbol_type=symbol_type,
       qr_path=qr_path  # ← Wird übernommen!
   )
   ```

### Workflow:

1. **Sticker aus PDF importieren**
   - QR-Code wird extrahiert → `temp_qr/qr_image.png`
   - In Collection gespeichert mit `full_info["qr_path"]`

2. **Rechtsklick auf Collection-Item**
   - "Equipment automatisch gruppieren"

3. **Equipment-Manager Ziel auswählen**
   - Standort + System wählen

4. **Equipment wird angelegt**
   - ✅ Name, Energy-ID, Symbol-Typ
   - ✅ **QR-Code Pfad wird automatisch mit übernommen!**

---

## 4. 🖱️ QR-Code Verwaltung per Rechtsklick

### Equipment-Dialog Erweiterung

**Datei:** `dialogs/equipment_dialog.py`  
**Neue Funktionen im Kontextmenü:**

```
Rechtsklick auf Equipment-Item:
├── ➕ Zur Sammlung hinzufügen
├── ─────────────────────────
├── 🔳 QR-Code verwalten         ← NEU
├── 📂 QR-Code zuweisen          ← NEU
└── 🗑️ QR-Code löschen           ← NEU (nur wenn QR vorhanden)
```

### 4.1 QR-Code Verwaltungsdialog

**Datei:** `dialogs/qr_code_dialog.py`  
**Klasse:** `QRCodeDialog`

#### Features:

✅ **QR-Code Anzeige**
- Vorschau mit automatischer Skalierung (max 300x300px)
- Dateigröße und Dimensionen anzeigen
- Pfad-Anzeige mit Monospace-Font

✅ **QR-Code zuweisen**
- Dateidialog für PNG, JPG, BMP, GIF, PDF
- Unterstützte Formate werden automatisch konvertiert

✅ **QR-Code generieren**
- Integrierter QR-Generator (benötigt `qrcode` Library)
- Text-Input für QR-Inhalt
- Automatische Speicherung in `temp_qr/`

✅ **QR-Code löschen**
- Entfernt Verknüpfung (Datei bleibt erhalten)
- Bestätigungsdialog

#### Verwendung:

```python
from dialogs.qr_code_dialog import QRCodeDialog

# Dialog öffnen
dialog = QRCodeDialog(
    parent=self,
    equipment_name="Motor 1",
    current_qr_path="/path/to/current_qr.png"
)

if dialog.exec() == QDialog.DialogCode.Accepted:
    # Neuen QR-Pfad abrufen
    new_qr_path = dialog.get_qr_path()  # None wenn gelöscht
    
    # Im Equipment Manager speichern
    equipment['qr_path'] = new_qr_path or ""
    equipment_manager.save()
```

### 4.2 Schnellzuweisung

**Methode:** `_assign_qr_code_quick()`

- Direkter Dateidialog ohne vollständigen QRCodeDialog
- Schneller Workflow für einfache Zuweisungen
- Automatisches Speichern

### 4.3 QR-Code Löschen

**Methode:** `_delete_qr_code()`

- Löscht nur die Verknüpfung
- Bilddatei bleibt erhalten
- Bestätigungsdialog

---

## 📊 Datenfluss-Diagramm

```
┌─────────────────────┐
│   PDF-Import        │
│  (PDF mit Sticker)  │
└──────┬──────────────┘
       │
       ├─ extract_qr_code_from_sticker()
       │
       ▼
┌─────────────────────┐
│  temp_qr/           │
│  qr_image.png       │ ← QR-Code extrahiert
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│   Collection        │
│  full_info:         │
│  { qr_path: "..." } │
└──────┬──────────────┘
       │
       ├─ Rechtsklick → Equipment gruppieren
       │
       ▼
┌─────────────────────┐
│ Equipment Manager   │
│  {                  │
│    name: "Motor 1"  │
│    qr_path: "..."   │ ← QR übernommen
│  }                  │
└──────┬──────────────┘
       │
       ├─ Rechtsklick auf Equipment
       │
       ▼
┌─────────────────────┐
│  QR-Code Dialog     │
│  - Anzeigen         │
│  - Bearbeiten       │
│  - Generieren       │
│  - Löschen          │
└─────────────────────┘
```

---

## 🔧 Technische Details

### QR-Code Generierung

```python
import qrcode

qr = qrcode.QRCode(
    version=1,
    error_correction=qrcode.constants.ERROR_CORRECT_M,
    box_size=10,
    border=4,
)
qr.add_data(text)
qr.make(fit=True)

img = qr.make_image(fill_color="black", back_color="white")
img.save("temp_qr/qr_code.png")
```

### QR-Code Extraktion (PDF)

```python
# Mit PyMuPDF (fitz)
mat = fitz.Matrix(4.0, 4.0)  # 4x Zoom
qr_rect = fitz.Rect(x0, y0, x1, y1)
pix = page.get_pixmap(matrix=mat, clip=qr_rect, alpha=True)

# Als PIL Image
img = Image.frombytes("RGBA", (pix.width, pix.height), pix.samples)
img.save("temp_qr/extracted_qr.png")
```

### QR-Code Anzeige (PyQt6)

```python
from PIL import Image
from PyQt6.QtGui import QImage, QPixmap

img = Image.open(qr_path).convert('RGBA')
img.thumbnail((300, 300), Image.Resampling.LANCZOS)

img_data = img.tobytes('raw', 'RGBA')
qimage = QImage(img_data, img.width, img.height, QImage.Format.Format_RGBA8888)
pixmap = QPixmap.fromImage(qimage)

label.setPixmap(pixmap)
```

---

## 🎯 Verwendungsbeispiele

### Beispiel 1: PDF-Import mit QR-Codes

```python
# 1. PDF importieren
dialog = PDFImportDialog(self, sticker_config=config)
if dialog.exec() == QDialog.DialogCode.Accepted:
    # QR-Code wurde automatisch extrahiert
    qr_path = dialog.import_qr_path
    
    # 2. Sticker zur Collection hinzufügen
    full_info = {"qr_path": qr_path}
    self._add_to_collection_with_thumbnail(img, type, id, name, desc, full_info)
```

### Beispiel 2: Equipment mit QR anlegen

```python
# Aus Collection übernehmen
# → QR wird automatisch mit übernommen!
equipment_manager.add_equipment(
    location="DBE1",
    system="ADTA", 
    equipment_name="Motor",
    energy_id="E001",
    symbol_type="ELECTRICAL",
    qr_path=qr_path  # ← Automatisch aus Collection
)
```

### Beispiel 3: QR-Code nachträglich hinzufügen

```python
# 1. Rechtsklick im Equipment-Tree
# 2. "QR-Code zuweisen" wählen
# 3. Datei auswählen
# → Automatisch gespeichert!
```

### Beispiel 4: QR-Code generieren

```python
# 1. Rechtsklick im Equipment-Tree
# 2. "QR-Code verwalten"
# 3. "🔳 QR generieren" klicken
# 4. Text eingeben (z.B. "E001-Motor-1")
# 5. Speichern
# → QR automatisch in temp_qr/ erstellt und zugewiesen!
```

---

## 📝 Wichtige Hinweise

### QR-Code Speicherort

- **Extrahierte QR-Codes:** `temp_qr/`
- **Generierte QR-Codes:** `temp_qr/`
- **Format:** PNG mit schwarzem QR auf weißem Hintergrund

### Unterstützte Formate

- **Bilder:** PNG, JPG, JPEG, BMP, GIF
- **Dokumente:** PDF (erste Seite wird konvertiert)

### Dependencies

```bash
# QR-Code Generierung (optional)
pip install qrcode[pil]

# QR-Code Erkennung im PDF (optional, für erweiterte Features)
pip install opencv-python pyzbar
```

### Fehlerbehandlung

- **Datei nicht gefunden:** Dialog zeigt Warnung, aber Pfad bleibt gespeichert
- **Ungültiges Format:** Automatische Konvertierung zu PNG
- **Fehlende Library:** Benutzerfreundliche Fehlermeldung mit Installationshinweis

---

## 🚀 Zusammenfassung

Die QR-Code Funktionalität ist vollständig implementiert und bietet:

✅ **Automatische Extraktion** beim PDF-Import  
✅ **Persistente Speicherung** im Equipment-Manager  
✅ **Automatische Übernahme** aus der Collection  
✅ **Komfortable Verwaltung** per Rechtsklick-Menü  
✅ **QR-Generierung** direkt in der App  
✅ **Flexible Zuweisung** von externen QR-Dateien  

Die Implementierung ist nahtlos in den bestehenden Workflow integriert und erfordert keine manuellen Schritte für die QR-Übernahme!
