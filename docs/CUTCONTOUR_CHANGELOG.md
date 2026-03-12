# Cut Contour - Changelog

## Version 2.1 (November 2025)

### 🐛 Bugfix: Count-Header Cut-Contours fehlten

**Problem**: Rot-weiße Count-Sticker (Header im Multi-Mode) erhielten keine Cut-Contours, während gelbe LOTO-Sticker korrekt Konturen bekamen.

**Lösung**: Cut-Contour-Aufrufe für Count-Header hinzugefügt an zwei Stellen:
1. Auto-Höhe-Modus (Zeile 177)
2. Paging-Modus (Zeile 274)

**Ergebnis**: 
- ✅ Alle Count-Sticker bekommen jetzt Cut-Contours (5 verschiedene Positionen)
- ✅ Header-Sticker haben abgerundete Ecken wie reguläre Sticker
- ✅ Magenta-Spotfarbe für Mimaki-Erkennung

### Count-Sticker Cut-Contour Positionen (komplett)

1. ✅ **Count-Header (Multi-Mode, Auto-Höhe)** ← NEU in v2.1
2. ✅ **Count-Header (Multi-Mode, Paging)** ← NEU in v2.1  
3. ✅ Count-Sticker (Single-Mode, Auto-Höhe)
4. ✅ Count-Sticker (Paging, freie Fläche)
5. ✅ Count-Single-Sticker (Extra-Seiten)

## Version 2.0 (November 2025)

### ✨ Neue Features

#### 1. Abgerundete Ecken für Cut Contours
- **Vorher**: Rechteckige Schnittlinien mit scharfen Ecken
- **Jetzt**: Abgerundete Schnittlinien passend zur Sticker-Form

```
VORHER (V1.0):              JETZT (V2.0):
┌────────────────┐          ╭────────────────╮
│                │          │                │
│   STICKER      │    →     │   STICKER      │
│                │          │                │
└────────────────┘          ╰────────────────╯
  (eckig)                     (abgerundet)
```

#### 2. Automatische Radius-Übernahme
- Eckradius wird direkt aus `config.json` gelesen
- Separate Radien für:
  - Reguläre Sticker: `sticker.corner_radius` (60px)
  - Count-Sticker: `count.corner_radius` (60px)
- Automatische Umrechnung: Pixel → mm → Points

#### 3. Count-Sticker Cut Contours
- ✅ Count-Sticker erhalten ebenfalls Cut Contours
- ✅ Gleiche Magenta-Spotfarbe wie reguläre Sticker
- ✅ Abgerundete Ecken auch für Count-Sticker

### 🔧 Technische Änderungen

#### Funktion `draw_cut_contour()`
**Neue Parameter:**
```python
corner_radius_px=0   # Eckradius in Pixel (Standard: 0 = eckig)
dpi=300              # DPI für Umrechnung Pixel → mm
```

**Neue Logik:**
- Berechnung: `corner_radius_mm = corner_radius_px * (25.4 / dpi)`
- Umrechnung: `corner_radius_pt = corner_radius_mm * pt_per_mm`
- Verwendung: `c.roundRect()` statt `c.rect()` wenn `corner_radius_pt > 0`

#### Alle Export-Modi aktualisiert
1. **Auto-Höhe-Modus**
   - Reguläre Sticker: ✅ mit Radius
   - Count-Sticker: ✅ mit Radius

2. **Paging-Modus**
   - Reguläre Sticker: ✅ mit Radius
   - Count-Sticker (freie Fläche): ✅ mit Radius
   - Count-Single (Extra-Seiten): ✅ mit Radius

### 📊 Beispiel-Berechnungen

**Reguläre Sticker (config.json):**
```
corner_radius: 60px
dpi: 300
→ 60px * (25.4mm / 300) = 5.08mm
→ 5.08mm * (72pt / 25.4mm) = 14.41pt (abgerundet)
```

**Count-Sticker (config.json):**
```
corner_radius: 60px
dpi: 300
→ 60px * (25.4mm / 300) = 5.08mm
→ 5.08mm * (72pt / 25.4mm) = 14.41pt (abgerundet)
```

### 🎯 Vorteile

1. **Präziserer Schnitt**: Kontur folgt exakter Sticker-Form
2. **Weniger Verschnitt**: Keine überstehenden Ecken
3. **Professionelleres Ergebnis**: Perfekt gerundete Sticker-Kanten
4. **Automatische Anpassung**: Radius-Änderungen in `config.json` werden direkt übernommen
5. **Count-Sticker Support**: Vollständige Unterstützung für beide Sticker-Typen

### 📝 Migration von V1.0 zu V2.0

**Keine Änderungen nötig!** 
- Die Cut-Contours werden automatisch mit abgerundeten Ecken erstellt
- Alte PDFs (V1.0) können weiterhin verwendet werden
- Neue Exports nutzen automatisch die V2.0-Logik

**Optional:** 
- Eckradius in `config.json` anpassen für andere Rundungen
- `offset_mm` Parameter für Bleed-Rand nutzen

---

## Version 1.0 (November 2025)

### Initiale Features
- Magenta Cut Contours für Mimaki CJV 30-60
- Rechteckige Schnittlinien um Sticker
- Hairline-Linienstärke (0.1pt)
- Optionaler Bleed/Offset
- Support für alle Export-Modi

---

**Autor**: GitHub Copilot  
**Letzte Aktualisierung**: 26. November 2025
