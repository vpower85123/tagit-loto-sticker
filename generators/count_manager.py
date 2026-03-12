"""Count preview & settings extraction.

Provides CountStickerGenerator and helper functions to manage the count
preview UI logic (scaling + debounced updates) separated from StickerApp.
"""
from dataclasses import asdict
from typing import Any, Optional
import logging
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageChops

from core.models import CountConfig
from core.config_manager import ConfigManager
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

def hex_to_rgba(hex_color: str, alpha: int = 255) -> tuple:
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 6:
        return tuple(int(hex_color[i:i+2], 16) for i in (0,2,4)) + (alpha,)
    if len(hex_color) == 8:
        return tuple(int(hex_color[i:i+2], 16) for i in (0,2,4,6))
    raise ValueError(f"Invalid hex color: {hex_color}")

class CountStickerGenerator:
    def __init__(self, cfg: CountConfig):
        self.cfg = cfg
        self._font_cache: dict[int, Any] = {}
        self._last_text_mask: Optional[Image.Image] = None

    def _get_font(self, size_mm: float):
        size_px = int(size_mm * self.cfg.px_per_mm)
        if size_px not in self._font_cache:
            try:
                font_path = _resolve_path(self.cfg.font_path)
                self._font_cache[size_px] = ImageFont.truetype(str(font_path), size_px)
            except Exception:
                self._font_cache[size_px] = ImageFont.load_default()
        return self._font_cache[size_px]

    def generate(self, detail: str, count: int, custom_header: str = None):
        cfg = self.cfg; ppmm = cfg.px_per_mm
        items = [it.strip() for it in detail.split(',') if it.strip()]
        fd = self._get_font(cfg.font_size_mm - 2.0)
        fh = self._get_font(cfg.font_size_mm - 1.0)
        
        # Immer den Header-Text aus Config verwenden, niemals ersetzen
        header = f"{cfg.header_text} {count}".upper()
        
        hb = fh.getbbox(header); hh = hb[3] - hb[1]
        base_w, base_h = cfg.size_px
        margin_px = int(5 * ppmm)

        def group_lines(max_w: int) -> list[str]:
            out, current = [], ''
            for item in items:
                up = item.upper(); w_item = fd.getbbox(up)[2] - fd.getbbox(up)[0]
                if w_item > max_w:
                    if current: out.append(current); current = ''
                    out.append(up); continue
                if current:
                    test = f"{current}, {up}"; w_test = fd.getbbox(test)[2] - fd.getbbox(test)[0]
                    if w_test <= max_w: current = test
                    else: out.append(current); current = up
                else:
                    current = up
            if current: out.append(current)
            return out

        if cfg.auto_adjust:
            # Fix: min_width_px should be DPI-aware to maintain consistent layout across resolutions
            # 600px at 96 DPI is approx 160mm
            min_width_mm = 160.0
            min_width_px = int(min_width_mm * ppmm)
            
            max_w_group = max(base_w, min_width_px) - 2 * margin_px
            lines = group_lines(max_w_group)
            block_h = hh + int(cfg.text_spacing_mm * ppmm) + len(lines) * cfg.line_height_px
            h = block_h + 2 * margin_px; w = max(base_w, min_width_px)
        else:
            w, h = base_w, base_h
            max_w_group = w - 2 * margin_px
            if max_w_group < 50: max_w_group = max(10, w - margin_px)
            lines = group_lines(max_w_group)

        if not cfg.auto_adjust:
            # Calculate actual required width based on content
            header_w = hb[2] - hb[0]
            max_content_w = header_w
            for ln in lines:
                bb = fd.getbbox(ln)
                lw = bb[2] - bb[0]
                max_content_w = max(max_content_w, lw)
            w = max_content_w + 2 * margin_px

            required_h = (margin_px + hh + int(cfg.text_spacing_mm * ppmm) +
                          len(lines) * cfg.line_height_px + margin_px)
            # Respect configured height_mm as minimum — never shrink below it
            h = max(base_h, required_h)

        w = int(w); h = int(h)
        
        # Create base image with transparency
        img = Image.new('RGBA', (w, h), (0,0,0,0))
        text_mask = Image.new('L', (w, h), 0)
        mask_draw = ImageDraw.Draw(text_mask)
        
        # Create rounded corner mask once
        mask = Image.new('L', (w, h), 0)
        ImageDraw.Draw(mask).rounded_rectangle([(0,0),(w,h)], radius=cfg.corner_radius, fill=255)
        
        # Create white background with rounded corners
        bg = Image.new('RGBA', (w, h), hex_to_rgba(cfg.bg_color))
        img.paste(bg, (0,0), mask)

        # Add stripes ON TOP of white background
        if cfg.show_stripes:
            stripe = max(1, h // 3)
            pat = Image.new('RGBA', (w, h), (0,0,0,0))
            pd = ImageDraw.Draw(pat)
            for x in range(-h, w, stripe * 2):
                pd.polygon([(x,0),(x+stripe,0),(x+stripe+h,h),(x+h,h)], fill=cfg.stripe_color)
            # Combine stripe alpha with rounded mask so stripes also have rounded corners
            pat_alpha = pat.split()[3]
            combined_mask = ImageChops.multiply(pat_alpha, mask)
            img.paste(pat, (0,0), combined_mask)
        
        draw = ImageDraw.Draw(img)
        
        bw2 = getattr(cfg, 'border_width', 1)
        draw.rounded_rectangle([(0,0),(w,h)], radius=cfg.corner_radius, outline='black' if bw2 else None, width=bw2)

        # Vertically center the text block within the sticker
        total_text_h = hh + int(cfg.text_spacing_mm * ppmm) + len(lines) * cfg.line_height_px
        block_y = max(margin_px, (h - total_text_h) // 2)
        header_x = max(margin_px, (w - (hb[2]-hb[0])) // 2)
        draw.text((header_x, block_y), header, fill='black', font=fh)
        mask_draw.text((header_x, block_y), header, fill=255, font=fh)
        y0 = block_y + hh + int(cfg.text_spacing_mm * ppmm)
        for i, ln in enumerate(lines):
            y_line = y0 + i * cfg.line_height_px
            if (not cfg.auto_adjust) and y_line + cfg.line_height_px > h - margin_px: break
            bb_line = fd.getbbox(ln); line_w = bb_line[2] - bb_line[0]
            x = max(margin_px, (w - line_w)//2)
            draw.text((x, y_line), ln, fill='black', font=fd)
            mask_draw.text((x, y_line), ln, fill=255, font=fd)

        self._last_text_mask = text_mask
        return img

    def get_last_text_mask(self) -> Optional[Image.Image]:
        if self._last_text_mask is None:
            return None
        return self._last_text_mask.copy()


__all__ = ['CountStickerGenerator']
