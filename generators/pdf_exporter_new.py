"""
Neuer PDF-Exporter mit individueller Sticker-Platzierung und Kollisionsprüfung
"""
import math
import logging
import re
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from PIL import Image

logger = logging.getLogger(__name__)

try:
    from reportlab.pdfgen import canvas as pdf_canvas
    from reportlab.lib.utils import ImageReader
    from reportlab.lib.colors import CMYKColor, PCMYKColor, CMYKColorSep, PCMYKColorSep
except Exception:
    pdf_canvas = None
    ImageReader = None
    CMYKColor = None


class StickerBox:
    """Repräsentiert einen platzierten Sticker mit Position und Dimensionen"""
    def __init__(self, x, y, width, height, image, dpi, corner_radius):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.image = image
        self.dpi = dpi
        self.corner_radius = corner_radius
    
    def collides_with(self, other, gap_mm=0):
        """Prüft ob dieser Sticker mit einem anderen kollidiert (inkl. Gap)"""
        return not (self.x + self.width + gap_mm <= other.x or
                   other.x + other.width + gap_mm <= self.x or
                   self.y + self.height + gap_mm <= other.y or
                   other.y + other.height + gap_mm <= self.y)
    
    def fits_on_page(self, page_width, page_height, margin):
        """Prüft ob Sticker auf Seite passt (inkl. Margins)"""
        return (self.x >= margin and
                self.y >= margin and
                self.x + self.width <= page_width - margin and
                self.y + self.height <= page_height - margin)


class PageLayout:
    """Verwaltet Sticker-Platzierung auf einer Seite"""
    def __init__(self, width_mm, height_mm, margin_mm, gap_mm):
        self.width_mm = width_mm
        self.height_mm = height_mm
        self.margin_mm = margin_mm
        self.gap_mm = gap_mm
        self.placed_boxes = []
        self.current_y = margin_mm
        self.loto_sticker_width = 0
        self.loto_sticker_height = 0
    
    def get_actual_height(self):
        """Berechnet die tatsächlich benötigte Höhe basierend auf platzierten Stickern"""
        if not self.placed_boxes:
            return 2 * self.margin_mm  # Minimum
        
        # Finde den untersten Punkt
        max_bottom = 0
        for box in self.placed_boxes:
            bottom = box.y + box.height
            if bottom > max_bottom:
                max_bottom = bottom
        
        # Höhe = unterster Punkt + unterer Rand
        actual_height = max_bottom + self.margin_mm
        return actual_height
    
    def get_actual_width(self):
        """Berechnet die tatsächlich benötigte Breite basierend auf platzierten Stickern"""
        if not self.placed_boxes:
            return 2 * self.margin_mm
        
        max_right = 0
        for box in self.placed_boxes:
            right = box.x + box.width
            if right > max_right:
                max_right = right
        
        return max_right + self.margin_mm
    
    def can_place(self, x, y, width, height):
        """Prüft ob ein Sticker an Position (x,y) platziert werden kann"""
        test_box = StickerBox(x, y, width, height, None, 0, 0)
        
        # Prüfe Seitengrenzen
        if not test_box.fits_on_page(self.width_mm, self.height_mm, self.margin_mm):
            return False
        
        # Prüfe Kollisionen mit bereits platzierten Stickern
        for box in self.placed_boxes:
            if test_box.collides_with(box, self.gap_mm):
                return False
        
        return True
    
    def find_next_position(self, sticker_width, sticker_height):
        """Findet die nächste freie Position für einen Sticker"""
        # Strategie: Von links nach rechts, von oben nach unten
        y = self.margin_mm
        
        while y + sticker_height <= self.height_mm - self.margin_mm:
            x = self.margin_mm
            
            while x + sticker_width <= self.width_mm - self.margin_mm:
                if self.can_place(x, y, sticker_width, sticker_height):
                    return (x, y, True)  # Position gefunden
                
                # Nächste X-Position: Nach dem nächsten Hindernis
                x += self.gap_mm + sticker_width
            
            # Nächste Y-Position
            y += self.gap_mm + sticker_height
        
        return (0, 0, False)  # Kein Platz gefunden
    
    def place_sticker(self, image, width_mm, height_mm, dpi, corner_radius, center_horizontal=False):
        """Platziert einen Sticker und gibt Position zurück"""
        if center_horizontal:
            # Zentriere Sticker horizontal
            x = (self.width_mm - width_mm) / 2
            y = self.current_y
            
            # Prüfe ob Position gültig ist
            if not self.can_place(x, y, width_mm, height_mm):
                return None
            
            box = StickerBox(x, y, width_mm, height_mm, image, dpi, corner_radius)
            self.placed_boxes.append(box)
            
            # Aktualisiere current_y für nächste Zeile
            self.current_y = y + height_mm + self.gap_mm
            
            logger.info(f"✓ Sticker ZENTRIERT platziert bei x={x:.1f}mm, y={y:.1f}mm, w={width_mm:.1f}mm, h={height_mm:.1f}mm")
            return box
        else:
            x, y, success = self.find_next_position(width_mm, height_mm)
            
            if not success:
                return None
        
            box = StickerBox(x, y, width_mm, height_mm, image, dpi, corner_radius)
            self.placed_boxes.append(box)
            
            logger.info(f"✓ Sticker platziert bei x={x:.1f}mm, y={y:.1f}mm, w={width_mm:.1f}mm, h={height_mm:.1f}mm")
            return box
    
    def place_loto_grid_row(self, stickers_data, start_idx, max_count):
        """Platziert eine zentrierte Reihe von LOTO-Stickern"""
        if start_idx >= len(stickers_data):
            return 0
        
        # Hole erste LOTO-Sticker Dimensionen (alle gleich)
        first_sticker = stickers_data[start_idx]
        sticker_w = first_sticker['width_mm']
        sticker_h = first_sticker['height_mm']
        
        # Berechne wie viele in diese Reihe passen (dynamisch basierend auf Seitenbreite)
        available_width = self.width_mm - 2 * self.margin_mm
        cols_possible = max(1, int((available_width + self.gap_mm) / (sticker_w + self.gap_mm)))
        cols = min(cols_possible, max_count, len(stickers_data) - start_idx)
        
        if cols <= 0:
            return 0
        
        # Prüfe ob mindestens 1 Sticker passt
        if sticker_w > available_width:
            logger.warning(f"Sticker zu breit ({sticker_w:.1f}mm) für Seite ({available_width:.1f}mm verfügbar)")
            return 0
        
        # Berechne Gesamtbreite dieser Reihe
        row_width = cols * sticker_w + (cols - 1) * self.gap_mm
        
        # Zentriere die Reihe horizontal
        start_x = (self.width_mm - row_width) / 2
        y = self.current_y
        
        # Prüfe ob Reihe auf Seite passt (Höhe)
        if y + sticker_h > self.height_mm - self.margin_mm:
            return 0  # Keine Höhe mehr
        
        logger.info(f"Zentrierte Reihe: {cols} Spalten, Breite={row_width:.1f}mm, Start-X={start_x:.1f}mm, Y={y:.1f}mm")
        
        # Platziere Sticker in dieser Reihe
        placed = 0
        for i in range(cols):
            idx = start_idx + i
            if idx >= len(stickers_data):
                break
            
            sticker = stickers_data[idx]
            x = start_x + i * (sticker_w + self.gap_mm)
            
            # Prüfe ob Position gültig ist
            if not self.can_place(x, y, sticker_w, sticker_h):
                logger.warning(f"Sticker #{idx+1} kollidiert bei x={x:.1f}mm, y={y:.1f}mm")
                break
            
            box = StickerBox(x, y, sticker_w, sticker_h, 
                           sticker['image'], sticker['dpi'], sticker['corner_radius'])
            self.placed_boxes.append(box)
            placed += 1
            
            logger.info(f"✓ LOTO #{idx+1} bei x={x:.1f}mm, y={y:.1f}mm (Spalte {i+1}/{cols})")
        
        # Aktualisiere current_y für nächste Zeile
        if placed > 0:
            self.current_y = y + sticker_h + self.gap_mm
        
        return placed
    
    def is_full(self, sticker_width, sticker_height):
        """Prüft ob Seite voll ist (kein Platz mehr für weiteren Sticker)"""
        _, _, success = self.find_next_position(sticker_width, sticker_height)
        return not success


def draw_cut_contour(c, x_pt, y_pt, width_pt, height_pt, offset_mm, pt_per_mm, corner_radius_px, dpi):
    """Zeichnet CutContour mit Magenta Spot Color für RasterLink/Mimaki"""
    # Mimaki RasterLink erwartet: Spot Color "CutContour" oder "Cut" in Magenta
    # WICHTIG: CMYKColorSep statt CMYKColor für echte Separation
    try:
        # Versuche CMYKColorSep (bessere Separation für RasterLink)
        magenta = CMYKColorSep(0, 1, 0, 0, spotName='CutContour')
    except Exception:
        # Fallback zu CMYKColor
        magenta = CMYKColor(0, 1, 0, 0, spotName='CutContour')
    
    offset_pt = offset_mm * pt_per_mm
    corner_radius_pt = corner_radius_px * 25.4 / dpi * pt_per_mm if corner_radius_px > 0 else 0
    
    x1 = x_pt - offset_pt
    y1 = y_pt - offset_pt
    rect_width = width_pt + 2 * offset_pt
    rect_height = height_pt + 2 * offset_pt
    
    # Setze Stroke Color
    c.setStrokeColor(magenta)
    
    # WICHTIG: Hairline (0) für saubere Schnittpfade
    c.setLineWidth(0)
    c.setDash([])
    
    # Overprint MUSS aktiviert sein für RasterLink
    try:
        c.setOverprintStroke(1)  # Stroke overprint AN
        c.setOverprintFill(0)    # Fill overprint AUS
    except AttributeError:
        logger.warning("Overprint nicht verfügbar - CutContour könnte in RasterLink nicht erkannt werden")
    
    # Zeichne Pfad
    if corner_radius_pt > 0:
        c.roundRect(x1, y1, rect_width, rect_height, corner_radius_pt, stroke=1, fill=0)
    else:
        c.rect(x1, y1, rect_width, rect_height, stroke=1, fill=0)
    
    logger.debug(f"CutContour gezeichnet: {rect_width:.1f}x{rect_height:.1f}pt, radius={corner_radius_pt:.1f}pt")


def opaque_rgb(pil_img: Image.Image) -> Image.Image:
    """Konvertiert Bild zu RGB ohne Transparenz"""
    try:
        rgba = pil_img.convert('RGBA')
        bg = Image.new('RGBA', rgba.size, (255, 255, 255, 255))
        bg.alpha_composite(rgba)
        return bg.convert('RGB')
    except Exception:
        return pil_img.convert('RGB')


def export_pdf_new(app):
    """Neue PDF-Export Logik mit fortlaufender Sticker-Platzierung
    
    Layout-Regeln:
    - Rand: 7mm außen
    - Abstand zwischen Objekten: 5mm  
    - Count-Multi wird wie normaler Sticker behandelt (oben links zuerst)
    - Alle Sticker fortlaufend von links nach rechts, oben nach unten
    - Top-Align innerhalb jeder Reihe
    - Proportionen bleiben erhalten (keine Skalierung)
    """
    
    if not app.collection:
        QMessageBox.information(app, "Info", "Keine Sticker zum Exportieren.")
        return
    
    if pdf_canvas is None:
        QMessageBox.critical(app, "Fehler", "ReportLab nicht installiert. 'pip install reportlab'")
        return
    
    out_dir = QFileDialog.getExistingDirectory(app, "Export-Ordner wählen")
    if not out_dir:
        return
    
    try:
        # === SCHRITT 1: Sammle alle Sticker ===
        logger.info("=== PDF Export START ===")
        
        count_mode = getattr(app.export_config, 'export_mode', 'multi')
        count_print_copies = max(1, int(getattr(app.count_config, 'count_print_copies', 1)))
        
        # Extrahiere Bilder aus Collection
        def extract_image(item):
            if len(item) >= 7:
                return item[6] if item[6] else item[0]
            return item[0]
        
        # Helper: Prüfe ob Item Count-Multi ist
        def is_count_multi(item):
            if len(item) < 6:
                return False
            marker = item[5]
            if isinstance(marker, dict):
                return marker.get("type") == "count_multi"
            return marker == "count_multi"

        def is_count_single(item):
            if len(item) < 6:
                return False
            marker = item[5]
            if isinstance(marker, dict):
                return marker.get("type") == "count_single"
            if marker == "count_single":
                return True
            return str(item[1]).upper() == "COUNT_SINGLE"

        def _safe_filename(text: str) -> str:
            cleaned = re.sub(r"[\\/:*?\"<>|]", "_", text)
            cleaned = re.sub(r"\s+", "_", cleaned).strip("_")
            cleaned = re.sub(r"_+", "_", cleaned)
            return cleaned or "export"

        def _derive_export_basename() -> str:
            sources = getattr(app, "collection_export_sources", None)
            regular_count = sum(
                1 for item in app.collection
                if len(item) > 3 and not is_count_multi(item) and not is_count_single(item)
            )

            if sources:
                src_list = sorted([s for s in sources if s])
                if len(src_list) == 1:
                    base_src = src_list[0]
                elif len(src_list) <= 3:
                    base_src = "+".join(src_list)
                else:
                    base_src = f"{len(src_list)}_Gruppen"
                return f"{_safe_filename(base_src)}_{regular_count}items"

            names = []
            for item in app.collection:
                if is_count_multi(item) or is_count_single(item):
                    continue
                if len(item) > 3 and item[3]:
                    names.append(str(item[3]))
            if not names:
                return "stickers_export"

            # Gemeinsamen Präfix versuchen
            common = names[0]
            for n in names[1:]:
                common = common[:len(common)]
                while common and not n.upper().startswith(common.upper()):
                    common = common[:-1]
                if not common:
                    break

            if common and len(common) >= 4:
                # Auf sinnvolle Trennzeichen schneiden
                cut = max(common.rfind("."), common.rfind("-"), common.rfind(" "))
                if cut >= 3:
                    common = common[:cut]
                base = _safe_filename(common)
            else:
                # Fallback: erste 3 Tokens
                tokens = []
                for n in names:
                    parts = re.split(r"[\.\-\s]+", n)
                    for p in parts:
                        p = p.strip()
                        if p and p not in tokens:
                            tokens.append(p)
                        if len(tokens) >= 3:
                            break
                    if len(tokens) >= 3:
                        break
                base = _safe_filename("_".join(tokens) if tokens else "stickers_export")

            return f"{base}_{len(names)}items"
        
        # Sammle Sticker-Daten
        stickers_to_place = []
        
        # Debug: Zeige Collection-Inhalt
        logger.info(f"Collection hat {len(app.collection)} Items")
        for i, item in enumerate(app.collection):
            marker = item[5] if len(item) >= 6 else "?"
            symbol_type = item[1] if len(item) > 1 else "?"
            logger.info(f"  Item {i}: symbol_type={symbol_type}, marker={marker}, is_count_multi={is_count_multi(item)}")
        
        # Count-Multi Sticker (falls vorhanden) - IMMER suchen, nicht nur bei mode=='multi'
        count_found = False
        for item in app.collection:
            if is_count_multi(item):
                img = extract_image(item)
                if img:
                    # Extrahiere per-Sticker Kopienanzahl (neu) oder fallback zu global
                    marker = item[5] if len(item) >= 6 else {}
                    item_copies = marker.get("copies", count_print_copies) if isinstance(marker, dict) else count_print_copies
                    
                    # Immer tatsächliche Bildgröße verwenden, damit Export den Count-Settings entspricht
                    actual_width_mm = img.width * 25.4 / app.count_config.dpi
                    actual_height_mm = img.height * 25.4 / app.count_config.dpi
                    logger.info(
                        f"Count-Multi Bildgröße: {img.width}x{img.height}px → "
                        f"{actual_width_mm:.1f}x{actual_height_mm:.1f}mm (Kopien: {item_copies})"
                    )
                    
                    for copy_idx in range(item_copies):
                        stickers_to_place.append({
                            'image': img,
                            'width_mm': actual_width_mm,
                            'height_mm': actual_height_mm,
                            'dpi': app.count_config.dpi,
                            'corner_radius': app.count_config.corner_radius,
                            'type': 'count_multi'
                        })
                        logger.info(
                            f"✅ Count-Multi hinzugefügt ({copy_idx + 1}/{item_copies}): "
                            f"{actual_width_mm:.1f}x{actual_height_mm:.1f}mm"
                        )
                    count_found = True
        
        if not count_found:
            logger.info("⚠️ Kein Count-Multi Sticker in der Collection gefunden")
        
        # Prüfe ob Single-LOTO Modus (dann Count-Single mit exportieren)
        is_single_mode = count_mode == 'single'
        logger.info(f"Export-Modus: {count_mode} (Single-Mode: {is_single_mode})")
        
        # LOTO Sticker und Count-Single (im Single-Mode)
        for item in app.collection:
            if not is_count_multi(item):  # Alle außer Count-Multi
                # Count-Single nur im Multi-Mode überspringen
                if is_count_single(item):
                    if not is_single_mode:
                        continue  # Skip Count-Single nur im Multi-Mode
                    # Im Single-Mode: Count-Single mit exportieren (mit Count-Dimensionen)
                    img = extract_image(item)
                    if img:
                        # Extrahiere per-Sticker Kopienanzahl (neu) oder fallback zu global
                        marker = item[5] if len(item) >= 6 else {}
                        item_copies = marker.get("copies", count_print_copies) if isinstance(marker, dict) else count_print_copies
                        
                        # Count-Single bekommt die COUNT-Sticker Dimensionen
                        actual_width_mm = img.width * 25.4 / app.count_config.dpi
                        actual_height_mm = img.height * 25.4 / app.count_config.dpi
                        stickers_to_place.append({
                            'image': img,
                            'width_mm': actual_width_mm,
                            'height_mm': actual_height_mm,
                            'dpi': app.count_config.dpi,
                            'corner_radius': app.count_config.corner_radius,
                            'type': 'count_single',
                            'copies': item_copies,
                        })
                        logger.info(
                            f"✅ Count-Single hinzugefügt: {actual_width_mm:.1f}x{actual_height_mm:.1f}mm "
                            f"(x{item_copies})"
                        )
                    continue
                
                # Normaler LOTO Sticker
                img = extract_image(item)
                if img:
                    stickers_to_place.append({
                        'image': img,
                        'width_mm': app.sticker_config.width_mm,
                        'height_mm': app.sticker_config.height_mm,
                        'dpi': app.sticker_config.dpi,
                        'corner_radius': app.sticker_config.corner_radius,
                        'type': 'loto'
                    })
        
        logger.info(f"Gesamt: {len(stickers_to_place)} Sticker zum Platzieren")
        
        if not stickers_to_place:
            QMessageBox.information(app, "Info", "Keine Sticker zum Exportieren.")
            return
        
        # Trenne Count-Sticker von LOTO-Stickern
        count_multi_stickers = []
        count_single_stickers = []
        loto_stickers = []
        
        for sticker in stickers_to_place:
            if sticker['type'] == 'count_multi':
                count_multi_stickers.append(sticker)
            elif sticker['type'] == 'count_single':
                count_single_stickers.append(sticker)
            else:
                loto_stickers.append(sticker)
        
        logger.info(
            f"Count-Multi: {len(count_multi_stickers)}, "
            f"Count-Single: {len(count_single_stickers)}, "
            f"LOTO-Sticker: {len(loto_stickers)}"
        )
        
        # === SCHRITT 2: Konfiguration aus App-Einstellungen ===
        roll_mode = getattr(app.export_config, 'roll_mode', False)
        roll_width_mm = getattr(app.export_config, 'roll_width_mm', 0.0)
        sheet_w_mm = roll_width_mm if roll_mode and roll_width_mm > 0 else app.export_config.sheet_width_mm
        sheet_h_mm = app.export_config.sheet_height_mm
        margin_mm = app.export_config.margin_mm  # Rand (z.B. 7mm)
        gap_mm = app.export_config.gap_mm        # Abstand (z.B. 5mm)
        
        # Im Rollenmodus: Maximal 600mm pro Stück
        max_roll_length_mm = 600.0 if roll_mode else sheet_h_mm
        
        # === MATHEMATISCHE VARIABLEN (Algorithmus) ===
        W_total = sheet_w_mm - 2 * margin_mm  # Verfügbare Breite
        G = gap_mm                             # Gap zwischen Objekten
        
        logger.info(f"=== LAYOUT-ALGORITHMUS ===")
        logger.info(f"W_total (verfügbare Breite) = {sheet_w_mm:.2f} - 2×{margin_mm:.2f} = {W_total:.2f}mm")
        logger.info(f"G (Gap) = {G:.2f}mm")
        logger.info(f"Rand = {margin_mm:.2f}mm")
        
        # === SCHRITT 1: ORIENTIERUNG - Logik wie in Vorschau (DimensionsWidget) ===
        # Teste beide Orientierungen und wähle die mit MEHR Stickern (Spalten × Reihen)
        # Im Single-Mode: KEINE Rotation, damit LOTO + Count-Single als Paare untereinander passen
        H_total = max_roll_length_mm - 2 * margin_mm  # Verfügbare Höhe
        
        if is_single_mode:
            use_rotation = False
            logger.info(f"Single-LOTO Modus: Rotation DEAKTIVIERT (Paare untereinander)")
        elif loto_stickers:
            base_w = loto_stickers[0]['width_mm']  # Original z.B. 85mm
            base_h = loto_stickers[0]['height_mm'] # Original z.B. 25mm
            
            # Berechne Anzahl Sticker in beiden Orientierungen (wie Vorschau)
            # Normal (nicht rotiert)
            cols_normal = max(1, int((W_total + G) / (base_w + G)))
            rows_normal = max(1, int((H_total + G) / (base_h + G)))
            total_normal = cols_normal * rows_normal
            
            # Rotiert (90°)
            cols_rotated = max(1, int((W_total + G) / (base_h + G)))
            rows_rotated = max(1, int((H_total + G) / (base_w + G)))
            total_rotated = cols_rotated * rows_rotated
            
            # Wähle Orientierung mit MEHR Stickern (wie Vorschau)
            use_rotation = total_rotated > total_normal
            
            logger.info(f"LOTO-Sticker Original: {base_w:.1f}x{base_h:.1f}mm")
            logger.info(f"Normal: {cols_normal}×{rows_normal}={total_normal} Sticker | Rotiert: {cols_rotated}×{rows_rotated}={total_rotated} Sticker")
            logger.info(f"→ Rotation: {'JA' if use_rotation else 'NEIN'} (mehr Sticker)")
        else:
            use_rotation = False
        
        # === SCHRITT 3: Platzierung mit Fließtext-Prinzip ===
        # Alle Objekte werden gleichberechtigt von links nach rechts platziert
        # Count-Multi ist O_1 (erstes Objekt), dann folgen E1, E2, E3...
        
        pages = []
        current_page = PageLayout(sheet_w_mm, max_roll_length_mm, margin_mm, gap_mm)
        
        # === Sammle ALLE Objekte (O_1, O_2, ... O_n) ===
        all_objects = []
        
        # O_1: Count-Multi als erstes Objekt
        for count_idx, count_multi_sticker in enumerate(count_multi_stickers, start=1):
            count_w = count_multi_sticker['width_mm']
            count_h = count_multi_sticker['height_mm']
            count_img = count_multi_sticker['image']

            # Rotiere Count-Multi wenn use_rotation aktiv oder wenn breiter als W_total
            if use_rotation or (count_w > W_total and count_h <= W_total):
                count_img = count_img.rotate(90, expand=True)
                count_w, count_h = count_h, count_w
                logger.info(f"Count-Multi {count_idx} rotiert auf {count_w:.1f}x{count_h:.1f}mm")

            obj_num = len(all_objects) + 1
            all_objects.append({
                'image': count_img,
                'width_mm': count_w,
                'height_mm': count_h,
                'dpi': count_multi_sticker['dpi'],
                'corner_radius': count_multi_sticker['corner_radius'],
                'name': f'O_{obj_num} (Count-Multi {count_idx})'
            })
            logger.info(f"O_{obj_num} (Count-Multi {count_idx}): {count_w:.1f}x{count_h:.1f}mm")
        
        # O_2 bis O_n: LOTO-Sticker (im Querformat wenn use_rotation=True oder wenn nötig)
        # Im Single-Mode: LOTO + Count-Single paarweise einfügen
        count_single_idx = 0
        for i, sticker in enumerate(loto_stickers):
            img = sticker['image']
            w_mm = sticker['width_mm']
            h_mm = sticker['height_mm']
            
            if use_rotation:
                img = img.rotate(90, expand=True)
                w_mm, h_mm = h_mm, w_mm  # 135x35 → 35x135
            
            # Rotiere LOTO-Sticker wenn breiter als verfügbare Breite (und Höhe passt rotiert)
            if w_mm > W_total and h_mm <= W_total:
                img = img.rotate(90, expand=True)
                w_mm, h_mm = h_mm, w_mm
                logger.info(f"LOTO E{i+1} rotiert auf {w_mm:.1f}x{h_mm:.1f}mm (passt in W_total={W_total:.1f}mm)")
            
            obj_num = len(all_objects) + 1
            all_objects.append({
                'image': img,
                'width_mm': w_mm,
                'height_mm': h_mm,
                'dpi': sticker['dpi'],
                'corner_radius': sticker['corner_radius'],
                'name': f'O_{obj_num} (LOTO E{i+1})'
            })
            
            # Im Single-Mode: Füge zugehörigen Count-Single direkt danach ein
            if is_single_mode and count_single_idx < len(count_single_stickers):
                cs = count_single_stickers[count_single_idx]
                cs_img = cs['image']
                cs_w = cs['width_mm']
                cs_h = cs['height_mm']
                
                # Rotiere Count-Single wenn use_rotation aktiv oder wenn breiter als verfügbare Breite
                if use_rotation or (cs_w > W_total and cs_h <= W_total):
                    cs_img = cs_img.rotate(90, expand=True)
                    cs_w, cs_h = cs_h, cs_w
                    logger.info(f"Count-Single {count_single_idx+1} rotiert auf {cs_w:.1f}x{cs_h:.1f}mm")
                
                obj_num = len(all_objects) + 1
                all_objects.append({
                    'image': cs_img,
                    'width_mm': cs_w,
                    'height_mm': cs_h,
                    'dpi': cs['dpi'],
                    'corner_radius': cs['corner_radius'],
                    'name': f'O_{obj_num} (Count-Single {count_single_idx+1})'
                })
                logger.info(f"Count-Single {count_single_idx+1} hinzugefügt: {cs_w:.1f}x{cs_h:.1f}mm")
                count_single_idx += 1
        
        logger.info(f"Gesamt: {len(all_objects)} Objekte")
        if use_rotation and loto_stickers:
            logger.info(f"LOTO-Sticker: {loto_stickers[0]['height_mm']:.1f}x{loto_stickers[0]['width_mm']:.1f}mm (Querformat)")
        
        # === SCHRITT 2 & 3: Reihenbildung und Prüfung ===
        # Im Single-Mode: Spezielle Paar-Platzierung (LOTO + Count-Single untereinander als Block)
        if is_single_mode and count_single_stickers:
            logger.info(f"=== SINGLE-MODE PAAR-PLATZIERUNG ===")
            
            # Erstelle Paare: LOTO + Count-Single als Blöcke
            pairs = []
            for i, sticker in enumerate(loto_stickers):
                loto_img = sticker['image']
                loto_w = sticker['width_mm']
                loto_h = sticker['height_mm']
                
                # Rotiere LOTO wenn use_rotation aktiv
                if use_rotation:
                    loto_img = loto_img.rotate(90, expand=True)
                    loto_w, loto_h = loto_h, loto_w
                
                # Zugehöriger Count-Single
                if i < len(count_single_stickers):
                    cs = count_single_stickers[i]
                    cs_img = cs['image']
                    cs_w = cs['width_mm']
                    cs_h = cs['height_mm']
                    # Rotiere Count-Single wenn use_rotation aktiv
                    if use_rotation:
                        cs_img = cs_img.rotate(90, expand=True)
                        cs_w, cs_h = cs_h, cs_w
                else:
                    cs = None
                    cs_img = None
                    cs_w = 0
                    cs_h = 0
                
                # Block-Dimensionen: Breite = max(LOTO, Count), Höhe = LOTO + Gap + Count
                block_w = max(loto_w, cs_w) if cs else loto_w
                block_h = loto_h + (gap_mm + cs_h if cs else 0)
                
                pairs.append({
                    'loto_img': loto_img, 'loto_w': loto_w, 'loto_h': loto_h,
                    'cs_img': cs_img, 'cs_w': cs_w, 'cs_h': cs_h,
                    'cs_copies': (cs.get('copies', 1) if cs else 0),
                    'block_w': block_w, 'block_h': block_h,
                    'dpi': sticker['dpi'], 'corner_radius': sticker['corner_radius'],
                    'cs_dpi': cs['dpi'] if cs else 0, 'cs_corner_radius': cs['corner_radius'] if cs else 0
                })

                if cs:
                    cs_copies = max(1, int(cs.get('copies', 1)))
                    pairs[-1]['cs_copies'] = cs_copies
                    pairs[-1]['block_h'] = loto_h + cs_copies * (gap_mm + cs_h)
            
            # Platziere Paare als Blöcke
            X = margin_mm
            Y = margin_mm
            row_height = 0
            
            for i, pair in enumerate(pairs):
                block_w = pair['block_w']
                block_h = pair['block_h']
                
                # Zeilenumbruch wenn Block nicht passt
                if X + block_w > sheet_w_mm - margin_mm:
                    X = margin_mm
                    Y = Y + row_height + gap_mm
                    row_height = 0
                    
                    # Neue Seite wenn nötig
                    if Y + block_h > max_roll_length_mm - margin_mm:
                        logger.info(f"📄 Seite voll bei Y={Y:.1f}mm → neue Seite")
                        pages.append(current_page)
                        current_page = PageLayout(sheet_w_mm, max_roll_length_mm, margin_mm, gap_mm)
                        X = margin_mm
                        Y = margin_mm
                        row_height = 0
                
                # Platziere LOTO (oben im Block)
                loto_box = StickerBox(X, Y, pair['loto_w'], pair['loto_h'], 
                                     pair['loto_img'], pair['dpi'], pair['corner_radius'])
                current_page.placed_boxes.append(loto_box)
                logger.info(f"✓ LOTO {i+1} bei X={X:.1f}mm, Y={Y:.1f}mm ({pair['loto_w']:.1f}x{pair['loto_h']:.1f}mm)")
                
                # Platziere Count-Single(s) unter LOTO
                if pair['cs_img']:
                    cs_copies = max(1, int(pair.get('cs_copies', 1)))
                    for cs_copy_idx in range(cs_copies):
                        cs_y = Y + pair['loto_h'] + gap_mm + cs_copy_idx * (pair['cs_h'] + gap_mm)
                        cs_box = StickerBox(X, cs_y, pair['cs_w'], pair['cs_h'],
                                           pair['cs_img'], pair['cs_dpi'], pair['cs_corner_radius'])
                        current_page.placed_boxes.append(cs_box)
                        logger.info(
                            f"✓ Count-Single {i+1} ({cs_copy_idx + 1}/{cs_copies}) "
                            f"bei X={X:.1f}mm, Y={cs_y:.1f}mm "
                            f"({pair['cs_w']:.1f}x{pair['cs_h']:.1f}mm)"
                        )
                
                # Update für nächsten Block
                X = X + block_w + gap_mm
                row_height = max(row_height, block_h)
            
            # Update current_y für PageLayout
            current_page.current_y = Y + row_height + margin_mm
            
        else:
            # Standard-Platzierung (Multi-Mode) - ZENTRIERT wie in Vorschau
            # Berechne Grid-Zentrierung wie in DimensionsWidget._calculate_optimal_layout
            
            # Trenne Count-Multi von LOTO-Stickern für separate Behandlung
            count_objects = []
            loto_objects = []
            for obj in all_objects:
                if 'Count' in obj['name']:
                    count_objects.append(obj)
                else:
                    loto_objects.append(obj)
            
            # Verfügbare Fläche
            H_available = max_roll_length_mm - 2 * margin_mm
            
            # LOTO-Sticker ZUERST platzieren, Count-Multi DANACH (spart Druckfläche)
            loto_start_y = margin_mm
            
            # LOTO-Sticker in zentriertem Grid platzieren
            if loto_objects:
                sticker_w = loto_objects[0]['width_mm']
                sticker_h = loto_objects[0]['height_mm']
                
                # Berechne wie viele Spalten und Reihen passen
                cols = max(1, int((W_total + G) / (sticker_w + G)))
                
                # Berechne Grid-Größe für diese Seite
                grid_width = cols * sticker_w + (cols - 1) * G
                
                # Zentriere nur horizontal (vertikal oben ausrichten wie in Vorschau)
                start_x = margin_mm + (W_total - grid_width) / 2
                
                logger.info(f"LOTO Grid: {cols} Spalten, start_x={start_x:.1f}mm, start_y={loto_start_y:.1f}mm")
                
                # Platziere LOTO-Sticker zeilenweise
                obj_idx = 0
                Y = loto_start_y
                
                while obj_idx < len(loto_objects):
                    # Neue Reihe
                    row_y = Y
                    
                    # Prüfe ob Reihe auf Seite passt
                    if row_y + sticker_h > max_roll_length_mm - margin_mm:
                        # Neue Seite
                        logger.info(f"📄 Seite voll bei Y={row_y:.1f}mm → neue Seite")
                        pages.append(current_page)
                        current_page = PageLayout(sheet_w_mm, max_roll_length_mm, margin_mm, gap_mm)
                        Y = margin_mm
                        row_y = Y
                    
                    # Platziere Sticker in dieser Reihe (alle Spalten)
                    for col in range(cols):
                        if obj_idx >= len(loto_objects):
                            break
                        
                        obj = loto_objects[obj_idx]
                        X = start_x + col * (sticker_w + G)
                        
                        box = StickerBox(X, row_y, sticker_w, sticker_h,
                                       obj['image'], obj['dpi'], obj['corner_radius'])
                        current_page.placed_boxes.append(box)
                        logger.info(f"✓ {obj['name']} bei X={X:.1f}mm, Y={row_y:.1f}mm (Spalte {col+1}/{cols})")
                        
                        obj_idx += 1
                    
                    # Nächste Reihe
                    Y = row_y + sticker_h + G
                
                # Merke Position der letzten LOTO-Reihe für Count-Sticker-Platzierung
                last_loto_row_y = row_y  # Y der letzten Reihe
                last_loto_cols_used = (len(loto_objects) - 1) % cols + 1 if loto_objects else 0
                last_loto_next_x = start_x + last_loto_cols_used * (sticker_w + G)
                last_loto_row_h = sticker_h
                
                # Update current_y für PageLayout
                current_page.current_y = Y
            
            # Count-Multi NACH den LOTO-Stickern platzieren
            # Versuche in die letzte LOTO-Reihe einzufügen wenn Platz
            if count_objects:
                count_start_x = start_x if loto_objects else margin_mm
                
                # Starte in der letzten LOTO-Reihe wenn dort noch Platz ist
                if loto_objects and last_loto_cols_used < cols:
                    X = last_loto_next_x
                    Y = last_loto_row_y
                    row_height = last_loto_row_h
                else:
                    X = count_start_x
                    Y = current_page.current_y if current_page.current_y > margin_mm else margin_mm
                    row_height = 0
                
                for count_idx, count_obj in enumerate(count_objects, start=1):
                    count_w = count_obj['width_mm']
                    count_h = count_obj['height_mm']
                    
                    # Prüfe ob in aktuelle Reihe passt
                    if X + count_w > sheet_w_mm - margin_mm:
                        # Neue Reihe
                        X = count_start_x
                        Y = Y + row_height + G
                        row_height = 0
                    
                    # Prüfe ob auf aktuelle Seite passt
                    if Y + count_h > max_roll_length_mm - margin_mm:
                        logger.info(f"📄 Count passt nicht mehr → neue Seite")
                        pages.append(current_page)
                        current_page = PageLayout(sheet_w_mm, max_roll_length_mm, margin_mm, gap_mm)
                        X = count_start_x
                        Y = margin_mm
                        row_height = 0
                    
                    box = StickerBox(X, Y, count_w, count_h,
                                   count_obj['image'], count_obj['dpi'], count_obj['corner_radius'])
                    current_page.placed_boxes.append(box)
                    logger.info(
                        f"✓ Count-Multi {count_idx}/{len(count_objects)} bei "
                        f"X={X:.1f}mm, Y={Y:.1f}mm ({count_w:.1f}x{count_h:.1f}mm)"
                    )
                    
                    X += count_w + G
                    row_height = max(row_height, count_h)
                
                current_page.current_y = Y + row_height + G
        
        # Letzte Seite hinzufügen
        if current_page.placed_boxes:
            pages.append(current_page)
        
        logger.info(f"=== PLATZIERUNG FERTIG: {len(pages)} Seite(n) ===")
        
        # === SCHRITT 4: PDF Rendering ===
        MM_TO_PT = 72.0 / 25.4
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Speichere jede Seite als separate PDF
        saved_files = []
        export_basename = _derive_export_basename()
        
        for page_num, page in enumerate(pages, 1):
            # Berechne dynamische Höhe basierend auf Inhalt
            actual_height_mm = page.get_actual_height()
            
            # Standard-Format: Feste Höhe (z.B. A4 = 297mm)
            # Rollenmodus: Dynamische Höhe (min 2*margin, max 600mm)
            if roll_mode:
                page_height_mm = min(max(actual_height_mm, 2 * margin_mm), max_roll_length_mm)
            else:
                # Beschneide auf Inhaltshöhe, aber nie größer als Blatt
                page_height_mm = min(actual_height_mm, sheet_h_mm)
            
            logger.info(f"Seite {page_num}/{len(pages)}: {len(page.placed_boxes)} Sticker, Höhe: {page_height_mm:.1f}mm (Inhalt: {actual_height_mm:.1f}mm, Modus: {'Rolle' if roll_mode else 'Standard'})")
            for box_idx, box in enumerate(page.placed_boxes):
                logger.info(f"   Box {box_idx}: x={box.x:.1f}mm, y={box.y:.1f}mm, {box.width:.1f}x{box.height:.1f}mm")
            
            # Dateiname mit Seitennummer
            if len(pages) > 1:
                out_path = Path(out_dir) / f"{export_basename}_{timestamp}_page{page_num:03d}.pdf"
            else:
                out_path = Path(out_dir) / f"{export_basename}_{timestamp}.pdf"
            
            # Breite auf Inhalt beschneiden
            actual_width_mm = page.get_actual_width()
            page_width_mm = min(actual_width_mm, sheet_w_mm)
            
            # Erstelle Canvas für diese Seite
            pw = page_width_mm * MM_TO_PT
            ph = page_height_mm * MM_TO_PT
            
            c = pdf_canvas.Canvas(str(out_path), pagesize=(pw, ph))
            
            # Zeichne alle Sticker auf dieser Seite
            for box in page.placed_boxes:
                x_pt = box.x * MM_TO_PT
                y_pt = ph - (box.y + box.height) * MM_TO_PT
                w_pt = box.width * MM_TO_PT
                h_pt = box.height * MM_TO_PT
                
                # Bild zeichnen
                c.drawImage(ImageReader(opaque_rgb(box.image)), x_pt, y_pt,
                           width=w_pt, height=h_pt, preserveAspectRatio=False)
                
                # CutContour zeichnen
                draw_cut_contour(c, x_pt, y_pt, w_pt, h_pt, 0.0, MM_TO_PT, 
                               box.corner_radius, box.dpi)
            
            c.save()
            saved_files.append(str(out_path))
            logger.info(f"✓ Seite {page_num} gespeichert: {out_path.name}")
        
        logger.info(f"=== PDF Export FERTIG: {len(saved_files)} Datei(en) ===")
        
        # Success Message
        if len(saved_files) == 1:
            msg_text = f"PDF exportiert:\n{saved_files[0]}"
        else:
            msg_text = f"{len(saved_files)} PDFs exportiert:\n" + "\n".join([Path(f).name for f in saved_files])
        
        msg = QMessageBox(app)
        msg.setWindowTitle("Erfolg")
        msg.setText(msg_text)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #f3f3f3;
            }
            QMessageBox QLabel {
                color: #1f2937;
                font-size: 13px;
            }
            QMessageBox QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                            stop:0 #f6f8fb, stop:1 #eef1f6);
                color: #1e293b;
                border: 1.5px solid #cfd8e6;
                border-radius: 20px;
                padding: 4px 16px;
                min-height: 24px;
                min-width: 80px;
                font-family: 'Segoe UI', 'Bahnschrift';
                font-size: 13px;
                font-weight: 600;
            }
            QMessageBox QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                            stop:0 #dbe8ff, stop:1 #c7d9f9);
                border: 1.5px solid #1d4ed8;
                color: #1d4ed8;
            }
            QMessageBox QPushButton:pressed {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                            stop:0 #c7d9f9, stop:1 #b0c9f5);
            }
        """)
        msg.exec()
        
    except Exception as e:
        logger.error(f"Export-Fehler: {e}", exc_info=True)
        QMessageBox.critical(app, "Fehler", f"Export fehlgeschlagen:\n{str(e)}")
