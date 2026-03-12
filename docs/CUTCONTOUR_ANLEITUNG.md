# Cut Contour für Mimaki CJV 30-60

## Übersicht
Die PDF-Export-Funktion erstellt jetzt automatisch **Schnittlinien (Cut Contours)** für jeden exportierten Sticker, die vom Mimaki CJV 30-60 Drucker/Schneidplotter erkannt und verarbeitet werden können.

**✨ NEU**: Die Cut-Contours berücksichtigen jetzt die **abgerundeten Ecken** der Sticker und Count-Sticker!

## Technische Details

### Spotfarbe
- **Farbe**: Magenta (CMYK: C=0, M=100, Y=0, K=0)
- **Linienstärke**: 0.1 Points (Hairline für präzises Schneiden)
- **Format**: PDF mit ReportLab generiert
- **Eckradius**: Automatisch aus Sticker-Konfiguration übernommen
  - Reguläre Sticker: 60 Pixel Radius (aus `config.json`)
  - Count-Sticker: 60 Pixel Radius (aus `config.json`)

### Implementierung
Die Funktion `draw_cut_contour()` in `pdf_exporter.py` zeichnet für jeden Sticker:
- **Abgerundete Kontur** passend zur Sticker-Form
- Optionaler Offset/Bleed-Rand (Standard: 0.0mm)
- Magenta-Spotfarbe für Mimaki-Erkennung
- Automatische Umrechnung Pixel → mm → Points

### Parameter
```python
draw_cut_contour(
    c,                    # ReportLab Canvas
    x_pt,                 # X-Position (Points)
    y_pt,                 # Y-Position (Points)
    width_pt,             # Breite (Points)
    height_pt,            # Höhe (Points)
    offset_mm=0.0,        # Zusätzlicher Rand in mm
    pt_per_mm=72/25.4,    # Umrechnungsfaktor
    corner_radius_px=60,  # Eckradius in Pixel (aus config.json)
    dpi=300               # DPI für Umrechnung
)
```

## Sticker-Formen

Die Cut-Contours passen sich automatisch der Sticker-Form an:

### Reguläre Sticker (LOTO Points)
- Größe: 135mm × 35mm
- **Eckradius**: 60 Pixel ≈ 5.08mm
- Farbe: Gelb (#FFC000)
- Cut-Contour folgt den abgerundeten Ecken

### Count-Sticker
- Größe: 135mm × 25mm  
- **Eckradius**: 60 Pixel ≈ 5.08mm
- Farbe: Weiß mit roten Streifen
- Cut-Contour folgt den abgerundeten Ecken

## Verwendung

### 1. Sticker erstellen
- Sticker wie gewohnt in der App erstellen
- Zur Sammlung hinzufügen

### 2. PDF exportieren
- Menü: **Export → PDF Export** (oder `Ctrl+P`)
- Export-Ordner wählen
- PDF wird mit Cut Contours erstellt

### 3. Mimaki-Einstellungen

#### In FineCut/CorelDRAW:
1. PDF in FineCut öffnen
2. Cut Contour-Ebene sollte automatisch erkannt werden (Magenta)
3. Schnitteinstellungen prüfen:
   - **Spot Color**: CutContour / Magenta
   - **Schnittgeschwindigkeit**: Empfohlen 30 cm/s
   - **Schnittdruck**: Je nach Material (z.B. 80-120g für Vinyl)

#### Direkt am Mimaki CJV 30-60:
1. Datei an Drucker senden
2. Druckvorgang starten
3. Nach Druck erfolgt automatischer Schnitt entlang Magenta-Linien

## Anpassungen

### Bleed/Offset einstellen
Für einen Schnittrand außerhalb des Stickers `offset_mm` in `pdf_exporter.py` anpassen:

```python
# Beispiel: 1mm Bleed
draw_cut_contour(c, x_pt, y_pt, 
               st_w_mm * pt_per_mm_x, 
               st_h_mm * pt_per_mm_y,
               offset_mm=1.0,  # <-- Hier anpassen
               pt_per_mm=pt_per_mm_x,
               corner_radius_px=app.sticker_config.corner_radius,
               dpi=app.sticker_config.dpi)
```

### Eckradius ändern
Falls die Sticker-Ecken anders gerundet werden sollen, in `config.json` anpassen:

```json
{
  "sticker": {
    "corner_radius": 60,  // <-- In Pixel, hier anpassen
    ...
  },
  "count": {
    "corner_radius": 60,  // <-- Für Count-Sticker
    ...
  }
}
```

**Hinweis**: Die Cut-Contour übernimmt automatisch den Radius aus der Config!

### Andere Schnittplotter
Falls ein anderer Plotter verwendet wird:
- Spotfarbe in `draw_cut_contour()` anpassen
- Linienstärke ggf. ändern (`c.setLineWidth()`)

## Troubleshooting

### Cut Contour wird nicht erkannt
- **Lösung**: Prüfen ob Magenta-Spotfarbe aktiv ist
- PDF in Acrobat/Reader öffnen → Erweitert → Druckproduktion → Ausgabevorschau
- Magenta-Kanal sollte sichtbar sein

### Schnittlinien zu dick/dünn
- In `pdf_exporter.py` Linienstärke anpassen: `c.setLineWidth(0.1)` → z.B. `0.05` oder `0.2`

### Offset falsch
- `offset_mm` Parameter in allen `draw_cut_contour()` Aufrufen anpassen

## Beispiel-Workflow

1. **Sticker erstellen**: 10 Sticker in Sammlung
2. **PDF Export**: Eine Seite A4 mit Cut Contours
3. **Mimaki vorbereiten**: Material einlegen (z.B. Vinyl-Folie)
4. **Drucken**: PDF an Mimaki senden
5. **Automatisches Schneiden**: Nach Druck schneidet Mimaki entlang Magenta-Linien
6. **Fertig**: Sticker können ausgeklebt/verteilt werden

## Hinweise

- Cut Contours werden für **alle** Sticker-Typen erstellt:
  - ✅ Reguläre LOTO-Sticker (mit abgerundeten Ecken)
  - ✅ Count-Sticker (mit abgerundeten Ecken)
- Funktioniert in allen Export-Modi (Auto-Höhe, Paging, Single/Multi Count)
- **Abgerundete Ecken** werden automatisch aus `config.json` übernommen
- Radius wird automatisch von Pixel in mm und Points umgerechnet
- Keine manuelle Nachbearbeitung in Grafikprogrammen nötig
- Schnittlinien werden nicht gedruckt, nur vom Plotter verwendet

---

**Stand**: November 2025  
**Version**: 2.0 (mit abgerundeten Ecken)
