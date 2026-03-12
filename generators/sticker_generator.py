"""Sticker Generator Module.

Contains the StickerGenerator class for generating sticker images.
"""
import logging
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
import math
from PIL import Image, ImageDraw, ImageFont

try:
    import fitz  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    fitz = None
from core.models import StickerConfig, SymbolType
from core.paths import PathManager

logger = logging.getLogger(__name__)

def _resolve_path(path_str: str) -> Path:
    """Resolve a path string to absolute path, handling relative paths."""
    if not path_str:
        return PathManager.BASE_DIR
    p = Path(path_str)
    # If already absolute, return it
    if p.is_absolute():
        return p
    # Otherwise, resolve relative to BASE_DIR
    return PathManager.BASE_DIR / p

class StickerGenerator:
    """Generator for individual LOTO stickers."""

    def __init__(self, cfg: StickerConfig):
        self.cfg = cfg
        self._img_cache: Dict[str, Image.Image] = {}
        self._mask_cache: Dict[str, Image.Image] = {}
        self._sym_cache: Dict[str, Image.Image] = {}
        self._font_cache: Dict[int, ImageFont.FreeTypeFont] = {}
        self._qr_cache: Dict[str, Image.Image] = {}
        self._last_text_mask: Optional[Image.Image] = None

    # ---------------- Internal helpers -----------------
    def _load_symbol(self, st: SymbolType, size: int) -> Optional[Image.Image]:
        key = f"{st.name}_{size}"
        if key in self._sym_cache:
            return self._sym_cache[key]
        symbols_dir = getattr(self.cfg, 'symbols_dir', None)
        if not symbols_dir:
            return None
        symbols_path = _resolve_path(symbols_dir)
        p = symbols_path / f"{st.name.lower()}.png"
        if not p.exists():
            return None
        img = Image.open(p).convert("RGBA")
        img.thumbnail((size, size), Image.Resampling.LANCZOS)
        self._sym_cache[key] = img
        return img

    def _round_mask(self, size: Tuple[int, int], radius: int) -> Image.Image:
        r = max(0, min(radius, min(size) // 2))
        mask = Image.new("L", size, 0)
        ImageDraw.Draw(mask).rounded_rectangle([(0, 0), size], radius=r, fill=255)
        return mask

    def _load_qr_image(self) -> Optional[Image.Image]:
        qr_path = getattr(self.cfg, 'qr_image_path', None)
        if not qr_path:
            return None
        try:
            path_obj = Path(qr_path)
        except Exception:
            return None
        if not path_obj.exists():
            return None

        cache_key = f"{path_obj.resolve()}::{path_obj.stat().st_mtime}"
        if cache_key in self._qr_cache:
            return self._qr_cache[cache_key]

        suffix = path_obj.suffix.lower()
        img: Optional[Image.Image]
        if suffix == '.pdf':
            img = self._load_pdf_as_image(path_obj)
        else:
            img = self._load_raster_image(path_obj)

        if img is None:
            return None

        self._qr_cache[cache_key] = img
        return img

    def _load_raster_image(self, path_obj: Path) -> Optional[Image.Image]:
        try:
            return Image.open(path_obj).convert("RGBA")
        except Exception as exc:
            logger.warning("QR Bild konnte nicht geladen werden (%s): %s", path_obj, exc)
            return None

    def _load_pdf_as_image(self, path_obj: Path) -> Optional[Image.Image]:
        if fitz is None:
            logger.warning("PDF-Unterstützung erfordert PyMuPDF (pip install PyMuPDF)")
            return None
        try:
            with fitz.open(path_obj) as doc:
                if doc.page_count == 0:
                    logger.warning("PDF %s enthält keine Seiten", path_obj)
                    return None
                page = doc.load_page(0)
                pix = page.get_pixmap(alpha=True)
                mode = "RGBA" if pix.alpha else "RGB"
                img = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
                if not pix.alpha:
                    img = img.convert("RGBA")
                return img
        except Exception as exc:
            logger.warning("PDF konnte nicht als QR-Bild geladen werden (%s): %s", path_obj, exc)
            return None

    def _get_font(self, size_mm: float) -> ImageFont.ImageFont:  # type: ignore[override]
        size_px = max(1, int(size_mm * self.cfg.px_per_mm))
        if size_px not in self._font_cache:
            try:
                font_path = _resolve_path(self.cfg.font_path)
                self._font_cache[size_px] = ImageFont.truetype(str(font_path), size_px)  # type: ignore[arg-type]
            except Exception:
                # Fallback to default bitmap font
                self._font_cache[size_px] = ImageFont.load_default()  # type: ignore[assignment]
        # Stored objects are FreeTypeFont or default bitmap font; both implement ImageFont interface used here.
        return self._font_cache[size_px]  # type: ignore[return-value]

    def _wrap_text(self, text: str, font: ImageFont.ImageFont, max_width: int) -> List[str]:
        if not text:
            return [""]
        if (font.getbbox(text)[2] - font.getbbox(text)[0]) <= max_width:
            return [text]
        words = text.split()
        lines: List[str] = []
        current = ""
        for w in words:
            test = f"{current} {w}".strip()
            if (font.getbbox(test)[2] - font.getbbox(test)[0]) <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                    current = w
                else:
                    lines.append(w)
                    current = ""
        if current:
            lines.append(current)
        return lines or [""]

    # ---------------- Public API -----------------
    def generate(self, st: SymbolType, lines: List[str]) -> Image.Image:
        """Generate a sticker image for the given symbol + text lines."""
        cache_key = (
            st.name, tuple(lines), self.cfg.font_size_mm, self.cfg.line_height_mm,
            self.cfg.sticker_color, self.cfg.symbol_size_mm, self.cfg.symbol_offset_x_mm,
            self.cfg.symbol_offset_y_mm, self.cfg.width_mm, self.cfg.height_mm,
            getattr(self.cfg, 'text_offset_x', 0), getattr(self.cfg, 'text_offset_y', 0),
            getattr(self.cfg, 'qr_mode_enabled', False), getattr(self.cfg, 'qr_image_path', None),
            getattr(self.cfg, 'qr_placeholder_bg', '#FFFFFF'), getattr(self.cfg, 'qr_placeholder_text', 'QR')
        )
        key_str = repr(cache_key)
        if key_str in self._img_cache:
            self._last_text_mask = self._mask_cache.get(key_str)
            return self._img_cache[key_str]

        if self.cfg.auto_adjust:
            self._auto_adjust(lines)

        w, h = self.cfg.size_px
        img = Image.new("RGBA", (w, h), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        text_mask = Image.new("L", (w, h), 0)
        mask_draw = ImageDraw.Draw(text_mask)

        # Background sticker shape
        bw = getattr(self.cfg, 'border_width', 1)
        draw.rounded_rectangle(
            [(0, 0), (w, h)],
            radius=self.cfg.corner_radius,
            fill=self.cfg.sticker_color,
            outline="black" if bw else None,
            width=bw
        )

        # Detect form type based on dimensions and corner radius
        aspect_ratio = w / h if h > 0 else 1.0
        is_square = 0.85 <= aspect_ratio <= 1.15
        is_circle = is_square and self.cfg.corner_radius >= min(w, h) * 0.4
        is_rectangle = aspect_ratio > 2.0 or aspect_ratio < 0.5
        
        # Choose layout based on form
        if is_circle:
            self._generate_circle_layout(img, draw, text_mask, mask_draw, st, lines, w, h)
        elif is_square:
            self._generate_square_layout(img, draw, text_mask, mask_draw, st, lines, w, h)
        else:
            self._generate_rectangle_layout(img, draw, text_mask, mask_draw, st, lines, w, h)

        self._manage_cache(self._img_cache, key_str, img)
        self._manage_cache(self._mask_cache, key_str, text_mask)
        self._last_text_mask = text_mask
        return img
    
    def _generate_rectangle_layout(self, img, draw, text_mask, mask_draw, st, lines, w, h):
        """Layout für rechteckige Sticker: Symbol links, Text rechts"""
        symbol_size_px = int(self.cfg.symbol_size_mm * self.cfg.px_per_mm)
        symbol_offset_x_px = int(self.cfg.symbol_offset_x_mm * self.cfg.px_per_mm)
        symbol_offset_y_px = int(self.cfg.symbol_offset_y_mm * self.cfg.px_per_mm)

        # Symbol
        sym = self._load_symbol(st, symbol_size_px)
        if sym:
            mask = self._round_mask(sym.size, self.cfg.symbol_corner_radius)
            img.paste(sym, (symbol_offset_x_px, symbol_offset_y_px), mask)

        qr_enabled = getattr(self.cfg, 'qr_mode_enabled', False)
        qr_path = getattr(self.cfg, 'qr_image_path', None)
        
        # QR nur anzeigen wenn BEIDE Bedingungen erfüllt: mode enabled UND path vorhanden
        qr_should_show = qr_enabled and qr_path and str(qr_path).strip()
        logger.debug(f"Rectangle Layout: qr_enabled={qr_enabled}, qr_path={qr_path}, qr_should_show={qr_should_show}")
        
        qr_block_px = symbol_size_px
        text_margin_px = 20

        if qr_should_show:
            # QR-Code rechts oben positionieren - vertikal zentriert im Sticker
            qr_x = max(0, w - symbol_offset_x_px - qr_block_px)
            # Vertikal zentrieren statt an Symbol-Position
            qr_y = (h - qr_block_px) // 2
            qr_rect = [qr_x, qr_y, qr_x + qr_block_px, qr_y + qr_block_px]
            qr_bg = getattr(self.cfg, 'qr_placeholder_bg', "#FFFFFF")
            
            draw.rounded_rectangle(qr_rect, radius=self.cfg.symbol_corner_radius, fill=qr_bg, outline=None)

            qr_img_loaded = self._load_qr_image()
            if qr_img_loaded:
                qr_img = qr_img_loaded.copy()
                qr_img.thumbnail((qr_block_px, qr_block_px), Image.Resampling.LANCZOS)
                paste_x = qr_x + (qr_block_px - qr_img.width) // 2
                paste_y = qr_y + (qr_block_px - qr_img.height) // 2
                mask_qr = self._round_mask(qr_img.size, self.cfg.symbol_corner_radius)
                img.paste(qr_img, (paste_x, paste_y), mask_qr)
            else:
                placeholder = (getattr(self.cfg, 'qr_placeholder_text', 'QR') or 'QR').upper()
                qr_font = self._get_font(self.cfg.font_size_mm)
                bb = qr_font.getbbox(placeholder)
                pw, ph = bb[2] - bb[0], bb[3] - bb[1]
                draw.text((qr_x + (qr_block_px - pw) // 2, qr_y + (qr_block_px - ph) // 2), placeholder, fill="black", font=qr_font)
            
            draw.rounded_rectangle(qr_rect, radius=self.cfg.symbol_corner_radius, fill=None, outline="black", width=3)

        qr_reserved_px = symbol_offset_x_px + qr_block_px + text_margin_px if qr_should_show else 0
        font = self._get_font(self.cfg.font_size_mm)

        header_token = "#LOTOPOINT"
        if len(lines) >= 2:
            line1 = lines[0].upper()
            line2 = (lines[1] or "").upper()
            header = line1 if line1 == "WELCOME TO" else f"{header_token} - {line1}" if line1 else header_token
            txts = [header]
            if line2:
                txts.append(line2)
            if len(lines) > 2 and lines[2]:
                txts.append(lines[2].upper())
        else:
            txts = [header_token] + [ln.upper() for ln in lines]
        
        print(f"*** STICKER GEN DEBUG (rectangle): lines={lines}, txts={txts} ***")

        text_area_start = symbol_offset_x_px + symbol_size_px + text_margin_px
        text_area_width = max(10, w - text_area_start - text_margin_px - qr_reserved_px)

        wrapped = []
        for t in txts:
            wrapped.extend(self._wrap_text(t, font, text_area_width))
        if not wrapped:
            wrapped = [""]

        self._draw_wrapped_text(draw, mask_draw, font, wrapped, text_area_start, text_area_width, h)
    
    def _generate_square_layout(self, img, draw, text_mask, mask_draw, st, lines, w, h):
        """Layout für quadratische Sticker: Symbol oben, Text unten zentriert"""
        symbol_size_px = int(self.cfg.symbol_size_mm * self.cfg.px_per_mm)
        margin = int(w * 0.08)
        
        # Symbol oben zentriert
        sym = self._load_symbol(st, symbol_size_px)
        if sym:
            symbol_x = (w - symbol_size_px) // 2
            symbol_y = margin
            mask = self._round_mask(sym.size, self.cfg.symbol_corner_radius)
            img.paste(sym, (symbol_x, symbol_y), mask)

        font = self._get_font(self.cfg.font_size_mm)
        
        # Build text
        header_token = "#LOTOPOINT"
        if len(lines) >= 2:
            line1 = lines[0].upper()
            line2 = (lines[1] or "").upper()
            header = line1 if line1 == "WELCOME TO" else f"{header_token} - {line1}" if line1 else header_token
            txts = [header]
            if line2:
                txts.append(line2)
            if len(lines) > 2 and lines[2]:
                txts.append(lines[2].upper())
        else:
            txts = [header_token] + [ln.upper() for ln in lines]

        text_area_width = w - 2 * margin
        wrapped = []
        for t in txts:
            wrapped.extend(self._wrap_text(t, font, text_area_width))
        if not wrapped:
            wrapped = [""]

        # Text unter Symbol, zentriert
        text_start_y = symbol_y + symbol_size_px + margin
        self._draw_wrapped_text_centered(draw, mask_draw, font, wrapped, margin, w - margin, text_start_y, h)
    
    def _generate_circle_layout(self, img, draw, text_mask, mask_draw, st, lines, w, h):
        """Layout für runde Sticker: Symbol oben, Text unten zentriert"""
        symbol_size_px = int(self.cfg.symbol_size_mm * self.cfg.px_per_mm)
        margin = int(w * 0.1)
        
        # Symbol oben zentriert
        sym = self._load_symbol(st, symbol_size_px)
        if sym:
            symbol_x = (w - symbol_size_px) // 2
            symbol_y = margin
            mask = self._round_mask(sym.size, self.cfg.symbol_corner_radius)
            img.paste(sym, (symbol_x, symbol_y), mask)

        font = self._get_font(self.cfg.font_size_mm)
        
        # Build text
        header_token = "#LOTOPOINT"
        if len(lines) >= 2:
            line1 = lines[0].upper()
            line2 = (lines[1] or "").upper()
            header = line1 if line1 == "WELCOME TO" else f"{header_token} - {line1}" if line1 else header_token
            txts = [header]
            if line2:
                txts.append(line2)
            if len(lines) > 2 and lines[2]:
                txts.append(lines[2].upper())
        else:
            txts = [header_token] + [ln.upper() for ln in lines]

        # Für Kreis: schmaler Textbereich
        text_area_width = int(w * 0.8)
        wrapped = []
        for t in txts:
            wrapped.extend(self._wrap_text(t, font, text_area_width))
        if not wrapped:
            wrapped = [""]

        # Text unter Symbol, zentriert
        text_start_y = symbol_y + symbol_size_px + margin // 2
        text_x_start = (w - text_area_width) // 2
        self._draw_wrapped_text_centered(draw, mask_draw, font, wrapped, text_x_start, text_x_start + text_area_width, text_start_y, h)
    
    def _draw_wrapped_text(self, draw, mask_draw, font, wrapped, text_area_start, text_area_width, h):
        """Zeichnet umgebrochenen Text (für Rechteck-Layout)"""
        line_spacing = self.cfg.line_height_px
        
        if wrapped:
            last_bb = font.getbbox(wrapped[-1])
            last_h = last_bb[3] - last_bb[1]
            block_h = max(0, (len(wrapped) - 1) * line_spacing) + last_h
        else:
            block_h = 0
            
        min_pad = 10
        y_start = min_pad if block_h >= (h - 2 * min_pad) else (h - block_h) // 2

        off_x = int(getattr(self.cfg, 'text_offset_x', 0))
        off_y = int(getattr(self.cfg, 'text_offset_y', 0))

        for i, ln in enumerate(wrapped):
            bb = font.getbbox(ln)
            tw = bb[2] - bb[0]
            x = text_area_start + (text_area_width - tw) // 2 + off_x
            y = int(y_start + i * line_spacing + off_y - bb[1])
            max_x = text_area_start + text_area_width - tw
            if max_x < text_area_start:
                max_x = text_area_start
            x = max(text_area_start, min(x, max_x))
            if y < 0:
                y = 0
            elif y > h - line_spacing:
                y = h - line_spacing
            draw.text((x, y), ln, fill="black", font=font)
            mask_draw.text((x, y), ln, fill=255, font=font)
    
    def _draw_wrapped_text_centered(self, draw, mask_draw, font, wrapped, x_start, x_end, y_start, h):
        """Zeichnet umgebrochenen Text zentriert (für Quadrat/Kreis-Layout)"""
        line_spacing = self.cfg.line_height_px
        text_area_width = x_end - x_start
        
        off_x = int(getattr(self.cfg, 'text_offset_x', 0))
        off_y = int(getattr(self.cfg, 'text_offset_y', 0))

        current_y = y_start + off_y
        for ln in wrapped:
            bb = font.getbbox(ln)
            tw = bb[2] - bb[0]
            x = x_start + (text_area_width - tw) // 2 + off_x
            y = int(current_y - bb[1])
            
            # Clamp
            x = max(x_start, min(x, x_end - tw))
            if y < 0:
                y = 0
            elif y > h - line_spacing:
                y = h - line_spacing
                
            draw.text((x, y), ln, fill="black", font=font)
            mask_draw.text((x, y), ln, fill=255, font=font)
            current_y += line_spacing

    # --------------- Auto adjust -----------------
    def _auto_adjust(self, lines: List[str]):
        font = self._get_font(getattr(self.cfg, 'font_size_mm', 6.0))
        ppmm = self.cfg.px_per_mm
        # Height: header + lines
        needed_h_px = (len(lines) + 1) * self.cfg.line_height_px
        self.cfg.height_mm = max(self.cfg.height_mm, needed_h_px / ppmm)
        # Width: symbol block + max text + padding
        header_token = "#LOTOPOINT"
        texts = [header_token] + [ln.upper() for ln in lines]
        widths = [font.getbbox(t)[2] - font.getbbox(t)[0] for t in texts]
        max_text_w = max(widths) if widths else 0
        symbol_block_px = (
            int(self.cfg.symbol_size_mm * ppmm)
            + int(self.cfg.symbol_offset_x_mm * ppmm)
            + 20
        )
        qr_reserved_px = 0
        if getattr(self.cfg, 'qr_mode_enabled', False):
            qr_reserved_px = (
                int(self.cfg.symbol_size_mm * ppmm)
                + int(self.cfg.symbol_offset_x_mm * ppmm)
                + 20
            )
        desired_w_px = symbol_block_px + max_text_w + 20 + qr_reserved_px
        cur_w_px = int(self.cfg.width_mm * ppmm)
        if desired_w_px > cur_w_px:
            self.cfg.width_mm = desired_w_px / ppmm
        # Optional live update callback
        try:
            import __main__  # type: ignore
            app = getattr(__main__, 'app', None)
            if app and hasattr(app, 'update_collection_count_preview'):
                app.update_collection_count_preview()
        except Exception:
            pass

    # --------------- Cache helper -----------------
    def _manage_cache(self, cache: Dict[str, Any], key: str, img: Image.Image):
        if len(cache) > 10:
            oldest_key = next(iter(cache))
            del cache[oldest_key]
        cache[key] = img

    def get_last_text_mask(self) -> Optional[Image.Image]:
        if self._last_text_mask is None:
            return None
        return self._last_text_mask.copy()
