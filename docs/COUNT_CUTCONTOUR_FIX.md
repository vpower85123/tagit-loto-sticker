# Count-Sticker Cut-Contour - Übersicht

## Problem gelöst ✅

**Vorher**: Rot-weiße Count-Sticker (Header im Multi-Mode) hatten keine Cut-Contour  
**Jetzt**: Alle Count-Sticker bekommen Cut-Contours mit abgerundeten Ecken!

## Count-Sticker Positionen mit Cut-Contours

### 1. Count-Header (Multi-Mode)
**Wann**: Export mit `count_mode = 'multi'` und `include_count_header = True`  
**Position**: Oben auf der Seite, vor den regulären Stickern  
**Inhalt**: "TOTAL COUNT OF LOTO POINTS – [Details]"

#### Auto-Höhe-Modus
```python
# Zeile 177 in pdf_exporter.py
draw_cut_contour(c, x_pt, y_pt,
               draw_w_mm * pt_per_mm_x,
               draw_h_mm * pt_per_mm_y,
               offset_mm=0.0,
               pt_per_mm=pt_per_mm_x,
               corner_radius_px=app.count_config.corner_radius,
               dpi=app.count_config.dpi)
```

#### Paging-Modus
```python
# Zeile 274 in pdf_exporter.py
draw_cut_contour(c, x_pt, y_pt,
               draw_w_mm * pt_per_mm_x,
               draw_h_mm * pt_per_mm_y,
               offset_mm=0.0,
               pt_per_mm=pt_per_mm_x,
               corner_radius_px=app.count_config.corner_radius,
               dpi=app.count_config.dpi)
```

### 2. Count-Sticker (Single-Mode, Auto-Höhe)
**Wann**: Export mit `count_mode = 'single'`  
**Position**: Unter den regulären Stickern auf derselben Seite

```python
# Zeile 226 in pdf_exporter.py
draw_cut_contour(c, x_pt, y_pt,
               ct_w_mm * pt_per_mm_x,
               ct_h_mm * pt_per_mm_y,
               offset_mm=0.0,
               pt_per_mm=pt_per_mm_x,
               corner_radius_px=app.count_config.corner_radius,
               dpi=app.count_config.dpi)
```

### 3. Count-Sticker (Paging, freie Fläche)
**Wann**: Freie Fläche am Ende einer Seite  
**Position**: Unter den regulären Stickern, wenn Platz ist

```python
# Zeile 344 in pdf_exporter.py
draw_cut_contour(c, x_pt, y_pt,
               ct_w_mm * pt_per_mm_x,
               ct_h_mm * pt_per_mm_y,
               offset_mm=0.0,
               pt_per_mm=pt_per_mm_x,
               corner_radius_px=app.count_config.corner_radius,
               dpi=app.count_config.dpi)
```

### 4. Count-Single-Sticker (Extra-Seiten)
**Wann**: Wenn Count-Sticker nicht auf reguläre Seiten passen  
**Position**: Eigene dedizierte Seiten

```python
# Zeile 379 in pdf_exporter.py
draw_cut_contour(c, x_pt, y_pt,
               ct_w_mm * pt_per_mm_x,
               ct_h_mm * pt_per_mm_y,
               offset_mm=0.0,
               pt_per_mm=pt_per_mm_x,
               corner_radius_px=app.count_config.corner_radius,
               dpi=app.count_config.dpi)
```

## Eigenschaften aller Count-Sticker Cut-Contours

- ✅ **Magenta Spotfarbe** (C=0, M=100, Y=0, K=0)
- ✅ **Hairline-Linienstärke** (0.1 Points)
- ✅ **Abgerundete Ecken** (60px Radius ≈ 5.08mm)
- ✅ **Automatische Radius-Übernahme** aus `config.json`
- ✅ **Mimaki CJV 30-60 kompatibel**

## Visueller Vergleich

```
ROT-WEISSER COUNT-STICKER (Multi-Mode Header):

VORHER:                           JETZT:
┌──────────────────────┐          ╭──────────────────────╮
│ TOTAL COUNT: 5       │          │ TOTAL COUNT: 5       │
│ (rot-weiß gestreift) │    →     │ (rot-weiß gestreift) │
└──────────────────────┘          ╰──────────────────────╯
   (KEINE Kontur!)                  (MIT Magenta-Kontur!)
```

## Test-Szenario

1. Erstelle mehrere LOTO-Sticker (z.B. 5 Stück)
2. Exportiere als PDF
3. **Erwartetes Ergebnis**:
   - ✅ Gelbe LOTO-Sticker: Magenta Cut-Contour mit abgerundeten Ecken
   - ✅ Rot-weißer Count-Header: Magenta Cut-Contour mit abgerundeten Ecken
   - ✅ Alle Konturen im PDF sichtbar (Magenta-Kanal)
   - ✅ Mimaki erkennt beide Sticker-Typen zum Schneiden

---

**Gelöst**: 26. November 2025  
**Version**: 2.1 (Count-Header Cut-Contours hinzugefügt)
