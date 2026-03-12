# ---------- Utility-Funktionen ----------
import sys
import os
import logging
from typing import List, Optional, Tuple, cast
import io
import base64
from dataclasses import dataclass
import math
import numpy as np
import cv2
from PIL import Image, ImageDraw
from PySide6.QtCore import Qt, QSettings, QObject, QEvent
from PySide6.QtGui import QAction, QPixmap, QImage
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QSpinBox, QDoubleSpinBox, QComboBox, QLabel, QCheckBox,
    QListWidget, QListWidgetItem, QFileDialog, QMessageBox, QScrollArea,
    QSizePolicy, QToolButton, QDialog, QGroupBox, QRadioButton, QButtonGroup
)

logger = logging.getLogger(__name__)

def mm_to_px(mm: float, dpi: float) -> float:
    return (mm / 25.4) * dpi

def pt_to_px(pt: float) -> float:
    # 1pt = 1/72 inch; use 96 px per inch typical screen mapping
    return pt * (96.0 / 72.0)

def pil_to_qimage(img: Image.Image) -> QImage:
    rgba = img.convert("RGBA")
    w, h = rgba.size
    data = rgba.tobytes()
    qimg = QImage(data, w, h, 4 * w, QImage.Format.Format_RGBA8888)
    return qimg.copy()  # ensure data ownership

# ---------- Maskenerkennung ----------
def detect_black_line_masks(img_rgba, black_thresh: int, blur: int, morph: int, min_area_px2: float):
    """
    Erkennt Sticker-Bereiche basierend auf Outlines (schwarz oder farbig).
    Gibt eine Liste von Masken zurück, die die ÄUSSERE Kontur jedes Stickers enthalten.
    
    Strategie:
    1. Versuche zuerst schwarze Outlines zu erkennen (max-Kanal < Schwellwert)
    2. Falls keine Sticker gefunden: Fallback auf farbige Sticker-Erkennung
       (min-Kanal < Schwellwert → direkte Außenkontur der farbigen Fläche)
    """
    import cv2, numpy as np

    rgba = np.array(img_rgba.convert("RGBA"))
    orig_h, orig_w = rgba.shape[:2]
    # Puffer sorgt dafür, dass Outlines, die direkt am Bildrand liegen, trotzdem eine geschlossene Fläche bilden
    pad = max(2, morph + 2)
    if pad > 0:
        rgba = cv2.copyMakeBorder(rgba, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=(255, 255, 255, 255))
    bgr = cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGR)
    # max-Kanal: erkennt nur Pixel bei denen ALLE Kanäle dunkel sind (= schwarz)
    mx = np.max(bgr, axis=2)
    _, black = cv2.threshold(mx, black_thresh, 255, cv2.THRESH_BINARY_INV)
    if blur > 0 and blur % 2 == 1:
        black = cv2.GaussianBlur(black, (blur, blur), 0)
        _, black = cv2.threshold(black, 127, 255, cv2.THRESH_BINARY)
    if morph > 0:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (morph, morph))
        black = cv2.morphologyEx(black, cv2.MORPH_CLOSE, k)
    
    # === Schritt 1: Messe die typische Breite der schwarzen Outline ===
    # Berechne die Distanztransformation der schwarzen Maske,
    # um die halbe Outline-Breite zu bestimmen
    black_dist = cv2.distanceTransform(black, cv2.DIST_L2, 5)
    # Der Median der Distanzwerte innerhalb der schwarzen Bereiche
    # gibt uns eine gute Schätzung der halben Outline-Breite
    black_pixels = black_dist[black > 0]
    if len(black_pixels) > 0:
        outline_half_width = float(np.median(black_pixels))
    else:
        outline_half_width = 3.0  # Fallback
    # Dilatationsradius: etwas mehr als die halbe Outline-Breite
    dilate_radius = max(2, int(outline_half_width * 1.5 + 1))
    
    # Invertiere: Schwarze Linien werden zu 0, Rest zu 255
    non_black = 255 - black

    # Entferne Hintergrundflächen außerhalb der Sticker, indem die von außen erreichbaren Bereiche leer geflutet werden
    flood_src = non_black.copy()
    flood_mask = np.zeros((flood_src.shape[0] + 2, flood_src.shape[1] + 2), dtype=np.uint8)
    cv2.floodFill(flood_src, flood_mask, (0, 0), 0)
    non_black = flood_src
    
    # Finde alle verbundenen Komponenten (potenzielle Sticker-Bereiche)
    num, labels, stats, _ = cv2.connectedComponentsWithStats(non_black, connectivity=8)
    h, w = non_black.shape[:2]
    raw_masks: List[np.ndarray] = []
    
    for i in range(1, num):  # 0 ist Hintergrund
        x, y, cw, ch, area = stats[i]
        
        # Filtere zu kleine Bereiche aus
        if area < max(1.0, float(min_area_px2)):
            continue
            
        # Erstelle Maske für diese Sticker-Komponente
        component_mask = np.zeros_like(non_black, dtype=np.uint8)
        component_mask[labels == i] = 255
        
        # KRITISCH: Finde NUR die äußerste Kontur - ignoriere alle inneren Konturen
        contours, _ = cv2.findContours(component_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        
        if contours:
            # Wähle die größte äußere Kontur als Sticker-Grenze
            outer_contour = max(contours, key=cv2.contourArea)
            
            # Erstelle eine saubere Maske NUR mit der äußeren Sticker-Form
            clean_outer_mask = np.zeros_like(component_mask, dtype=np.uint8)
            cv2.fillPoly(clean_outer_mask, [outer_contour], 255)
            raw_masks.append(clean_outer_mask)
    
    # === Schritt 2: Dilatiere jede Maske um die Outline-Breite ===
    # Dadurch umschließt die Maske auch die schwarze Outline selbst
    dilate_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * dilate_radius + 1, 2 * dilate_radius + 1))
    dilated_masks: List[np.ndarray] = []
    for m in raw_masks:
        dilated = cv2.dilate(m, dilate_kernel)
        dilated_masks.append(dilated)
    
    # === Schritt 3: Merge überlappende dilatierte Masken ===
    # Wenn Masken sich nach der Dilatation überlappen, gehören sie zum selben Sticker
    merged_masks: List[np.ndarray] = list(dilated_masks)
    changed = True
    while changed and len(merged_masks) > 1:
        changed = False
        for i in range(len(merged_masks)):
            if changed:
                break
            for j in range(i + 1, len(merged_masks)):
                # Prüfe ob sich die Masken überlappen
                overlap = cv2.bitwise_and(merged_masks[i], merged_masks[j])
                if cv2.countNonZero(overlap) > 0:
                    # Merge: Vereinige beide Masken
                    merged_masks[i] = cv2.bitwise_or(merged_masks[i], merged_masks[j])
                    del merged_masks[j]
                    changed = True
                    break
    
    # === Schritt 4: Für jede gemergte Maske, erstelle eine saubere Außenkontur ===
    # UND beschränke auf die tatsächlich schwarzen + inneren Bereiche
    sticker_masks: List[np.ndarray] = []
    for merged_m in merged_masks:
        # Die gemergte dilatierte Maske enthält den gesamten Sticker inkl. Outline
        # Verfeinere: Kombiniere die gemergte Maske mit den schwarzen Pixeln
        # um die exakte äußere Kante zu finden
        # Nimm alles was schwarz ist ODER innerhalb der original Flood-Fill-Bereiche
        combined = cv2.bitwise_or(merged_m, black)
        # Beschränke auf den Bereich der gemergten Maske (nicht über den Sticker hinaus)
        combined = cv2.bitwise_and(combined, merged_m)
        
        # Finde die äußerste Kontur des kombinierten Bereichs
        contours, _ = cv2.findContours(combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        if contours:
            outer = max(contours, key=cv2.contourArea)
            final_mask = np.zeros_like(combined, dtype=np.uint8)
            cv2.fillPoly(final_mask, [outer], 255)
            
            if pad > 0:
                final_mask = final_mask[pad:pad+orig_h, pad:pad+orig_w]
            sticker_masks.append(final_mask)
    
    # Nachfilterung: Entferne sehr kleine Artefakte basierend auf der medianen Fläche
    if sticker_masks:
        import numpy as _np, cv2 as _cv2
        areas = [_cv2.countNonZero(m) for m in sticker_masks]
        median_area = float(_np.median(areas)) if areas else 0.0
        if median_area > 0:
            filtered = [m for m, a in zip(sticker_masks, areas) if a >= 0.35 * median_area]
            if filtered:
                sticker_masks = filtered

        # Performance-Limit (Default 200 / ENV override)
        try:
            limit = int(os.environ.get('CC2_MAX_STICKERS', '200'))
        except Exception:
            limit = 200
        if limit > 0 and len(sticker_masks) > limit:
            areas = [_cv2.countNonZero(m) for m in sticker_masks]
            idx_sorted = sorted(range(len(sticker_masks)), key=lambda i: areas[i], reverse=True)
            sticker_masks = [sticker_masks[i] for i in idx_sorted[:limit]]

        # Entferne Masken, die vollständig innerhalb einer größeren Maske liegen
        if len(sticker_masks) > 1:
            areas = [_cv2.countNonZero(m) for m in sticker_masks]
            bboxes = []
            for m in sticker_masks:
                ys, xs = (m > 0).nonzero()
                if len(xs) == 0:
                    bboxes.append((0,0,0,0)); continue
                bboxes.append((int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())))
            keep_flags = [True] * len(sticker_masks)
            for i in range(len(sticker_masks)):
                if not keep_flags[i]:
                    continue
                for j in range(len(sticker_masks)):
                    if i == j or not keep_flags[j]:
                        continue
                    if areas[j] <= areas[i]:
                        continue
                    ix1, iy1, ix2, iy2 = bboxes[i]
                    jx1, jy1, jx2, jy2 = bboxes[j]
                    if ix1 < jx1 or iy1 < jy1 or ix2 > jx2 or iy2 > jy2:
                        continue
                    overlap = _cv2.bitwise_and(sticker_masks[i], sticker_masks[j])
                    if _cv2.countNonZero(overlap) == areas[i]:
                        keep_flags[i] = False
                        break
            sticker_masks = [m for m, keep in zip(sticker_masks, keep_flags) if keep]
    
    if sticker_masks:
        return sticker_masks

    # === FALLBACK: Farbige Sticker erkennen (min-Kanal) ===
    # Für Sticker mit farbigen (nicht-schwarzen) Flächen wie rot, blau, grün.
    # Der min-Kanal pro Pixel ist bei gesättigten Farben niedrig,
    # bei Weiß/Grau jedoch hoch → trennt farbige Sticker vom Hintergrund.
    mn = np.min(bgr, axis=2)
    _, colored_mask = cv2.threshold(mn, black_thresh, 255, cv2.THRESH_BINARY_INV)
    if blur > 0 and blur % 2 == 1:
        colored_mask = cv2.GaussianBlur(colored_mask, (blur, blur), 0)
        _, colored_mask = cv2.threshold(colored_mask, 127, 255, cv2.THRESH_BINARY)
    if morph > 0:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (morph, morph))
        colored_mask = cv2.morphologyEx(colored_mask, cv2.MORPH_CLOSE, k)

    # Direkt die äußeren Konturen der farbigen Fläche finden
    # (kein Flood-Fill/Dilate nötig, da die Farbe SELBST den Sticker definiert)
    contours, _ = cv2.findContours(colored_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < max(1.0, float(min_area_px2)):
            continue
        mask = np.zeros_like(colored_mask, dtype=np.uint8)
        cv2.fillPoly(mask, [cnt], 255)
        if pad > 0:
            mask = mask[pad:pad+orig_h, pad:pad+orig_w]
        sticker_masks.append(mask)

    return sticker_masks

def create_single_cutcontour_per_sticker(
    img_rgba,
    black_thresh: int,
    blur: int,
    morph: int,
    min_area_px2: float,
    offset_mm: float,
    dpi: int,
    eps: float,
) -> List[np.ndarray]:
    """
    Erstellt pro erkannten Sticker genau EINEN rechteckigen CutContour-Pfad.

    Neuer Fokus:
    ✓ Immer eine simple Außenkontur in Form eines Achsen-parallelen Rechtecks
    ✓ Rechteck deckt die komplette Stickerfläche (bzw. Masken-Bounding-Box) ab
    ✓ Innere Objekte werden weiterhin komplett ignoriert
    ✓ Offset wird symmetrisch auf das Rechteck angewandt
    """
    sticker_masks = detect_black_line_masks(img_rgba, black_thresh, blur, morph, min_area_px2)
    cutcontours: List[np.ndarray] = []

    img_size = img_rgba.size
    offset_px = mm_to_px(offset_mm, dpi) if abs(offset_mm) > 1e-6 else 0.0
    # eps Parameter bleibt aus Kompatibilitätsgründen erhalten, hat aber bei reinen Rechtecken keinen Effekt.

    for sticker_mask in sticker_masks:
        rect = _mask_to_rect_polygon(sticker_mask, img_size, offset_px)
        if rect is not None:
            cutcontours.append(rect)

    return cutcontours
def detect_mask_alpha(img: Image.Image, thr: int, blur: int, morph: int, invert: bool, min_area_px2: float = 100.0) -> List[np.ndarray]:
    """
    Erkennt separate Sticker-Bereiche basierend auf Alpha-Kanal.
    Gibt eine Liste von Masken zurück - eine pro erkanntem Sticker.
    NUR die äußere Kontur, ignoriert Buchstaben/Logos im Inneren.
    """
    arr = np.array(img.convert("RGBA"))
    alpha = arr[:, :, 3]
    if blur > 0 and blur % 2 == 1 and cv2 is not None:
        alpha = cv2.GaussianBlur(alpha, (blur, blur), 0)
    if cv2 is not None:
        _, mask = cv2.threshold(alpha, thr, 255, cv2.THRESH_BINARY)
    else:
        mask = (alpha >= thr).astype(np.uint8) * 255
    if morph > 0 and cv2 is not None:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (morph, morph))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)
    if invert:
        mask = 255 - mask
    
    if cv2 is None:
        return [mask]
    
    # Finde alle äußeren Konturen (ignoriert automatisch innere Löcher wie Buchstaben)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    
    if not contours:
        return []
    
    sticker_masks: List[np.ndarray] = []
    
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < max(1.0, float(min_area_px2)):
            continue
        
        # Erstelle Maske nur mit dieser äußeren Kontur (gefüllt)
        single_mask = np.zeros_like(mask, dtype=np.uint8)
        cv2.fillPoly(single_mask, [cnt], 255)
        sticker_masks.append(single_mask)
    
    return sticker_masks

def detect_mask_gray(img: Image.Image, thr: Optional[int], blur: int, morph: int, invert: bool, min_area_px2: float = 100.0) -> List[np.ndarray]:
    """
    Erkennt separate Sticker-Bereiche basierend auf Helligkeit.
    Gibt eine Liste von Masken zurück - eine pro erkanntem Sticker.
    NUR die äußere Kontur, ignoriert Buchstaben/Logos im Inneren.
    """
    arr = np.array(img.convert("L"))
    if blur > 0 and blur % 2 == 1 and cv2 is not None:
        arr = cv2.GaussianBlur(arr, (blur, blur), 0)
    if cv2 is not None:
        if thr is None or thr == 0:
            # Otsu
            _, mask = cv2.threshold(arr, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        else:
            _, mask = cv2.threshold(arr, thr, 255, cv2.THRESH_BINARY)
    else:
        t = thr if thr is not None and thr > 0 else 128
        mask = (arr >= t).astype(np.uint8) * 255
    if morph > 0 and cv2 is not None:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (morph, morph))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)
    if invert:
        mask = 255 - mask
    
    if cv2 is None:
        return [mask]
    
    # Finde alle äußeren Konturen (ignoriert automatisch innere Löcher wie Buchstaben)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    
    if not contours:
        return []
    
    sticker_masks: List[np.ndarray] = []
    
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < max(1.0, float(min_area_px2)):
            continue
        
        # Erstelle Maske nur mit dieser äußeren Kontur (gefüllt)
        single_mask = np.zeros_like(mask, dtype=np.uint8)
        cv2.fillPoly(single_mask, [cnt], 255)
        sticker_masks.append(single_mask)
    
    return sticker_masks

def detect_mask_black_per_sticker(img: Image.Image, black_thr: int, blur: int, morph: int, min_area_px2: float) -> List[np.ndarray]:
    if cv2 is None:
        return []
    return detect_black_line_masks(img, black_thr, blur, morph, min_area_px2)

def detect_mask_color(img: Image.Image, target_rgb: Tuple[int, int, int], tolerance: int, blur: int, morph: int, min_area_px2: float = 100.0) -> List[np.ndarray]:
    """
    Erkennt separate Sticker-Bereiche basierend auf einer bestimmten Farbe.
    Die ausgewählte Farbe wird als HINTERGRUND behandelt und maskiert.
    Gibt eine Liste von Masken zurück - eine pro erkanntem Sticker.
    NUR die äußere Kontur, ignoriert Buchstaben/Logos im Inneren.
    
    Args:
        img: PIL Image
        target_rgb: Tuple (R, G, B) der HINTERGRUNDFARBE (wird maskiert)
        tolerance: Maximale Abweichung pro Kanal (0-255)
        blur: Gaussian Blur Kernel-Größe
        morph: Morphologische Schließen Kernel-Größe
        min_area_px2: Minimale Fläche in Pixel²
    """
    if cv2 is None:
        return []
    
    # Konvertiere zu RGB Array
    arr = np.array(img.convert("RGB"))
    
    # Berechne Abstand zu Hintergrundfarbe für jeden Pixel
    target = np.array(target_rgb, dtype=np.float32)
    diff = np.abs(arr.astype(np.float32) - target)
    
    # Erstelle Binärmaske:
    # - Pixel die der Hintergrundfarbe entsprechen (innerhalb Toleranz) → 0 (schwarz)
    # - Pixel die NICHT der Hintergrundfarbe entsprechen → 255 (weiß = Sticker)
    is_background = np.all(diff <= tolerance, axis=2)
    mask = (~is_background).astype(np.uint8) * 255
    
    if blur > 0 and blur % 2 == 1:
        mask = cv2.GaussianBlur(mask, (blur, blur), 0)
        # Nach Blur: Re-threshold um saubere Binärmaske zu bekommen
        _, mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
    
    if morph > 0:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (morph, morph))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)
    
    # Finde alle äußeren Konturen der weißen Bereiche (= Sticker)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    
    if not contours:
        return []
    
    sticker_masks: List[np.ndarray] = []
    
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < max(1.0, float(min_area_px2)):
            continue
        
        # Erstelle Maske nur mit dieser äußeren Kontur (gefüllt)
        single_mask = np.zeros_like(mask, dtype=np.uint8)
        cv2.fillPoly(single_mask, [cnt], 255)
        sticker_masks.append(single_mask)
    
    return sticker_masks

# ---------- Bild/PDF-Handling ----------
try:
    import fitz
except Exception:
    fitz = None

try:
    from pdf2image import convert_from_path
except Exception:
    convert_from_path = None

def load_image_any(path: str, pdf_dpi: int = 300) -> Image.Image:  # type: ignore[override]
    ext = os.path.splitext(path)[1].lower()
    if ext == '.pdf':
        if fitz is None:
            raise RuntimeError(
                "PDF kann nicht geladen werden: PyMuPDF (pymupdf) ist nicht installiert.\n"
                "Installation: pip install pymupdf"
            )
        try:
            doc = fitz.open(path)
            if doc.page_count == 0:
                raise RuntimeError("Leere PDF (keine Seiten)")
            page = doc.load_page(0)
            # DPI -> Skalierung (72 pt = 1 Zoll in PDF Basis)
            scale = pdf_dpi / 72.0
            mat = fitz.Matrix(scale, scale)
            pix = page.get_pixmap(matrix=mat, alpha=True)
            mode = 'RGBA' if pix.alpha else 'RGB'
            img = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
            # Vereinheitlichen auf RGBA für nachfolgende Verarbeitung
            if mode != 'RGBA':
                img = img.convert('RGBA')
            return img
        except Exception as e:  # noqa: E722
            raise RuntimeError(f"PDF Rendering fehlgeschlagen: {e}")
    # Fallback für normale Bilder
    return Image.open(path)

def load_image_any_with_page(path: str, pdf_dpi: int = 300, page_index: int = 0) -> Image.Image:
    ext = os.path.splitext(path)[1].lower()
    if ext == '.pdf':
        if fitz is not None:
            try:
                doc = fitz.open(path)
                if page_index < doc.page_count:
                    page = doc.load_page(page_index)
                    mat = fitz.Matrix(pdf_dpi/72.0, pdf_dpi/72.0)
                    pix = page.get_pixmap(matrix=mat, alpha=True)
                    img = Image.frombytes("RGBA", (pix.width, pix.height), pix.samples)
                    return img
            except Exception:
                pass
        # Fallback to pdf2image
        if convert_from_path is not None:
            try:
                images = convert_from_path(path, dpi=pdf_dpi, first_page=page_index+1, last_page=page_index+1)
                if images:
                    return images[0].convert("RGBA")
            except Exception:
                pass
        raise RuntimeError("PDF kann nicht geladen werden. Installieren Sie PyMuPDF oder pdf2image.")
    return Image.open(path)

def load_pdf_all_pages(path: str, pdf_dpi: int = 300) -> List[Image.Image]:
    images: List[Image.Image] = []
    ext = os.path.splitext(path)[1].lower()
    if ext != '.pdf':
        return [Image.open(path)]
    if fitz is not None:
        try:
            doc = fitz.open(path)
            for page in doc:
                mat = fitz.Matrix(pdf_dpi/72.0, pdf_dpi/72.0)
                pix = page.get_pixmap(matrix=mat, alpha=True)
                img = Image.frombytes("RGBA", (pix.width, pix.height), pix.samples)
                images.append(img)
            doc.close()
        except Exception:
            images = []
    if not images and convert_from_path is not None:
        try:
            imgs = convert_from_path(path, dpi=pdf_dpi)
            images = [img.convert("RGBA") for img in imgs]
        except Exception:
            images = []
    if not images:
        raise RuntimeError("PDF-Seiten konnten nicht geladen werden. Installieren Sie PyMuPDF oder pdf2image.")
    return images

# ---------- PDF Export ----------
try:
    from reportlab.pdfgen import canvas as pdfcanvas
    from reportlab.lib.utils import ImageReader
    from reportlab.lib.colors import Color
except Exception:  # pragma: no cover
    pdfcanvas = None  # type: ignore
    ImageReader = None  # type: ignore
    Color = None  # type: ignore

# ---------- Polygon/Contour-Extraktion ----------

def _perfect_rounded_rect(x_min: float, y_min: float, x_max: float, y_max: float,
                          radius: float, points_per_corner: int = 16) -> np.ndarray:
    """
    Erzeugt ein perfektes Rounded-Rectangle-Polygon mit Kreisbogen-Ecken.
    """
    r = max(0.0, min(radius, (x_max - x_min) / 2.0, (y_max - y_min) / 2.0))
    pts: List[Tuple[float, float]] = []

    if r < 0.5:
        # Kein Radius → einfaches Rechteck
        return np.array([
            [x_min, y_min], [x_max, y_min],
            [x_max, y_max], [x_min, y_max]
        ], dtype=np.float32)

    # 4 Ecken: oben-links, oben-rechts, unten-rechts, unten-links
    corners = [
        (x_min + r, y_min + r, math.pi,     math.pi * 1.5),  # oben-links
        (x_max - r, y_min + r, math.pi * 1.5, math.pi * 2.0),  # oben-rechts
        (x_max - r, y_max - r, 0.0,          math.pi * 0.5),  # unten-rechts
        (x_min + r, y_max - r, math.pi * 0.5, math.pi),        # unten-links
    ]

    for cx, cy, a_start, a_end in corners:
        for i in range(points_per_corner + 1):
            t = i / points_per_corner
            angle = a_start + (a_end - a_start) * t
            pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))

    return np.array(pts, dtype=np.float32)


def _detect_corner_radius(mask: np.ndarray) -> float:
    """
    Misst den tatsächlichen Eckenradius einer Maske.
    Misst sowohl horizontal als auch vertikal an jeder Ecke und mittelt.
    """
    ys, xs = np.nonzero(mask > 0)
    if len(xs) == 0:
        return 0.0

    x_min, x_max = int(xs.min()), int(xs.max())
    y_min, y_max = int(ys.min()), int(ys.max())
    w = x_max - x_min + 1
    h = y_max - y_min + 1

    if w < 4 or h < 4:
        return 0.0

    max_r = min(w, h) // 2
    radii = []

    # 4 Ecken: (corner_x, corner_y, x_direction, y_direction)
    corners = [
        (x_min, y_min, +1, +1),  # oben-links
        (x_max, y_min, -1, +1),  # oben-rechts
        (x_max, y_max, -1, -1),  # unten-rechts
        (x_min, y_max, +1, -1),  # unten-links
    ]

    for cx, cy, dx, dy in corners:
        # Horizontale Messung: wie viele leere Pixel vom Eckpunkt entlang der Kante?
        h_empty = 0
        for d in range(1, max_r):
            px = cx + d * dx
            if 0 <= cy < mask.shape[0] and 0 <= px < mask.shape[1]:
                if mask[cy, px] == 0:
                    h_empty = d
                else:
                    break
            else:
                break

        # Vertikale Messung: wie viele leere Pixel vom Eckpunkt entlang der Kante?
        v_empty = 0
        for d in range(1, max_r):
            py = cy + d * dy
            if 0 <= py < mask.shape[0] and 0 <= cx < mask.shape[1]:
                if mask[py, cx] == 0:
                    v_empty = d
                else:
                    break
            else:
                break

        # Mittelwert horizontal/vertikal ergibt einen genaueren Radius
        if h_empty > 0 and v_empty > 0:
            radii.append((h_empty + v_empty) / 2.0)
        elif h_empty > 0:
            radii.append(float(h_empty))
        elif v_empty > 0:
            radii.append(float(v_empty))

    if not radii:
        return 0.0

    return float(np.median(radii))


def _is_roughly_rectangular(mask: np.ndarray, threshold: float = 0.85) -> Tuple[bool, float, float, float, float, float]:
    """
    Prüft ob eine Maske annähernd rechteckig ist.
    Gibt (is_rect, x_min, y_min, x_max, y_max, corner_radius) zurück.
    """
    ys, xs = np.nonzero(mask > 0)
    if len(xs) == 0:
        return (False, 0, 0, 0, 0, 0)

    x_min = float(xs.min())
    x_max = float(xs.max())
    y_min = float(ys.min())
    y_max = float(ys.max())

    bbox_area = (x_max - x_min + 1) * (y_max - y_min + 1)
    mask_area = float(cv2.countNonZero(mask))

    if bbox_area < 1:
        return (False, 0, 0, 0, 0, 0)

    # Ein Rechteck hat Füllfaktor ~1.0
    # Ein Rounded Rect mit moderatem Radius hat ~0.95+
    fill_ratio = mask_area / bbox_area

    corner_radius = _detect_corner_radius(mask)

    # Berechne den erwarteten Füllfaktor für ein Rounded Rect
    # Ein Rounded Rect mit Radius r in einer w×h Box hat Fläche:
    # w*h - (4-π)*r²
    w = x_max - x_min + 1
    h = y_max - y_min + 1
    if corner_radius > 0:
        expected_area = w * h - (4 - math.pi) * corner_radius * corner_radius
        expected_ratio = expected_area / bbox_area
        # Prüfe ob der Füllfaktor zum erwarteten passt
        if fill_ratio >= expected_ratio * 0.92:
            return (True, x_min, y_min, x_max, y_max, corner_radius)
    
    if fill_ratio >= threshold:
        return (True, x_min, y_min, x_max, y_max, corner_radius)

    return (False, x_min, y_min, x_max, y_max, corner_radius)


def _curvature_aware_downsample(pts: np.ndarray, max_points: int = 300, curvature_keep_factor: float = 3.0) -> np.ndarray:
    """
    Reduziert die Punktanzahl einer Kontur, behält aber mehr Punkte in Bereichen
    mit hoher Krümmung (Ecken, Rundungen) bei.
    """
    n = len(pts)
    if n <= max_points:
        return pts
    
    curvature = np.zeros(n, dtype=np.float32)
    window = max(2, n // 100)
    
    for i in range(n):
        p_prev = pts[(i - window) % n]
        p_curr = pts[i]
        p_next = pts[(i + window) % n]
        
        v1 = p_prev - p_curr
        v2 = p_next - p_curr
        
        len1 = np.linalg.norm(v1)
        len2 = np.linalg.norm(v2)
        
        if len1 < 1e-6 or len2 < 1e-6:
            curvature[i] = 0.0
            continue
        
        cos_angle = np.dot(v1, v2) / (len1 * len2)
        cos_angle = np.clip(cos_angle, -1.0, 1.0)
        angle = np.arccos(cos_angle)
        curvature[i] = np.pi - angle
    
    max_curv = curvature.max()
    if max_curv > 1e-6:
        curvature = curvature / max_curv
    
    weights = 1.0 + curvature * curvature_keep_factor
    cum_weights = np.cumsum(weights)
    total_weight = cum_weights[-1]
    
    target_weights = np.linspace(0, total_weight, max_points, endpoint=False)
    indices = np.searchsorted(cum_weights, target_weights)
    indices = np.clip(indices, 0, n - 1)
    indices = np.unique(indices)
    
    return pts[indices]


def contour_from_mask(mask: np.ndarray, approx_eps_px: float, smooth_iterations: int = 0) -> Optional[np.ndarray]:
    """
    Extrahiert Kontur aus Maske.
    Erkennt automatisch ob die Form rechteckig ist und erzeugt dann
    ein perfektes Rounded-Rectangle mit Kreisbogen-Ecken.
    Für nicht-rechteckige Formen wird die rohe Kontur verwendet.
    """
    # === Prüfe ob die Form rechteckig ist (auf ORIGINAL-Maske, nicht geglättet) ===
    # Die Glättung würde Eckenradien verfälschen
    is_rect, x_min, y_min, x_max, y_max, corner_radius = _is_roughly_rectangular(mask)
    
    if is_rect:
        # Erzeuge perfektes Rounded Rectangle basierend auf exakten Maßen
        pts = _perfect_rounded_rect(x_min, y_min, x_max, y_max, corner_radius, points_per_corner=20)
        if len(pts) >= 3:
            return pts
    
    # === Fallback: Rohe Kontur für nicht-rechteckige Formen ===
    # Hier wird die geglättete Maske verwendet für glattere Konturen
    working_mask = mask.copy()
    if smooth_iterations > 0:
        kernel_size = 2 * smooth_iterations + 1
        working_mask = cv2.GaussianBlur(working_mask, (kernel_size, kernel_size), 0)
        _, working_mask = cv2.threshold(working_mask, 127, 255, cv2.THRESH_BINARY)
    
    cnts_info = cv2.findContours(working_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    contours = cnts_info[-2] if len(cnts_info) == 3 else cnts_info[0]
    if not contours:
        return None
    c = max(contours, key=cv2.contourArea)
    
    pts_raw = c.reshape(-1, 2).astype(np.float32)
    if len(pts_raw) < 3:
        return None
    
    if approx_eps_px <= 0:
        max_pts = 600
    else:
        max_pts = max(60, int(400 / max(0.5, approx_eps_px)))
    
    pts = _curvature_aware_downsample(pts_raw, max_points=max_pts, curvature_keep_factor=4.0)
    
    if len(pts) < 3:
        return None
    
    return pts

def dilate_mask(mask: np.ndarray, offset_px: float) -> np.ndarray:
    r = max(0, int(round(abs(offset_px))))
    if r == 0:
        return mask.copy()
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2*r + 1, 2*r + 1))
    # Positive Offset = dilate (nach außen), Negative Offset = erode (nach innen)
    if offset_px > 0:
        return cv2.dilate(mask, k)
    else:
        return cv2.erode(mask, k)


def _mask_to_rect_polygon(mask: np.ndarray, img_size: Tuple[int, int], offset_px: float) -> Optional[np.ndarray]:
    """Wandelt eine Maske in ein schlichtes Rechteck-Polygon um."""
    ys, xs = np.nonzero(mask > 0)
    if len(xs) == 0 or len(ys) == 0:
        return None

    width, height = img_size

    min_x = float(xs.min())
    max_x = float(xs.max()) + 1.0
    min_y = float(ys.min())
    max_y = float(ys.max()) + 1.0

    # Berechnete Breite/Höhe vor der Offset-Anpassung sichern
    bbox_width = max_x - min_x
    bbox_height = max_y - min_y

    if offset_px > 0.0:
        min_x -= offset_px
        min_y -= offset_px
        max_x += offset_px
        max_y += offset_px
    elif offset_px < 0.0:
        shrink = abs(offset_px)
        # Schrumpfung darf maximal bis zur Hälfte der jeweiligen Kantenlänge reichen
        max_shrink_x = max(0.0, (bbox_width / 2.0) - 0.25)
        max_shrink_y = max(0.0, (bbox_height / 2.0) - 0.25)
        shrink_x = min(shrink, max_shrink_x)
        shrink_y = min(shrink, max_shrink_y)
        min_x += shrink_x
        max_x -= shrink_x
        min_y += shrink_y
        max_y -= shrink_y

    min_x = max(0.0, min_x)
    min_y = max(0.0, min_y)
    max_x = min(float(width), max_x)
    max_y = min(float(height), max_y)

    if (max_x - min_x) <= 1e-3 or (max_y - min_y) <= 1e-3:
        return None

    return np.array(
        [
            [min_x, min_y],
            [max_x, min_y],
            [max_x, max_y],
            [min_x, max_y],
        ],
        dtype=np.float32,
    )

def extract_polygons_per_sticker_from_masks(
    sticker_masks: List[np.ndarray],
    approx_eps_px: float,
    offset_px: float
) -> List[np.ndarray]:
    """
    Extrahiert genau ein rechteckiges CutContour-Polygon pro Sticker-Maske.

    Hinweis: approx_eps_px bleibt für API-Kompatibilität erhalten, hat bei Rechtecken
    jedoch keine Auswirkung.
    """
    cutcontour_polygons: List[np.ndarray] = []
    for sticker_mask in sticker_masks:
        img_size = (sticker_mask.shape[1], sticker_mask.shape[0])
        rect = _mask_to_rect_polygon(sticker_mask, img_size, offset_px)
        if rect is not None:
            cutcontour_polygons.append(rect)
    
    return cutcontour_polygons

def extract_polygons_from_single_mask(
    mask: np.ndarray,
    min_area_px2: float,
    approx_eps_px: float,
    offset_px: float
) -> List[np.ndarray]:
    """Split into components, per-sticker dilate for offset, then contour."""
    num, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    polys: List[np.ndarray] = []
    for i in range(1, num):
        _, _, _, _, area = stats[i]
        if area < max(1.0, float(min_area_px2)):
            continue
        comp = np.zeros_like(mask)
        comp[labels == i] = 255
        work = dilate_mask(comp, offset_px) if abs(offset_px) > 1e-6 else comp
        c = contour_from_mask(work, approx_eps_px)
        if c is not None:
            polys.append(c)
    return polys

def build_perf_outline(polys: List[np.ndarray], margin_mm: float, dpi: int, img_size: Tuple[int,int]) -> Optional[np.ndarray]:
    if not polys:
        return None
    xs: List[float] = []
    ys: List[float] = []
    for p in polys:
        if p is None or len(p) == 0:
            continue
        xs.extend(p[:,0].tolist())
        ys.extend(p[:,1].tolist())
    if not xs:
        return None
    min_x = float(min(xs)); max_x = float(max(xs))
    min_y = float(min(ys)); max_y = float(max(ys))
    margin_px = mm_to_px(margin_mm, dpi)
    w, h = img_size
    min_x = max(0.0, min_x - margin_px)
    min_y = max(0.0, min_y - margin_px)
    max_x = min(w - 1.0, max_x + margin_px)
    max_y = min(h - 1.0, max_y + margin_px)
    rect = np.array([
        [min_x, min_y],
        [max_x, min_y],
        [max_x, max_y],
        [min_x, max_y]
    ], dtype=np.float32)
    return rect

# ---------- Overlay/Rendering ----------
def render_overlay(base_img_rgba: Image.Image, polygons: List[np.ndarray], stroke_px: int, show_indices: bool) -> Image.Image:
    overlay = Image.new("RGBA", base_img_rgba.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    color = (255, 0, 0, 220)
    label = (0, 255, 0, 220)
    for idx, poly in enumerate(polygons):
        if poly.shape[0] < 2:
            continue
        pts = [tuple(map(float, p)) for p in poly.tolist()]
        draw.line(pts + [pts[0]], fill=color, width=stroke_px)
        if show_indices:
            x, y = pts[0]
            draw.text((x + 3, y + 3), str(idx + 1), fill=label)
    return Image.alpha_composite(base_img_rgba.convert("RGBA"), overlay)

def render_overlay_with_types(
    base_img_rgba: Image.Image,
    polygons: List[np.ndarray],
    types: List[str],
    stroke_px: int,
    show_indices: bool,
    cut_color: Tuple[int,int,int,int] = (255,0,255,220),
    perf_color: Tuple[int,int,int,int] = (0,255,255,220)
) -> Image.Image:
    overlay = Image.new("RGBA", base_img_rgba.size, (0,0,0,0))
    draw = ImageDraw.Draw(overlay)
    for idx, poly in enumerate(polygons):
        if poly.shape[0] < 2:
            continue
        color = cut_color if (idx < len(types) and types[idx] == "Cut") else perf_color
        pts = [tuple(map(float, p)) for p in poly.tolist()]
        draw.line(pts + [pts[0]], fill=color, width=stroke_px)
        if show_indices:
            x, y = pts[0]
            draw.text((x+3, y+3), f"{idx+1}", fill=(255,255,255,230))
    return Image.alpha_composite(base_img_rgba.convert("RGBA"), overlay)

def polygons_to_svg_both(
    cut_polys: List[np.ndarray],
    perf_polys: List[np.ndarray],
    width: int,
    height: int,
    stroke_pt: float = 0.25,
    artwork_b64: Optional[str] = None
) -> str:
    stroke_px = pt_to_px(stroke_pt)
    header = '<?xml version="1.0" encoding="UTF-8"?>'
    open_svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" version="1.1" '
        f'xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" '
        f'xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd" '
        f'xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
    )
    namedview = '<sodipodi:namedview id="namedview1" inkscape:current-layer="CutContour" />'
    close_svg = '</svg>'
    comment_a = '<!-- RasterLink detects cut lines by SPOT COLOR NAME: CutContour / PerfCutContour -->'
    comment_b = '<!-- Paths: stroke only (no fill). Thin line (~0.1–0.25 pt). Name is decisive; color is just visual. -->'

    def path_d(poly: np.ndarray) -> str:
        parts = []
        x0, y0 = poly[0]
        parts.append(f"M {float(x0):.3f} {float(y0):.3f}")
        for x, y in poly[1:]:
            parts.append(f"L {float(x):.3f} {float(y):.3f}")
        parts.append("Z")
        return " ".join(parts)

    def group_block(polys: List[np.ndarray], spot_name: str, stroke_color: str) -> str:
        open_group = (
            f'<g id="{spot_name}" label="{spot_name}" aria-label="{spot_name}" '
            f'inkscape:groupmode="layer" inkscape:label="{spot_name}" sodipodi:role="layer" data-spot-color="{spot_name}" '
            f'fill="none" stroke="{stroke_color}" stroke-width="{stroke_px}" '
            f'stroke-linejoin="round" stroke-linecap="round">'
        )
        paths = [f'<title>{spot_name}</title>']
        real_count = 0
        for i, poly in enumerate(polys, start=1):
            if poly.shape[0] < 2:
                continue
            d = path_d(poly)
            paths.append(f'<path id="{spot_name.lower()}-{i}" data-spot-color="{spot_name}" d="{d}" />')
            real_count += 1
        if real_count == 0:
            # Invisible fill-only placeholder (not cuttable), ensures layer shows up in editors
            paths.append('<rect width="1" height="1" x="-10000" y="-10000" fill="#000" opacity="0" stroke="none" />')
        return open_group + "".join(paths) + "</g>"

    def artwork_block(image_b64: str) -> str:
        # Bottom artwork layer with embedded raster image
        open_group = (
            f'<g id="Artwork" label="Artwork" aria-label="Artwork" '
            f'inkscape:groupmode="layer" inkscape:label="Artwork" sodipodi:role="layer">'
        )
        # Provide both href and xlink:href for compatibility
        img_el = (
            f'<image id="artwork-image" width="{width}" height="{height}" x="0" y="0" '
            f'preserveAspectRatio="none" href="data:image/png;base64,{image_b64}" '
            f'xlink:href="data:image/png;base64,{image_b64}" />'
        )
        return open_group + '<title>Artwork</title>' + img_el + '</g>'

    body_parts = [
        header
        , "\n", open_svg
        , "\n", namedview
        , "\n", comment_a
        , "\n", comment_b
    ]
    # Insert artwork layer first (bottom) if provided
    if artwork_b64:
        body_parts += ["\n", artwork_block(artwork_b64)]
    # Then cut layer on top
    body_parts += [
        "\n", group_block(cut_polys, "CutContour", "#FF00FF"),
        "\n", close_svg
    ]
    return "".join(body_parts)

# ---------- UI-Komponenten ----------
class CollapsibleGroupBox(QWidget):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setContentsMargins(0, 0, 0, 0)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.toggle_button = QToolButton()
        self.toggle_button.setStyleSheet("QToolButton { border: none; }")
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(Qt.ArrowType.RightArrow)
        self.toggle_button.setText(title)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(True)
        layout.addWidget(self.toggle_button)
        
        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(20, 0, 0, 0)
        layout.addWidget(self.content_area)
        
        self.toggle_button.toggled.connect(self.on_toggled)
        self.on_toggled(True)
    
    def on_toggled(self, checked):
        self.content_area.setVisible(checked)
        self.toggle_button.setArrowType(Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow)
    
    def setContentLayout(self, layout):
        # Remove existing layout if any
        if self.content_layout.count() > 0:
            old_layout = self.content_layout.takeAt(0)
            if old_layout:
                old_widget = old_layout.widget()
                if old_widget is not None:
                    old_widget.setParent(None)
                else:
                    old_sub_layout = old_layout.layout()
                    if old_sub_layout is not None:
                        old_sub_layout.setParent(None)
        self.content_layout.addLayout(layout)
    
    def setBodyMaxHeight(self, height):
        self.content_area.setMaximumHeight(height)

class ClickableLabel(QLabel):
    """QLabel that supports mouse clicks for pipette tool"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.click_callback = None
    
    def mousePressEvent(self, event):
        if self.click_callback:
            pos = event.position().toPoint()  # Use position() instead of deprecated pos()
            self.click_callback(pos)
        super().mousePressEvent(event)

def ensure_dependencies(parent, auto_install=True):
    missing = []
    try:
        import PySide6
    except ImportError:
        missing.append("PySide6")
    try:
        import numpy
    except ImportError:
        missing.append("numpy")
    try:
        import cv2
    except ImportError:
        missing.append("opencv-python")
    try:
        import PIL
    except ImportError:
        missing.append("Pillow")
    try:
        import fitz
    except ImportError:
        missing.append("pymupdf")
    try:
        import reportlab.pdfgen
    except ImportError:
        missing.append("reportlab")
    
    if not missing:
        return True
    
    msg = f"Fehlende Dependencies: {', '.join(missing)}\n\nInstallieren?"
    if not auto_install or QMessageBox.question(parent, "Dependencies", msg) != QMessageBox.StandardButton.Yes:
        return False
    
    import subprocess
    import sys
    for pkg in missing:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
        except Exception as e:
            QMessageBox.critical(parent, "Installation fehlgeschlagen", f"Fehler bei {pkg}: {e}")
            return False
    QMessageBox.information(parent, "Erfolg", "Dependencies installiert. Starten Sie die App neu.")
    return True

class PdfPageSelector(QDialog):
    def __init__(self, pdf_path, page_count, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PDF Seiten und Modus auswählen")
        self.setMinimumSize(900, 700)
        self.pdf_path = pdf_path
        self.page_count = page_count
        self.selected_pages = []  # Liste der ausgewählten Seitenindizes
        self.selected_mode = "Transparenz (Alpha)"
        self.parent_window = parent
        self.action_mode = "load"  # "load", "analyze", "stash"
        
        layout = QVBoxLayout(self)
        
        # Modus-Auswahl oben
        mode_group = QGroupBox("Analyse-Modus")
        mode_layout = QVBoxLayout()
        self.mode_buttons = QButtonGroup(self)
        
        modes = ["Transparenz (Alpha)", "Helligkeit (Threshold)", "Outline (Schwarz/Farbe)"]
        for i, mode in enumerate(modes):
            rb = QRadioButton(mode)
            if i == 0:
                rb.setChecked(True)
            self.mode_buttons.addButton(rb, i)
            mode_layout.addWidget(rb)
        
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # Seiten-Vorschau
        layout.addWidget(QLabel(f"PDF hat {page_count} Seiten. Wähle Seiten aus:"))
        
        # Scroll-Bereich für Thumbnails
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(350)
        
        scroll_widget = QWidget()
        self.grid_layout = QGridLayout(scroll_widget)
        self.grid_layout.setSpacing(10)
        
        # Thumbnails laden
        self.page_checkboxes = []
        self._load_thumbnails()
        
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        # Alle auswählen / Abwählen
        select_buttons = QHBoxLayout()
        btn_select_all = QPushButton("Alle auswählen")
        btn_select_all.clicked.connect(self._select_all)
        btn_deselect_all = QPushButton("Alle abwählen")
        btn_deselect_all.clicked.connect(self._deselect_all)
        select_buttons.addWidget(btn_select_all)
        select_buttons.addWidget(btn_deselect_all)
        select_buttons.addStretch()
        layout.addLayout(select_buttons)
        
        # Aktions-Buttons
        action_buttons = QHBoxLayout()
        
        btn_analyze = QPushButton("Alle analysieren")
        btn_analyze.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 8px;")
        btn_analyze.clicked.connect(self._analyze_all)
        
        btn_analyze_stash = QPushButton("Alle analysieren + in Ablage")
        btn_analyze_stash.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        btn_analyze_stash.clicked.connect(self._analyze_and_stash)
        
        action_buttons.addWidget(btn_analyze)
        action_buttons.addWidget(btn_analyze_stash)
        layout.addLayout(action_buttons)
        
        # OK / Abbrechen
        buttons = QHBoxLayout()
        btn_load = QPushButton("Nur laden")
        btn_load.clicked.connect(self._load_only)
        cancel = QPushButton("Abbrechen")
        cancel.clicked.connect(self.reject)
        buttons.addStretch()
        buttons.addWidget(btn_load)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)
    
    def _load_thumbnails(self):
        """Lädt Thumbnails aller PDF-Seiten"""
        try:
            import fitz
            doc = fitz.open(self.pdf_path)
            
            cols = 4  # 4 Spalten
            for i in range(self.page_count):
                page = doc.load_page(i)
                # Kleine Vorschau rendern
                mat = fitz.Matrix(0.3, 0.3)  # 30% Größe
                pix = page.get_pixmap(matrix=mat, alpha=False)
                
                # Konvertiere zu QPixmap
                img_data = pix.samples
                qimg = QImage(img_data, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(qimg)
                
                # Container für Seite
                page_widget = QWidget()
                page_layout = QVBoxLayout(page_widget)
                page_layout.setContentsMargins(5, 5, 5, 5)
                
                # Thumbnail
                thumb_label = QLabel()
                thumb_label.setPixmap(pixmap)
                thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                thumb_label.setStyleSheet("border: 1px solid #ccc;")
                page_layout.addWidget(thumb_label)
                
                # Checkbox
                chk = QCheckBox(f"Seite {i + 1}")
                chk.setChecked(True)  # Standard: alle ausgewählt
                self.page_checkboxes.append(chk)
                page_layout.addWidget(chk, alignment=Qt.AlignmentFlag.AlignCenter)
                
                # Zum Grid hinzufügen
                row = i // cols
                col = i % cols
                self.grid_layout.addWidget(page_widget, row, col)
            
            doc.close()
        except Exception as e:
            QMessageBox.warning(self, "Fehler", f"Konnte Vorschau nicht laden:\n{e}")
    
    def _select_all(self):
        for chk in self.page_checkboxes:
            chk.setChecked(True)
    
    def _deselect_all(self):
        for chk in self.page_checkboxes:
            chk.setChecked(False)
    
    def _get_selected_info(self):
        """Sammelt ausgewählte Seiten und Modus"""
        self.selected_pages = [i for i, chk in enumerate(self.page_checkboxes) if chk.isChecked()]
        
        if not self.selected_pages:
            QMessageBox.warning(self, "Hinweis", "Bitte mindestens eine Seite auswählen.")
            return False
        
        # Hole ausgewählten Modus
        checked_button = self.mode_buttons.checkedButton()
        if checked_button:
            self.selected_mode = checked_button.text()
        
        return True
    
    def _load_only(self):
        """Nur laden ohne Analyse"""
        if self._get_selected_info():
            self.action_mode = "load"
            self.accept()
    
    def _analyze_all(self):
        """Alle Seiten laden und analysieren"""
        if self._get_selected_info():
            self.action_mode = "analyze"
            self.accept()
    
    def _analyze_and_stash(self):
        """Alle Seiten laden, analysieren und in Ablage verschieben"""
        if self._get_selected_info():
            self.action_mode = "stash"
            self.accept()

# ---------- Qt UI ----------

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sticker Cut-Contours (Desktop, Single File)")
        self.resize(1200, 800)
        # State
        self.pil_img = None
        self.polygons = []
        self.poly_types = []  # "Cut" or "Perf" per polygon
        self._last_polygons: List[np.ndarray] = []
        self._last_poly_types: List[str] = []
        self.pdf_pages: List[Image.Image] = []
        self.pdf_page_index = 0
        self._current_source_path: Optional[str] = None
        self._orig_pixmap = None
        self._updating_list = False
        # Zoom
        self.zoom_mode = "fit"  # "fit" or "manual"
        self.zoom_factor = 1.0
        # Cached arrays / overlay
        self._img_arrays: Optional[dict] = None
        self._poly_version = 0
        self._types_version = 0
        self._overlay_cache_key = None
        self._overlay_cached_img: Optional[Image.Image] = None
        self.pipette_mode = False  # Pipetten-Modus Flag
        # Theme state
        self._dark_mode = False
        self._build_ui()
        self._build_menu()
        self._load_settings()
        self._apply_light_palette()

    def _build_menu(self):
        m = self.menuBar().addMenu("&Datei")
        a_open = QAction("Öffnen…", self); a_open.triggered.connect(self.open_image); m.addAction(a_open)
        a_export_pdf = QAction("PDF exportieren…", self); a_export_pdf.triggered.connect(self.export_pdf); m.addAction(a_export_pdf)
        a_exit = QAction("Beenden", self); a_exit.triggered.connect(self.close); m.addAction(a_exit)
        
        # Theme menu
        m_view = self.menuBar().addMenu("&Ansicht")
        self.theme_action = QAction("🌙 Dark Mode", self)
        self.theme_action.setCheckable(True)
        self.theme_action.setChecked(False)
        self.theme_action.triggered.connect(self._toggle_theme)
        m_view.addAction(self.theme_action)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        controls = QVBoxLayout(); controls.setSpacing(10)
        # Top buttons
        row = QHBoxLayout()
        self.btn_open = QPushButton("Bild öffnen"); self.btn_open.clicked.connect(self.open_image)
        self.btn_analyze = QPushButton("Analyse starten"); self.btn_analyze.clicked.connect(self.run_analysis)
        self.btn_move_to_stash = QPushButton("Konturen in Ablage")
        self.btn_move_to_stash.clicked.connect(self.move_analysis_to_stash)
        self.btn_move_to_stash.setEnabled(False)
        row.addWidget(self.btn_open)
        row.addWidget(self.btn_analyze)
        row.addWidget(self.btn_move_to_stash)
        controls.addLayout(row)
        self.page_nav_widget = QWidget()
        nav_layout = QHBoxLayout(self.page_nav_widget)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(6)
        self.btn_prev_page = QPushButton("◀ Vorherige Seite")
        self.btn_prev_page.clicked.connect(self.prev_pdf_page)
        self.btn_next_page = QPushButton("Nächste Seite ▶")
        self.btn_next_page.clicked.connect(self.next_pdf_page)
        self.lbl_page_info = QLabel("Seite 0/0")
        nav_layout.addWidget(self.btn_prev_page)
        nav_layout.addWidget(self.btn_next_page)
        nav_layout.addWidget(self.lbl_page_info)
        nav_layout.addStretch(1)
        controls.addWidget(self.page_nav_widget)
        self.page_nav_widget.setVisible(False)
        # Erkennung — entfernte UI-Elemente (Standardparameter werden benutzt)
        # Wir benötigen die detaillierten Erkennungs-Parameter UI nicht mehr.
        # Erstellung eines schlanken Modus-Auswahlfeldes mit den verbleibenden Moden.
        grp1 = CollapsibleGroupBox("Erkennung"); g1 = QGridLayout(); r = 0
        self.cmb_mode = QComboBox(); self.cmb_mode.addItems(["Transparenz (Alpha)", "Helligkeit (Threshold)", "Outline (Schwarz/Farbe)"])
        g1.addWidget(QLabel("Modus:"), r,0); g1.addWidget(self.cmb_mode, r,1); r+=1
        grp1.setContentLayout(g1); grp1.setBodyMaxHeight(60); controls.addWidget(grp1)
        # Default-Parameter (ersetzt die vorher sichtbaren Steuerelemente)
        self.default_alpha = 10
        self.default_gray = 0
        self.default_black = 70
        self.default_blur = 7  # Erhöht für glattere Konturen
        self.default_morph = 7  # Erhöht für bessere Formenkohärenz
        self.default_area_px2 = 1000.0
        self.default_invert = False
        self.default_color_tolerance = 30
        self.picked_color = None
        # Konturen
        grp2 = CollapsibleGroupBox("Konturen"); g2 = QGridLayout(); r=0
        self.spn_dpi = QSpinBox(); self.spn_dpi.setRange(72,1200); self.spn_dpi.setValue(300)
        g2.addWidget(QLabel("DPI:"), r,0); g2.addWidget(self.spn_dpi, r,1); r+=1
        self.dsp_offset_mm = QDoubleSpinBox(); self.dsp_offset_mm.setRange(-50.0,50.0); self.dsp_offset_mm.setDecimals(2); self.dsp_offset_mm.setValue(0.0); self.dsp_offset_mm.setSingleStep(0.1)
        g2.addWidget(QLabel("Offset (mm):"), r,0); g2.addWidget(self.dsp_offset_mm, r,1); r+=1
        self.spn_smooth = QSpinBox(); self.spn_smooth.setRange(0,15); self.spn_smooth.setValue(3); self.spn_smooth.setSingleStep(1)
        g2.addWidget(QLabel("Kontur-Glättung:"), r,0); g2.addWidget(self.spn_smooth, r,1); r+=1
        self.dsp_epsilon = QDoubleSpinBox(); self.dsp_epsilon.setRange(0.0,50.0); self.dsp_epsilon.setDecimals(2); self.dsp_epsilon.setValue(1.0); self.dsp_epsilon.setSingleStep(0.1)
        g2.addWidget(QLabel("Vereinfachung ε (px):"), r,0); g2.addWidget(self.dsp_epsilon, r,1); r+=1
        self.spn_stroke = QSpinBox(); self.spn_stroke.setRange(1,20); self.spn_stroke.setValue(2)
        g2.addWidget(QLabel("Vorschau Liniendicke (px):"), r,0); g2.addWidget(self.spn_stroke, r,1); r+=1
        self.chk_indices = QCheckBox("Indizes anzeigen"); g2.addWidget(self.chk_indices, r,0,1,2); r+=1
        self.cmb_spot = QComboBox(); self.cmb_spot.addItems(["CutContour"])
        g2.addWidget(QLabel("Export-Spot:"), r,0); g2.addWidget(self.cmb_spot, r,1); r+=1
        grp2.setContentLayout(g2); grp2.setBodyMaxHeight(270); controls.addWidget(grp2)
        # Vorschau & Zoom
        grp3 = CollapsibleGroupBox("Vorschau & Zoom"); g3 = QGridLayout(); r=0
        zrow = QHBoxLayout()
        self.btn_zoom_out = QPushButton("−")
        self.btn_zoom_out.setFixedSize(38, 38)
        self.btn_zoom_out.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 rgba(16, 185, 129, 0.9), 
                    stop:1 rgba(5, 150, 105, 0.9));
                color: white;
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 8px;
                font-size: 16pt;
                font-weight: bold;
                padding: 2px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 rgba(16, 185, 129, 1.0), 
                    stop:1 rgba(5, 150, 105, 1.0));
            }
        """)
        self.btn_zoom_out.clicked.connect(self.zoom_out)
        
        self.btn_zoom_in = QPushButton("+")
        self.btn_zoom_in.setFixedSize(38, 38)
        self.btn_zoom_in.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 rgba(16, 185, 129, 0.9), 
                    stop:1 rgba(5, 150, 105, 0.9));
                color: white;
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 8px;
                font-size: 16pt;
                font-weight: bold;
                padding: 2px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 rgba(16, 185, 129, 1.0), 
                    stop:1 rgba(5, 150, 105, 1.0));
            }
        """)
        self.btn_zoom_in.clicked.connect(self.zoom_in)
        
        self.btn_zoom_100 = QPushButton("100%")
        self.btn_zoom_100.setMinimumHeight(36)
        self.btn_zoom_100.clicked.connect(self.zoom_reset)
        
        self.btn_zoom_fit = QPushButton("An Fenster")
        self.btn_zoom_fit.setMinimumHeight(36)
        self.btn_zoom_fit.clicked.connect(self.zoom_fit)
        
        self.lbl_zoom = QLabel("Zoom: Fit")
        for w in (self.btn_zoom_out, self.btn_zoom_in, self.btn_zoom_100, self.btn_zoom_fit, self.lbl_zoom):
            zrow.addWidget(w)
        g3.addLayout(zrow, r,0,1,2); r+=1
        self.chk_embed_artwork = QCheckBox("Bild als Ebene exportieren (Artwork)"); self.chk_embed_artwork.setChecked(True)
        g3.addWidget(self.chk_embed_artwork, r,0,1,2); r+=1
        self.stash_polygons = []; self.stash_types = []; self.stash_page_info = []
        stash_row = QHBoxLayout()
        self.btn_stash_add = QPushButton("In Ablage +"); self.btn_stash_add.clicked.connect(self.stash_add)
        self.btn_stash_clear = QPushButton("Ablage leeren"); self.btn_stash_clear.clicked.connect(self.stash_clear)
        stash_row.addWidget(self.btn_stash_add); stash_row.addWidget(self.btn_stash_clear)
        g3.addLayout(stash_row, r,0,1,2); r+=1
        self.chk_preview_stash = QCheckBox("Ablage in Vorschau anzeigen"); self.chk_preview_stash.toggled.connect(self._refresh_overlay); self.chk_preview_stash.setChecked(False)
        g3.addWidget(self.chk_preview_stash, r,0,1,2); r+=1
        g3.addWidget(QLabel("Ablage:"), r,0,1,2); r+=1
        self.list_stash = QListWidget(); self.list_stash.setMaximumHeight(120)
        g3.addWidget(self.list_stash, r,0,1,2); r+=1
        self.chk_export_stash = QCheckBox("Ablage beim Export benutzen"); g3.addWidget(self.chk_export_stash, r,0,1,2); r+=1
        grp3.setContentLayout(g3); grp3.setBodyMaxHeight(340); controls.addWidget(grp3)
        # Export Einstellungen
        grp_export = CollapsibleGroupBox("Export"); gx = QGridLayout(); rx=0
        self.cmb_media_preset = QComboBox(); self.cmb_media_preset.addItems(["Auto (Bildgröße)","A4 Hoch","A4 Quer","A3 Hoch","A3 Quer","A5 Hoch","A5 Quer","Letter","Tabloid","Benutzerdefiniert"])
        gx.addWidget(QLabel("Seitenformat:"), rx,0); gx.addWidget(self.cmb_media_preset, rx,1); rx+=1
        self.spn_media_w = QDoubleSpinBox(); self.spn_media_w.setRange(10.0,5000.0); self.spn_media_w.setDecimals(2); self.spn_media_w.setValue(210.0)
        self.spn_media_h = QDoubleSpinBox(); self.spn_media_h.setRange(10.0,5000.0); self.spn_media_h.setDecimals(2); self.spn_media_h.setValue(297.0)
        gx.addWidget(QLabel("Breite (mm):"), rx,0); gx.addWidget(self.spn_media_w, rx,1); rx+=1
        gx.addWidget(QLabel("Höhe (mm):"), rx,0); gx.addWidget(self.spn_media_h, rx,1); rx+=1
        grp_export.setContentLayout(gx); grp_export.setBodyMaxHeight(160); controls.addWidget(grp_export)
        # Status
        self.lbl_status = QLabel("Bereit."); controls.addWidget(self.lbl_status); controls.addStretch()
        # Signals
        self.cmb_media_preset.currentIndexChanged.connect(self._on_media_preset_changed)
        self.spn_media_w.valueChanged.connect(self._on_media_value_changed)
        self.spn_media_h.valueChanged.connect(self._on_media_value_changed)
        # Left panel container
        left = QWidget(); left.setLayout(controls); left.setMinimumWidth(360); left.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Expanding)
        # Preview + Scroll
        self.preview_label = ClickableLabel("Keine Vorschau")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.preview_label.setScaledContents(False)
        self.preview_label.click_callback = self._on_preview_click
        self.scroll_area = QScrollArea(); self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setWidget(self.preview_label)
    # Entfernt: Mausmodus/Zoom per EventFilter
        # Root layout
        root = QHBoxLayout(); root.addWidget(left); root.addWidget(self.scroll_area, 1)
        central.setLayout(root)
        self._update_action_states()

    def _update_action_states(self):
        has_polys = bool(getattr(self, 'polygons', [])) or bool(getattr(self, '_last_polygons', []))
        if hasattr(self, 'btn_move_to_stash'):
            self.btn_move_to_stash.setEnabled(has_polys)

    def _set_current_image(self, img: Image.Image):
        self.pil_img = img
        try:
            rgba = np.array(img.convert("RGBA"))
            self._img_arrays = {
                "rgba": rgba,
                "alpha": rgba[:, :, 3],
                "gray": np.array(img.convert("L")),
                "bgr": cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGR),
            }
        except Exception:
            self._img_arrays = None
        self._poly_version += 1
        self.polygons = []
        self.poly_types = []
        self._last_polygons = []
        self._last_poly_types = []
        self.stash_polygons = getattr(self, 'stash_polygons', [])
        self.stash_types = getattr(self, 'stash_types', [])
        self._refresh_preview()
        self._update_action_states()

    def _update_page_nav(self):
        total = len(self.pdf_pages)
        if total <= 1:
            self.page_nav_widget.setVisible(False)
            self.lbl_page_info.setText("Seite 0/0")
            return
        self.page_nav_widget.setVisible(True)
        self.lbl_page_info.setText(f"Seite {self.pdf_page_index + 1}/{total}")
        self.btn_prev_page.setEnabled(self.pdf_page_index > 0)
        self.btn_next_page.setEnabled(self.pdf_page_index < total - 1)

    def _display_pdf_page(self, index: int):
        if not self.pdf_pages:
            return
        index = max(0, min(index, len(self.pdf_pages) - 1))
        self.pdf_page_index = index
        self._set_current_image(self.pdf_pages[index])
        # Setze die Konturen der aktuellen Seite
        if hasattr(self, 'page_polygons') and self.page_polygons:
            self.polygons = self.page_polygons.get(index, [])
        else:
            self.polygons = []
        base = os.path.basename(self._current_source_path) if self._current_source_path else "Unbenannt"
        self.lbl_status.setText(f"Geladen: {base} (Seite {index + 1}/{len(self.pdf_pages)})")
        self._update_page_nav()
        self._update_action_states()

    def prev_pdf_page(self):
        if self.pdf_page_index > 0:
            self._display_pdf_page(self.pdf_page_index - 1)

    def next_pdf_page(self):
        if self.pdf_pages and self.pdf_page_index < len(self.pdf_pages) - 1:
            self._display_pdf_page(self.pdf_page_index + 1)

    def pick_color(self):
        """Pipetten-Funktion: Nutzer klickt auf Bild um Farbe zu wählen"""
        if self.pil_img is None:
            QMessageBox.information(self, "Hinweis", "Bitte erst ein Bild laden.")
            return
        
        # Aktiviere Pipetten-Modus
        self.pipette_mode = True
        self.lbl_status.setText("⚪ Pipetten-Modus: Klicke auf die Hintergrundfarbe im Bild")
        self.setCursor(Qt.CursorShape.CrossCursor)
    
    def _on_preview_click(self, pos):
        """Callback für Mausklicks auf Preview-Label (für Pipette)"""
        if not self.pipette_mode or not self.pil_img:
            return
        
        # Berechne tatsächliche Bildkoordinaten unter Berücksichtigung von Zoom/Skalierung
        pixmap = self.preview_label.pixmap()
        if not pixmap:
            return
        
        # Skalierung zwischen angezeigte Pixmap und Original
        scale_x = self.pil_img.size[0] / pixmap.width()
        scale_y = self.pil_img.size[1] / pixmap.height()
        
        # Konvertiere Label-Koordinaten zu Bildkoordinaten
        img_x = int(pos.x() * scale_x)
        img_y = int(pos.y() * scale_y)
        
        # Begrenze auf Bildgrenzen
        img_x = max(0, min(img_x, self.pil_img.size[0] - 1))
        img_y = max(0, min(img_y, self.pil_img.size[1] - 1))
        
        # Hole Farbe an dieser Position
        rgb_img = self.pil_img.convert("RGB")
        pixel = rgb_img.getpixel((img_x, img_y))
        
        # Speichere Farbe
        self.picked_color = pixel
        
        # UI: Es gibt kein separates Label mehr; die Farbe wird nur gespeichert und im Status angezeigt.
        
        # Deaktiviere Pipetten-Modus
        self.pipette_mode = False
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.lbl_status.setText(f"Farbe ausgewählt: RGB({pixel[0]}, {pixel[1]}, {pixel[2]})")
        
        # Kein Moduswechsel — Modus 'Farbe (Pipette)' ist entfernt
    
    def open_image(self):  # override with multi-page support
        if not ensure_dependencies(self, auto_install=False):
            pass  # Weiter erlauben: normale Bilder können ohne FitZ geladen werden
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Bild öffnen",
            "",
            "Bilder/PDF (*.png *.jpg *.jpeg *.pdf);;Bilder (*.png *.jpg *.jpeg);;PDF (*.pdf)"
        )
        if not path:
            return
        ext = os.path.splitext(path)[1].lower()
        load_all_pages = False
        page_index = 0
        selected_pages = []
        selected_mode = None
        
        if ext == '.pdf':
            # Multi-page ask mit neuem Dialog
            try:
                import fitz
                doc = fitz.open(path)
                if doc.page_count > 1:
                    dlg = PdfPageSelector(path, doc.page_count, self)
                    if dlg.exec() == QDialog.DialogCode.Accepted:
                        selected_pages = dlg.selected_pages
                        selected_mode = dlg.selected_mode
                        action_mode = dlg.action_mode
                        doc.close()
                    else:
                        doc.close()
                        return
                else:
                    selected_pages = [0]
                    action_mode = "load"
                doc.close()
            except Exception:
                pass
        
        try:
            dpi_val = int(self.spn_dpi.value()) if hasattr(self, 'spn_dpi') else 300
            self._current_source_path = path
            
            if ext == '.pdf' and selected_pages:
                # Lade nur die ausgewählten Seiten
                all_pages = load_pdf_all_pages(path, pdf_dpi=dpi_val)
                self.pdf_pages = [all_pages[i] for i in selected_pages if i < len(all_pages)]
                self.pdf_page_index = 0
                self._display_pdf_page(0)
                
                # Setze den Modus falls ausgewählt
                if selected_mode and hasattr(self, 'cmb_mode'):
                    idx = self.cmb_mode.findText(selected_mode)
                    if idx >= 0:
                        self.cmb_mode.setCurrentIndex(idx)
                
                # Führe Aktion aus basierend auf ausgewähltem Modus
                if action_mode == "analyze":
                    # Analysiere alle Seiten
                    self._analyze_all_pages()
                elif action_mode == "stash":
                    # Analysiere alle Seiten und verschiebe in Ablage
                    self._analyze_all_pages_and_stash()
            else:
                img = load_image_any_with_page(path, pdf_dpi=dpi_val, page_index=page_index)
                self.pdf_pages = [img]
                self.pdf_page_index = 0
                self._display_pdf_page(0)
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Konnte Datei nicht laden:\n{e}")
            return
        
        if len(self.pdf_pages) <= 1:
            self.lbl_status.setText(f"Geladen: {os.path.basename(path)}")

    def _refresh_overlay(self):
        # Placeholder: original overlay refresh logic was removed during patch; for now just rebuild preview
        self._refresh_preview()

    def _refresh_preview(self):
        """Rebuilds the preview with polygon + perf overlay."""
        if self.pil_img is None:
            self.preview_label.setText("Keine Vorschau")
            return

        try:
            import logging
            logging.debug(f"Refreshing preview... zoom_mode={getattr(self, 'zoom_mode', 'N/A')}, zoom_factor={getattr(self, 'zoom_factor', 'N/A')}")
            base_img = self.pil_img.convert("RGBA").copy()
            draw = ImageDraw.Draw(base_img, "RGBA")

            # Draw detected cut polygons (magenta outline only - wie RasterLink)
            cut_color_line = (255, 0, 255, 255)  # Magenta für CutContour
            line_width = 2  # Sichtbare Linienstärke
            for poly in getattr(self, 'polygons', []):
                try:
                    if poly is None or len(poly) < 2:
                        continue
                    pts = [(float(x), float(y)) for x, y in poly]
                    # Nur Outline, keine Füllung (fill=None)
                    draw.polygon(pts, fill=None, outline=cut_color_line, width=line_width)
                except Exception:
                    continue

            # Optional: draw stashed polygons (nur wenn Checkbox aktiv)
            if getattr(self, 'chk_preview_stash', None) and self.chk_preview_stash.isChecked():
                if getattr(self, 'stash_polygons', None):
                    stash_line = (200, 120, 255, 255)  # Helleres Magenta für Stash
                    for poly in self.stash_polygons:
                        try:
                            if poly is None or len(poly) < 2:
                                continue
                            pts = [(float(x), float(y)) for x, y in poly]
                            draw.polygon(pts, fill=None, outline=stash_line, width=line_width)
                        except Exception:
                            continue

            # Perf rectangle preview (cyan) - replicate export calculation
            polygons_all = list(getattr(self, 'polygons', []))
            if getattr(self, 'stash_polygons', None):
                polygons_all += self.stash_polygons
            if polygons_all:
                xs = [float(pt[0]) for poly in polygons_all for pt in poly]
                ys = [float(pt[1]) for poly in polygons_all for pt in poly]
                if xs and ys:
                    dpi = int(self.spn_dpi.value()) if hasattr(self, 'spn_dpi') else 300
                    margin_mm = 5.0
                    radius_mm = 6.0
                    margin_px = mm_to_px(margin_mm, dpi); radius_px = mm_to_px(radius_mm, dpi)
                    min_x = max(0.0, min(xs) - margin_px)
                    min_y = max(0.0, min(ys) - margin_px)
                    max_x = min(self.pil_img.size[0]-1.0, max(xs) + margin_px)
                    max_y = min(self.pil_img.size[1]-1.0, max(ys) + margin_px)

                    def rounded_rect_pts(min_x, min_y, max_x, max_y, r_px, seg=6):
                        r = max(0.0, min(r_px, (max_x-min_x)/2.0, (max_y-min_y)/2.0))
                        if r < 0.5:
                            return [(min_x,min_y),(max_x,min_y),(max_x,max_y),(min_x,max_y)]
                        pts_local: List[Tuple[float,float]] = []
                        def arc(cx, cy, a0, a1):
                            for i in range(seg+1):
                                t = i/seg; ang = a0 + (a1-a0)*t
                                pts_local.append((cx + r*math.cos(ang), cy + r*math.sin(ang)))
                        arc(min_x+r, min_y+r, math.pi, math.pi*1.5)      # bottom left
                        arc(max_x-r, min_y+r, math.pi*1.5, math.pi*2.0)  # bottom right
                        arc(max_x-r, max_y-r, 0.0, math.pi*0.5)          # top right
                        arc(min_x+r, max_y-r, math.pi*0.5, math.pi)      # top left
                        return pts_local

                    # PerfCut deaktiviert - nur CutContour anzeigen
                    # perf_pts = rounded_rect_pts(min_x, min_y, max_x, max_y, radius_px)
                    # if perf_pts:
                    #     perf_line = (0, 255, 255, 220)
                    #     perf_fill = (0, 255, 255, 25)
                    #     try:
                    #         draw.polygon(perf_pts, outline=perf_line, fill=perf_fill)
                    #     except Exception:
                    #         pass

            qimg = pil_to_qimage(base_img)
        except Exception as e:
            # Fallback: just base image
            logger.error(f"Preview generation failed: {e}")
            import traceback
            traceback.print_exc()
            qimg = pil_to_qimage(self.pil_img)

        pixmap = QPixmap.fromImage(qimg)
        if self.zoom_mode == "fit":
            scroll_size = self.scroll_area.viewport().size()
            scaled_pixmap = pixmap.scaled(scroll_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.preview_label.setPixmap(scaled_pixmap)
            self.preview_label.resize(scaled_pixmap.size())
            self.lbl_zoom.setText("Zoom: Fit")
        else:
            w = int(pixmap.width() * self.zoom_factor)
            h = int(pixmap.height() * self.zoom_factor)
            scaled_pixmap = pixmap.scaled(w, h, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.preview_label.setPixmap(scaled_pixmap)
            self.preview_label.resize(scaled_pixmap.size())
            self.lbl_zoom.setText(f"Zoom: {self.zoom_factor:.1f}x")

    def export_pdf(self):
        """Exportiert jede Seite als separate PDF-Datei mit Ebenen + Spotfarben"""
        if not self.pdf_pages:
            QMessageBox.information(self, "Hinweis", "Keine Seiten zum Exportieren.")
            return
        
        # Sammle Polygone und gruppiere nach Seiten
        stash_polygons = getattr(self, 'stash_polygons', [])
        stash_page_info = getattr(self, 'stash_page_info', [])
        
        # Wenn keine Stash-Polygone, prüfe aktuelle Polygone
        if not stash_polygons:
            if self.polygons:
                # Nur aktuelle Seite exportieren
                pages_data = [(self.pdf_page_index, self.pdf_pages[self.pdf_page_index], list(self.polygons))]
            else:
                QMessageBox.information(self, "Hinweis", "Keine Konturen zum Exportieren vorhanden.\nBitte zuerst eine Analyse durchführen.")
                return
        else:
            # Gruppiere Stash-Polygone nach Seiten
            from collections import defaultdict
            page_polygons = defaultdict(list)
            
            for poly, page_label in zip(stash_polygons, stash_page_info):
                # Extrahiere Seitennummer aus Label (z.B. "Seite 1" -> 0)
                try:
                    page_num = int(page_label.split()[-1]) - 1
                except (ValueError, IndexError):
                    page_num = 0
                page_polygons[page_num].append(poly)
            
            # Erstelle Liste von (page_index, image, polygons)
            pages_data = []
            for page_idx in sorted(page_polygons.keys()):
                if page_idx < len(self.pdf_pages):
                    pages_data.append((page_idx, self.pdf_pages[page_idx], page_polygons[page_idx]))
        
        if not pages_data:
            QMessageBox.information(self, "Hinweis", "Keine Konturen zum Exportieren vorhanden.")
            return
        
        # Wähle Zielordner für die PDF-Dateien
        if len(pages_data) > 1:
            folder = QFileDialog.getExistingDirectory(self, "Ordner für PDF-Export auswählen")
            if not folder:
                return
            base_name = "Page"
        else:
            # Einzelne Seite - normaler Datei-Dialog
            path, _ = QFileDialog.getSaveFileName(self, "PDF speichern", "CutPerf.pdf", "PDF (*.pdf)")
            if not path:
                return
            folder = os.path.dirname(path)
            base_name = os.path.splitext(os.path.basename(path))[0]
            pages_data = [(pages_data[0][0], pages_data[0][1], pages_data[0][2])]  # Nur eine Seite
        
        # Exportiere jede Seite einzeln
        exported_files = []
        for idx, (page_idx, page_img, polygons) in enumerate(pages_data):
            if len(pages_data) > 1:
                filename = f"{base_name}_{page_idx + 1:03d}.pdf"
                filepath = os.path.join(folder, filename)
            else:
                filepath = os.path.join(folder, f"{base_name}.pdf")
            
            success = self._export_single_page_pdf(filepath, page_img, polygons)
            if success:
                exported_files.append(filepath)
        
        if exported_files:
            self.lbl_status.setText(f"{len(exported_files)} PDF-Datei(en) exportiert")
            QMessageBox.information(self, "Export erfolgreich", f"{len(exported_files)} Seite(n) exportiert nach:\n{folder}")
        else:
            QMessageBox.warning(self, "Fehler", "Keine Dateien konnten exportiert werden.")
    
    def _export_single_page_pdf(self, path: str, page_img: Image.Image, polygons: List[np.ndarray]) -> bool:
        """Exportiert eine einzelne Seite als PDF"""
        try:
            import zlib, math
            
            # Seitengröße bestimmen
            preset = self.cmb_media_preset.currentText() if hasattr(self, 'cmb_media_preset') else "Auto (Bildgröße)"
            dpi = int(self.spn_dpi.value()) if hasattr(self, 'spn_dpi') else 300
            w_px, h_px = page_img.size
            
            if preset == "Auto (Bildgröße)":
                w_pt = (w_px * 72.0) / max(1, dpi)
                h_pt = (h_px * 72.0) / max(1, dpi)
            else:
                w_mm = self.spn_media_w.value(); h_mm = self.spn_media_h.value()
                w_pt = w_mm / 25.4 * 72.0; h_pt = h_mm / 25.4 * 72.0
            
            scale = min(w_pt / max(1.0, float(w_px)), h_pt / max(1.0, float(h_px)))
            offset_x = (w_pt - w_px * scale) * 0.5
            offset_y = (h_pt - h_px * scale) * 0.5
            embed_art = getattr(self, 'chk_embed_artwork', None) is None or self.chk_embed_artwork.isChecked()
            line_w_pt = 0.25
            
            # Helper-Funktionen
            def poly_to_path(poly: np.ndarray) -> str:
                if poly is None or len(poly) < 2:
                    return ""
                parts = []
                x0, y0 = poly[0]
                parts.append(f"{(offset_x + x0*scale):.3f} {(offset_y + (h_px - y0)*scale):.3f} m")
                for x, y in poly[1:]:
                    parts.append(f"{(offset_x + x*scale):.3f} {(offset_y + (h_px - y)*scale):.3f} l")
                parts.append("h")
                return "\n".join(parts)
            
            def rounded_rect(min_x, min_y, max_x, max_y, r_px, seg=6):
                r = max(0.0, min(r_px, (max_x-min_x)/2.0, (max_y-min_y)/2.0))
                if r < 0.5:
                    return np.array([[min_x,min_y],[max_x,min_y],[max_x,max_y],[min_x,max_y]], dtype=np.float32)
                pts: List[Tuple[float,float]] = []
                def arc(cx, cy, a0, a1):
                    for i in range(seg+1):
                        t = i/seg; ang = a0 + (a1-a0)*t
                        pts.append((cx + r*math.cos(ang), cy + r*math.sin(ang)))
                arc(min_x+r, min_y+r, math.pi, math.pi*1.5)
                arc(max_x-r, min_y+r, math.pi*1.5, math.pi*2.0)
                arc(max_x-r, max_y-r, 0.0, math.pi*0.5)
                arc(min_x+r, max_y-r, math.pi*0.5, math.pi)
                return np.array(pts, dtype=np.float32)
            
            # PDF Objektliste
            objects: List[bytes] = []
            def add(data: bytes) -> int:
                objects.append(data); return len(objects)
            
            add(b"<<>>")  # 1 Catalog placeholder
            add(b"<<>>")  # 2 Pages placeholder
            
            ocg_art = add(b"<< /Type /OCG /Name (Artwork) >>")
            ocg_cut = add(b"<< /Type /OCG /Name (CutContour) >>")
            fn_cut = add(b"<< /FunctionType 2 /Domain [0 1] /Range [0 1 0 1 0 1 0 1] /C0 [0 1 0 0] /C1 [0 1 0 0] /N 1 >>")
            
            # Artwork
            img_obj_num = None
            if embed_art:
                try:
                    rgba = page_img.convert("RGBA")
                    white = Image.new("RGBA", rgba.size, (255,255,255,255))
                    merged = Image.alpha_composite(white, rgba).convert("RGB")
                except Exception:
                    merged = page_img.convert("RGB")
                iw, ih = merged.size
                comp = zlib.compress(merged.tobytes())
                img_obj = (f"<< /Type /XObject /Subtype /Image /Width {iw} /Height {ih} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /FlateDecode /Length {len(comp)} >>\nstream\n".encode('utf-8') + comp + b"\nendstream")
                img_obj_num = add(img_obj)
            
            # Content Stream
            content: List[str] = []
            if embed_art and img_obj_num:
                img_w_pt = w_px * scale
                img_h_pt = h_px * scale
                content += [
                    "/OC /OC_ART BDC",
                    "q",
                    f"{img_w_pt:.3f} 0 0 {img_h_pt:.3f} {offset_x:.3f} {offset_y:.3f} cm",
                    f"/Im{img_obj_num} Do",
                    "Q",
                    "EMC"
                ]
            
            # Cut Konturen
            content += ["/OC /OC_CUT BDC", f"q\n{line_w_pt:.3f} w\n0 J 0 j", "/CS1 CS 1 SCN"]
            for p in polygons:
                path_s = poly_to_path(p)
                if path_s:
                    content.append(path_s)
                    content.append("S")
            content += ["Q", "EMC"]
            
            content_bytes = "\n".join(content).encode('utf-8')
            content_obj = b"<< /Length " + str(len(content_bytes)).encode('utf-8') + b" >>\nstream\n" + content_bytes + b"\nendstream"
            content_num = add(content_obj)
            
            # Page-Objekt
            cs_cut = f"[/Separation /CutContour /DeviceCMYK {fn_cut} 0 R]".encode('utf-8')
            xobj_part = f"/XObject <</Im{img_obj_num} {img_obj_num} 0 R>>".encode('utf-8') if embed_art and img_obj_num else b""
            res = b"/Resources << /ProcSet [/PDF /ImageC] /Properties <</OC_ART %d 0 R /OC_CUT %d 0 R>> /ColorSpace <</CS1 %s>> %s >>" % (ocg_art, ocg_cut, cs_cut, xobj_part)
            page_obj = (f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {w_pt:.3f} {h_pt:.3f}] ".encode('utf-8') + res + f" /Contents {content_num} 0 R >>".encode('utf-8'))
            page_num = add(page_obj)
            
            # Pages Dictionary
            objects[1] = f"<< /Type /Pages /Kids [{page_num} 0 R] /Count 1 >>".encode('utf-8')
            
            # Catalog
            ocprops = f"/OCProperties << /OCGs [{ocg_art} 0 R {ocg_cut} 0 R] /D << /Order [(Artwork) (CutContour)] /ON [{ocg_art} 0 R {ocg_cut} 0 R] >> >>"
            objects[0] = f"<< /Type /Catalog /Pages 2 0 R {ocprops} >>".encode('utf-8')
            
            # Schreiben
            with open(path, 'wb') as f:
                f.write(b"%PDF-1.6\n%\xE2\xE3\xCF\xD3\n")
                offsets = [0]
                for idx, obj in enumerate(objects, start=1):
                    offsets.append(f.tell())
                    f.write(f"{idx} 0 obj\n".encode('utf-8'))
                    f.write(obj)
                    f.write(b"\nendobj\n")
                startxref = f.tell()
                f.write(f"xref\n0 {len(objects)+1}\n".encode('utf-8'))
                f.write(b"0000000000 65535 f \n")
                for off in offsets[1:]:
                    f.write(f"{off:010d} 00000 n \n".encode('utf-8'))
                f.write((f"trailer << /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{startxref}\n%%EOF").encode('utf-8'))
            
            return True
        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(f"Fehler beim Export von {path}: {e}")
            return False

    def run_analysis(self):
        if self.pil_img is None:
            QMessageBox.information(self, "Hinweis", "Kein Bild geladen.")
            return
        # Reset previous analysis results
        self.polygons = []
        self.poly_types = []
        self._last_polygons = []
        self._last_poly_types = []
        self._update_action_states()
        mode = self.cmb_mode.currentText()
        
        # Hole Offset-Einstellung und Glättung (für alle Modi)
        offset_mm = self.dsp_offset_mm.value()
        offset_px = mm_to_px(offset_mm, self.spn_dpi.value()) if abs(offset_mm) > 1e-6 else 0.0
        smooth_iterations = self.spn_smooth.value()
        
        if mode == "Transparenz (Alpha)":
            # Verwende Standardwerte, UI für Parameter wurde entfernt
            min_area_px2 = self.default_area_px2
            masks = detect_mask_alpha(
                self.pil_img,
                self.default_alpha,
                self.default_blur,
                self.default_morph,
                self.default_invert,
                min_area_px2
            )
            if not masks:
                QMessageBox.information(self, "Hinweis", "Keine Sticker gefunden.")
                return
            for mask in masks:
                # Wende Offset an
                working_mask = dilate_mask(mask, offset_px) if abs(offset_px) > 1e-6 else mask
                poly = contour_from_mask(working_mask, self.dsp_epsilon.value(), smooth_iterations)
                if poly is not None:
                    self.polygons.append(poly)
                    self.poly_types.append("Cut")
        elif mode == "Helligkeit (Threshold)":
            min_area_px2 = self.default_area_px2
            masks = detect_mask_gray(
                self.pil_img,
                self.default_gray,
                self.default_blur,
                self.default_morph,
                self.default_invert,
                min_area_px2
            )
            if not masks:
                QMessageBox.information(self, "Hinweis", "Keine Sticker gefunden.")
                return
            for mask in masks:
                # Wende Offset an
                working_mask = dilate_mask(mask, offset_px) if abs(offset_px) > 1e-6 else mask
                poly = contour_from_mask(working_mask, self.dsp_epsilon.value(), smooth_iterations)
                if poly is not None:
                    self.polygons.append(poly)
                    self.poly_types.append("Cut")
        elif mode == "Outline (Schwarz/Farbe)":
            min_area_px2 = self.default_area_px2
            masks = detect_mask_black_per_sticker(
                self.pil_img,
                self.default_black,
                self.default_blur,
                self.default_morph,
                min_area_px2
            )
            if not masks:
                QMessageBox.information(self, "Hinweis", "Keine Sticker gefunden.")
                return
            for mask in masks:
                # Wende Offset an falls gewünscht
                working_mask = dilate_mask(mask, offset_px) if abs(offset_px) > 1e-6 else mask
                poly = contour_from_mask(working_mask, self.dsp_epsilon.value(), smooth_iterations)
                if poly is not None:
                    self.polygons.append(poly)
                    self.poly_types.append("Cut")
        # Farbe (Pipette) entfernt — dieser Modus ist nicht mehr verfügbar
        else:
            QMessageBox.critical(self, "Fehler", f"Unbekannter Modus: {mode}")
            return
        self._poly_version += 1
        # Speichere die Konturen für die aktuelle Seite
        if not hasattr(self, 'page_polygons'):
            self.page_polygons = {}
        self.page_polygons[self.pdf_page_index] = self.polygons.copy() if self.polygons else []
        self._refresh_preview()
        self._update_action_states()
        self._last_polygons = list(self.polygons)
        self._last_poly_types = list(self.poly_types)
        self.lbl_status.setText(f"Analyse abgeschlossen: {len(self.polygons)} Konturen gefunden")

    def zoom_out(self):
        if self.pil_img is None:
            return
        self.zoom_mode = "manual"
        self.zoom_factor *= 0.8
        self._refresh_preview()

    def zoom_in(self):
        if self.pil_img is None:
            return
        self.zoom_mode = "manual"
        self.zoom_factor *= 1.25
        self._refresh_preview()

    def zoom_reset(self):
        if self.pil_img is None:
            return
        self.zoom_mode = "manual"
        self.zoom_factor = 1.0
        self._refresh_preview()

    def zoom_fit(self):
        self.zoom_mode = "fit"
        self.lbl_zoom.setText("Zoom: Fit")
        self._refresh_preview()
    
    # Entfernt: Mausmodus-EventFilter (Ctrl+Mausrad Zoom)

    def stash_add(self):
        self.stash_polygons = getattr(self, 'stash_polygons', [])
        self.stash_types = getattr(self, 'stash_types', [])
        self.stash_page_info = getattr(self, 'stash_page_info', [])
        page_label = self._get_current_page_label()
        self.stash_polygons.extend(self.polygons)
        self.stash_types.extend(self.poly_types)
        for _ in self.polygons:
            self.stash_page_info.append(page_label)
        self._update_stash_list()

    def stash_clear(self):
        self.stash_polygons = []
        self.stash_types = []
        self.stash_page_info = []
        self._update_stash_list()

    def _get_current_page_label(self):
        if self.pdf_pages and len(self.pdf_pages) > 1:
            return f"Seite {self.pdf_page_index + 1}"
        elif self._current_source_path:
            return os.path.basename(self._current_source_path)
        else:
            return "Unbenannt"

    def _update_stash_list(self):
        if not hasattr(self, 'list_stash'):
            return
        self.list_stash.clear()
        page_counts = {}
        for page_label in getattr(self, 'stash_page_info', []):
            page_counts[page_label] = page_counts.get(page_label, 0) + 1
        for page_label, count in page_counts.items():
            self.list_stash.addItem(f"{page_label}: {count} Kontur(en)")
        total = len(getattr(self, 'stash_polygons', []))
        if total > 0:
            self.list_stash.addItem(f"──────────────────")
            self.list_stash.addItem(f"Gesamt: {total} Kontur(en)")

    def move_analysis_to_stash(self):
        logger.debug(f"move_analysis_to_stash: polygons={len(self.polygons)}, last={len(getattr(self, '_last_polygons', []))}")
        if not self.polygons:
            if hasattr(self, '_last_polygons') and self._last_polygons:
                self.polygons = self._last_polygons
                self.poly_types = self._last_poly_types
                logger.debug(f"Restored from last_polygons, count={len(self.polygons)}")
            else:
                logger.debug("No polygons to stash")
                QMessageBox.information(self, "Hinweis", "Keine Konturen vorhanden.")
                return
        self.stash_polygons = getattr(self, 'stash_polygons', [])
        self.stash_types = getattr(self, 'stash_types', [])
        self.stash_page_info = getattr(self, 'stash_page_info', [])
        page_label = self._get_current_page_label()
        count = len(self.polygons)
        logger.debug(f"Moving {count} polygons to stash")
        self.stash_polygons.extend(self.polygons)
        self.stash_types.extend(self.poly_types)
        for _ in self.polygons:
            self.stash_page_info.append(page_label)
        logger.debug(f"Stash now has {len(self.stash_polygons)} total polygons")
        self.polygons = []
        self.poly_types = []
        self._last_polygons = []
        self._last_poly_types = []
        self._poly_version += 1
        self._refresh_preview()
        self._update_stash_list()
        self._update_action_states()
        self.lbl_status.setText(f"{count} Konturen in die Ablage verschoben. Jetzt nächste Seite analysieren.")

    def _analyze_all_pages(self):
        """Analysiert alle geladenen PDF-Seiten nacheinander"""
        if not self.pdf_pages:
            return
        
        total = len(self.pdf_pages)
        for i in range(total):
            self._display_pdf_page(i)
            QApplication.processEvents()  # UI aktualisieren
            self.run_analysis()
            QApplication.processEvents()
        
        self.lbl_status.setText(f"Alle {total} Seiten analysiert. Letzte Seite aktiv.")
    
    def _analyze_all_pages_and_stash(self):
        """Analysiert alle geladenen PDF-Seiten und verschiebt sie in die Ablage"""
        if not self.pdf_pages:
            return
        
        total = len(self.pdf_pages)
        total_contours = 0
        
        for i in range(total):
            self._display_pdf_page(i)
            QApplication.processEvents()  # UI aktualisieren
            self.run_analysis()
            QApplication.processEvents()
            
            # Verschiebe in Ablage
            if self.polygons:
                count = len(self.polygons)
                total_contours += count
                self.move_analysis_to_stash()
                QApplication.processEvents()
        
        self.lbl_status.setText(f"Alle {total} Seiten analysiert. {total_contours} Konturen in Ablage.")
        
        # Zeige erste Seite wieder an
        if self.pdf_pages:
            self._display_pdf_page(0)

    def _on_media_preset_changed(self):
        preset = self.cmb_media_preset.currentText()
        if preset == "A4 Hoch":
            self.spn_media_w.setValue(210.0)
            self.spn_media_h.setValue(297.0)
        elif preset == "A4 Quer":
            self.spn_media_w.setValue(297.0)
            self.spn_media_h.setValue(210.0)
        # Add other presets as needed

    def _on_media_value_changed(self):
        self.cmb_media_preset.setCurrentText("Benutzerdefiniert")

    def _load_settings(self):
        settings = QSettings("StickerApp", "CC2")
        # Load settings if needed

    def _toggle_theme(self):
        self._dark_mode = not self._dark_mode
        if self._dark_mode:
            self._apply_dark_palette()
        else:
            self._apply_light_palette()

    def _apply_light_palette(self):
        # Light mode with modern glassmorphism
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #f8fafc, stop:0.5 #e2e8f0, stop:1 #f8fafc);
            }
            QMenuBar {
                background: rgba(255, 255, 255, 0.8);
                border-bottom: 1px solid rgba(226, 232, 240, 0.6);
                padding: 6px 12px;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
                font-size: 11pt;
            }
            QMenuBar::item {
                padding: 8px 16px;
                border-radius: 8px;
                color: #334155;
            }
            QMenuBar::item:selected {
                background: rgba(99, 102, 241, 0.15);
                color: #6366f1;
            }
            QMenu {
                background: rgba(255, 255, 255, 0.95);
                border: 1px solid rgba(226, 232, 240, 0.8);
                border-radius: 12px;
                padding: 8px;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
            }
            QMenu::item {
                padding: 10px 24px;
                border-radius: 8px;
                color: #334155;
            }
            QMenu::item:selected {
                background: rgba(99, 102, 241, 0.15);
                color: #6366f1;
            }
            QGroupBox {
                background: rgba(255, 255, 255, 0.8);
                border: 2px solid rgba(226, 232, 240, 0.8);
                border-radius: 16px;
                margin-top: 12px;
                padding: 16px;
                font-weight: 600;
                font-size: 11pt;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 16px;
                padding: 4px 12px;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 rgba(16, 185, 129, 0.9), 
                    stop:1 rgba(5, 150, 105, 0.9));
                color: white;
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 12px;
                padding: 10px 20px;
                font-weight: 600;
                font-size: 10pt;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 rgba(16, 185, 129, 1.0), 
                    stop:1 rgba(5, 150, 105, 1.0));
                box-shadow: 0 0 10px rgba(16, 185, 129, 0.4);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 rgba(5, 150, 105, 1.0), 
                    stop:1 rgba(4, 120, 87, 1.0));
            }
            QStatusBar {
                background: rgba(255, 255, 255, 0.8);
                border-top: 1px solid rgba(226, 232, 240, 0.6);
                padding: 8px;
            }
        """)
        self.theme_action.setText("🌙 Dark Mode")
        self.theme_action.setChecked(False)

    def _apply_dark_palette(self):
        # Dark mode with minimal colors
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #0f172a, stop:0.5 #1e293b, stop:1 #0f172a);
            }
            QMenuBar {
                background: rgba(30, 41, 59, 0.9);
                border-bottom: 1px solid rgba(71, 85, 105, 0.6);
                padding: 6px 12px;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
                font-size: 11pt;
            }
            QMenuBar::item {
                padding: 8px 16px;
                border-radius: 8px;
                color: #e2e8f0;
            }
            QMenuBar::item:selected {
                background: rgba(100, 116, 139, 0.3);
                color: #cbd5e1;
            }
            QMenu {
                background: rgba(30, 41, 59, 0.95);
                border: 1px solid rgba(71, 85, 105, 0.8);
                border-radius: 12px;
                padding: 8px;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
            }
            QMenu::item {
                padding: 10px 24px;
                border-radius: 8px;
                color: #e2e8f0;
            }
            QMenu::item:selected {
                background: rgba(100, 116, 139, 0.3);
                color: #cbd5e1;
            }
            QGroupBox {
                background: rgba(30, 41, 59, 0.6);
                border: 2px solid rgba(71, 85, 105, 0.6);
                border-radius: 16px;
                margin-top: 12px;
                padding: 16px;
                font-weight: 600;
                font-size: 11pt;
                color: #e2e8f0;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 16px;
                padding: 4px 12px;
                color: #cbd5e1;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 rgba(71, 85, 105, 0.8), 
                    stop:1 rgba(51, 65, 85, 0.8));
                color: #cbd5e1;
                border: 2px solid rgba(100, 116, 139, 0.3);
                border-radius: 12px;
                padding: 10px 20px;
                font-weight: 600;
                font-size: 10pt;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 rgba(71, 85, 105, 0.9), 
                    stop:1 rgba(51, 65, 85, 0.9));
                box-shadow: 0 0 10px rgba(100, 116, 139, 0.3);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 rgba(51, 65, 85, 1.0), 
                    stop:1 rgba(30, 41, 59, 1.0));
            }
            QStatusBar {
                background: rgba(30, 41, 59, 0.9);
                border-top: 1px solid rgba(71, 85, 105, 0.6);
                padding: 8px;
                color: #e2e8f0;
            }
            QLabel {
                color: #e2e8f0;
            }
            QSpinBox, QDoubleSpinBox, QComboBox {
                background: rgba(30, 41, 59, 0.8);
                border: 2px solid rgba(71, 85, 105, 0.6);
                border-radius: 8px;
                padding: 6px;
                color: #e2e8f0;
            }
            QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover {
                border: 2px solid rgba(100, 116, 139, 0.8);
            }
            QCheckBox {
                color: #e2e8f0;
            }
            QListWidget {
                background: rgba(30, 41, 59, 0.6);
                border: 2px solid rgba(71, 85, 105, 0.6);
                border-radius: 12px;
                color: #e2e8f0;
            }
        """)
        self.theme_action.setText("☀️ Light Mode")
        self.theme_action.setChecked(True)

    def _save_settings(self):
        settings = QSettings("StickerApp", "CC2")
        # Save settings if needed

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
