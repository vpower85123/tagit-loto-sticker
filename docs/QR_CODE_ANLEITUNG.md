# 🔳 QR-Code Funktionen - Benutzeranleitung

## Schnellübersicht

Die TAG!T Sticker App kann QR-Codes automatisch extrahieren, speichern und verwalten. Hier erfahren Sie, wie Sie die QR-Code-Funktionen nutzen können.

---

## 1. 📥 QR-Codes beim PDF-Import

### Automatische Extraktion

Wenn Sie Sticker aus einem PDF importieren:

1. **Datei → Aus PDF importieren**
2. PDF-Datei auswählen
3. **QR-Codes werden automatisch erkannt und extrahiert!**
4. Import bestätigen

✅ **Fertig!** QR-Codes sind jetzt mit jedem Sticker verknüpft.

### Was passiert?

- Die App scannt jeden Sticker
- Sucht QR-Codes im rechten oberen Bereich
- Speichert sie in `temp_qr/` Ordner
- Verknüpft sie automatisch mit dem Sticker

---

## 2. 🗂️ Equipment mit QR-Code anlegen

### Automatische Übernahme aus Collection

**Workflow:**

1. **Sticker importieren** (mit QR-Code)
2. **Rechtsklick** auf Sticker in der Collection
3. **"Equipment automatisch gruppieren"** wählen
4. **Ziel-System** auswählen
5. **Speichern**

✅ **QR-Code wird automatisch mit übernommen!**

### Manuelle Prüfung

Im **Equipment-Tab**:
- Rechtsklick auf Equipment
- "🔳 QR-Code verwalten"
- QR-Code wird angezeigt

---

## 3. 🖱️ QR-Codes im Equipment-Manager verwalten

### Rechtsklick-Menü

**Im Equipment-Tab:**

```
Equipment-Tree
└── Rechtsklick auf Equipment
    ├── ➕ Zur Sammlung hinzufügen
    ├── ─────────────────────────
    ├── 🔳 QR-Code verwalten      ← Hauptmenü
    ├── 📂 QR-Code zuweisen       ← Schnellzuweisung
    └── 🗑️ QR-Code löschen        ← Verknüpfung löschen
```

### 3.1 QR-Code verwalten

**Vollständiger Dialog mit allen Funktionen:**

1. **Rechtsklick** auf Equipment
2. **"🔳 QR-Code verwalten"**
3. Dialog öffnet sich mit:
   - **Vorschau** (300x300px)
   - **Dateipfad** (Read-only)
   - **Aktionen:**
     - 📂 QR-Code zuweisen (neue Datei)
     - 🔳 QR generieren (neuen QR erstellen)
     - 🗑️ Löschen (Verknüpfung entfernen)

### 3.2 QR-Code zuweisen (Schnell)

**Für schnelle Zuweisungen:**

1. **Rechtsklick** auf Equipment
2. **"📂 QR-Code zuweisen"**
3. **Datei auswählen** (PNG, JPG, etc.)
4. **Fertig!** Wird automatisch gespeichert

### 3.3 QR-Code generieren

**Neuen QR-Code erstellen:**

1. **Rechtsklick** → "🔳 QR-Code verwalten"
2. **"🔳 QR generieren"** Button
3. **Text eingeben** (z.B. Equipment-ID, URL, etc.)
4. **OK**
5. QR wird erstellt und gespeichert

**Beispiel-Eingaben:**
- `E001-Motor-Haupthalle`
- `https://equipment.example.com/E001`
- `DBE1/ADTA/Motor-1`

### 3.4 QR-Code löschen

**Verknüpfung entfernen:**

1. **Rechtsklick** → "🗑️ QR-Code löschen"
2. **Bestätigen**
3. Verknüpfung wird gelöscht

⚠️ **Hinweis:** Die Bilddatei bleibt erhalten, nur die Verknüpfung wird entfernt.

---

## 4. 📂 QR-Code Dateiverwaltung

### Speicherort

Alle QR-Codes werden hier gespeichert:
```
TAG!T/Sticker/temp_qr/
```

### Dateinamen

**Format:** `<Equipment-Name>_<Datum>_<Zeit>.png`

**Beispiele:**
- `Motor_1_20260128_143022.png`
- `ADTA_PUMP_20260128_143055.png`

### Dateiformate

**Unterstützte Formate:**
- PNG ✅ (Empfohlen)
- JPG/JPEG ✅
- BMP ✅
- GIF ✅
- PDF ✅ (wird zu PNG konvertiert)

---

## 5. 🎯 Praktische Beispiele

### Beispiel 1: PDF-Import mit QR-Codes

**Szenario:** Sie haben ein PDF mit 10 Stickern, jeder hat einen QR-Code.

**Schritte:**
1. **Datei → Aus PDF importieren**
2. PDF auswählen
3. ✅ **10 Sticker werden importiert**
4. ✅ **10 QR-Codes werden automatisch extrahiert**
5. **Rechtsklick** auf ersten Sticker → "Equipment gruppieren"
6. System auswählen
7. ✅ **Equipment wird mit QR-Code angelegt**

### Beispiel 2: QR-Code nachträglich hinzufügen

**Szenario:** Equipment existiert bereits, QR-Code soll hinzugefügt werden.

**Schritte:**
1. **Equipment-Tab** öffnen
2. **Rechtsklick** auf Equipment
3. **"📂 QR-Code zuweisen"**
4. QR-Bild auswählen
5. ✅ **Fertig!**

### Beispiel 3: QR-Code für mehrere Equipment generieren

**Szenario:** Sie möchten für 5 Motoren jeweils einen QR-Code erstellen.

**Schritte:**
```
Für jeden Motor:
1. Rechtsklick → "🔳 QR-Code verwalten"
2. "🔳 QR generieren"
3. Text eingeben: "Motor-1-Halle-A"
4. Speichern
```

---

## 6. ⚙️ Erweiterte Funktionen

### QR-Code in Sticker anzeigen

**Im Sticker-Tab:**

1. **QR-Modus aktivieren** (Checkbox)
2. **QR-Bild auswählen** (Browse-Button)
3. **Vorschau** wird automatisch aktualisiert
4. QR erscheint rechts oben im Sticker

### QR-Code kopieren

**Zwischen Equipment übertragen:**

1. Equipment A: Rechtsklick → "QR verwalten"
2. **Pfad kopieren** (aus Textfeld)
3. Equipment B: Rechtsklick → "QR verwalten"
4. "📂 QR-Code zuweisen"
5. Gleichen Pfad verwenden

---

## 7. 💡 Tipps & Tricks

### ✅ Best Practices

1. **Einheitliche Benennung**
   ```
   Equipment-Name → QR-Inhalt
   Motor 1      → E001-Motor-1-Halle-A
   Pumpe 3      → E023-Pumpe-3-Technikraum
   ```

2. **QR-Code Qualität**
   - Mindestens 300x300px
   - Hoher Kontrast (schwarz auf weiß)
   - PNG-Format bevorzugen

3. **Backup**
   - Sichern Sie den `temp_qr/` Ordner regelmäßig
   - QR-Codes können extern archiviert werden

### ⚠️ Häufige Probleme

**QR-Code wird nicht angezeigt**
- ✓ Prüfen Sie, ob Datei noch existiert
- ✓ Pfad überprüfen (absoluter Pfad empfohlen)

**QR-Code generieren funktioniert nicht**
- ✓ Library installieren: `pip install qrcode[pil]`

**QR wird nicht aus PDF extrahiert**
- ✓ Prüfen Sie QR-Position (rechts oben im Sticker)
- ✓ QR-Code muss ausreichend groß sein

---

## 8. 📊 Workflow-Übersicht

```
┌─────────────────┐
│  PDF-Datei      │
│  (mit Stickern) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Import         │
│  QR-Extraktion  │ ← Automatisch
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Collection     │
│  (mit QR)       │
└────────┬────────┘
         │
         ├─ Rechtsklick
         │
         ▼
┌─────────────────┐
│  Equipment      │
│  Manager        │ ← QR automatisch übernommen
└────────┬────────┘
         │
         ├─ Rechtsklick
         │
         ▼
┌─────────────────┐
│  QR-Code        │
│  Verwaltung     │ ← Anzeigen/Bearbeiten/Löschen
└─────────────────┘
```

---

## 9. 🔧 Installation (optional)

### QR-Code Generierung

Für die QR-Code-Generierung benötigen Sie:

```bash
pip install qrcode[pil]
```

### QR-Code Erkennung (erweitert)

Für verbesserte QR-Erkennung:

```bash
pip install opencv-python pyzbar
```

---

## 10. 📞 Support

### Dokumentation

- **Vollständige Technische Dokumentation:** `docs/QR_CODE_FEATURE.md`
- **Equipment-Manager:** `docs/EQUIPMENT_MANAGER.md`
- **PDF-Import:** `docs/PDF_IMPORT.md`

### Hilfe

Bei Fragen oder Problemen:
1. Prüfen Sie die Logs (Console-Ausgabe)
2. Überprüfen Sie Dateipfade
3. Stellen Sie sicher, dass alle Libraries installiert sind

---

## ✨ Zusammenfassung

**QR-Code Funktionen:**

✅ Automatische Extraktion beim PDF-Import  
✅ Automatische Übernahme in Equipment-Manager  
✅ Komfortable Verwaltung per Rechtsklick  
✅ QR-Generierung integriert  
✅ Flexible Dateiverwaltung  

**Kein manueller Aufwand nötig** - QR-Codes werden automatisch verwaltet! 🚀
