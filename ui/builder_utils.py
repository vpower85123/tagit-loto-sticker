"""Utility-Funktionen und Icon-Factory für UI Builder.

Enthält:
- add_depth_shadow: Schatten-Effekt für Widgets
- _get_card_style: Card-Container CSS
- _create_glass_button: GlassGlowButton Factory
- create_symbol_icon: Vektor-Icon Rendering
"""

from PyQt6.QtWidgets import QGraphicsDropShadowEffect
from PyQt6.QtGui import (
    QColor, QPainter, QPen, QBrush, QPixmap, QIcon,
    QPainterPath, QLinearGradient, QTransform, QFont
)
from PyQt6.QtCore import Qt, QSize, QPoint, QRectF, QPointF
import math

from ui.theme import Theme, get_theme_colors
from ui.glass_button import GlassGlowButton


def add_depth_shadow(widget):
    """Fügt weichen Gradient-Schatten für subtilen Übergang hinzu."""
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(24)
    shadow.setXOffset(0)
    shadow.setYOffset(2)
    shadow.setColor(QColor(0, 0, 0, 12))
    widget.setGraphicsEffect(shadow)


def _get_card_style(self, object_name: str) -> str:
    """Erstellt den Style für Card-Container unter Berücksichtigung von Custom Colors."""
    custom_colors = getattr(self.theme_config, 'custom_colors', {}) if hasattr(self, 'theme_config') else {}
    colors = get_theme_colors(Theme.LIGHT, custom_colors)
    
    element_bg = custom_colors.get('element_bg', colors.get('input_bg'))
    border_color = colors.get('border')
    
    return (
        f"QWidget#{object_name} {{"
        f"  background: {element_bg};"
        f"  border: none;"
        "  border-radius: 0px;"
        "  padding: 0px;"
        "}"
    )


def _create_glass_button(self, text: str) -> GlassGlowButton:
    """Erstellt einen GlassGlowButton mit Theme-Anpassung."""
    btn = GlassGlowButton(text, dark_mode=False)
    # Höhe und Schriftgröße kommen aus ButtonSettings
    return btn


def create_symbol_icon(name, size=64, color="#ffffff"):
    """Erstellt ein Vektor-Icon als QIcon (Modern Gradient Style)."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    # --- Modern Gradient Style ---
    base_color = QColor(color)
    
    # Gradient: Top-Left (Light) -> Bottom-Right (Darker)
    gradient = QLinearGradient(0, 0, size, size)
    gradient.setColorAt(0.0, base_color)
    gradient.setColorAt(1.0, base_color.darker(130)) # 30% darker
    
    painter.setBrush(QBrush(gradient))
    painter.setPen(Qt.PenStyle.NoPen)
    
    # Margin
    margin = size * 0.15
    w = size - 2 * margin
    h = size - 2 * margin
    x = margin
    y = margin
    
    cx = size / 2
    cy = size / 2
    
    path = QPainterPath()
    
    if name == "plus":
        # Rounded Plus
        thickness = w * 0.22
        radius = thickness / 2
        # Vertical
        path.addRoundedRect(cx - thickness/2, y, thickness, h, radius, radius)
        # Horizontal
        path.addRoundedRect(x, cy - thickness/2, w, thickness, radius, radius)
        
    elif name == "search":
        # Modern Search
        r_outer = w * 0.38
        r_inner = r_outer * 0.65
        
        # Ring
        ring = QPainterPath()
        ring.addEllipse(QPointF(x + r_outer, y + r_outer), r_outer, r_outer)
        inner = QPainterPath()
        inner.addEllipse(QPointF(x + r_outer, y + r_outer), r_inner, r_inner)
        ring = ring.subtracted(inner)
        path.addPath(ring)
        
        # Handle (Rounded)
        handle_len = w * 0.35
        handle_w = w * 0.15
        
        rcx, rcy = x + r_outer, y + r_outer
        
        painter.translate(rcx, rcy)
        painter.rotate(45)
        handle_path = QPainterPath()
        handle_path.addRoundedRect(QRectF(r_outer - 2, -handle_w/2, handle_len, handle_w), handle_w/2, handle_w/2)
        
        # Transform handle path back to world coords
        transform = QTransform()
        transform.translate(rcx, rcy)
        transform.rotate(45)
        path.addPath(transform.map(handle_path))
        
        painter.rotate(-45)
        painter.translate(-rcx, -rcy)
        
    elif name == "up":
        # Soft Arrow Up
        head_h = h * 0.45
        shaft_w = w * 0.4
        radius = 4.0
        
        p = QPainterPath()
        p.moveTo(cx, y) # Tip
        p.lineTo(x + w, y + head_h)
        p.lineTo(cx + shaft_w/2, y + head_h)
        p.lineTo(cx + shaft_w/2, y + h - radius)
        # Bottom right corner
        p.quadTo(cx + shaft_w/2, y + h, cx + shaft_w/2 - radius, y + h)
        p.lineTo(cx - shaft_w/2 + radius, y + h)
        # Bottom left corner
        p.quadTo(cx - shaft_w/2, y + h, cx - shaft_w/2, y + h - radius)
        p.lineTo(cx - shaft_w/2, y + head_h)
        p.lineTo(x, y + head_h)
        p.closeSubpath()
        
        path = p
        
    elif name == "down":
        # Soft Arrow Down
        head_h = h * 0.45
        shaft_w = w * 0.4
        radius = 4.0
        
        p = QPainterPath()
        p.moveTo(cx, y + h) # Tip
        p.lineTo(x + w, y + h - head_h)
        p.lineTo(cx + shaft_w/2, y + h - head_h)
        p.lineTo(cx + shaft_w/2, y + radius)
        # Top right corner
        p.quadTo(cx + shaft_w/2, y, cx + shaft_w/2 - radius, y)
        p.lineTo(cx - shaft_w/2 + radius, y)
        # Top left corner
        p.quadTo(cx - shaft_w/2, y, cx - shaft_w/2, y + radius)
        p.lineTo(cx - shaft_w/2, y + h - head_h)
        p.lineTo(x, y + h - head_h)
        p.closeSubpath()
        
        path = p

    elif name == "close":
        # Rounded X
        thickness = w * 0.18
        radius = thickness / 2
        
        # Center
        painter.translate(cx, cy)
        painter.rotate(45)
        
        p1 = QPainterPath()
        p1.addRoundedRect(QRectF(-w/2, -thickness/2, w, thickness), radius, radius)
        path.addPath(painter.transform().map(p1)) # Map to world
        
        painter.rotate(90)
        p2 = QPainterPath()
        p2.addRoundedRect(QRectF(-w/2, -thickness/2, w, thickness), radius, radius)
        
        painter.resetTransform()
        
        # Re-do with transform mapping
        t1 = QTransform()
        t1.translate(cx, cy)
        t1.rotate(45)
        path.addPath(t1.map(p1))
        
        t2 = QTransform()
        t2.translate(cx, cy)
        t2.rotate(135) # 45 + 90
        path.addPath(t2.map(p1))
        
    elif name == "trash":
        # Modern Trash
        lid_h = h * 0.12
        lid_w = w * 1.0
        
        # Lid Handle
        handle_w = w * 0.3
        handle_h = h * 0.06
        path.addRoundedRect(cx - handle_w/2, y, handle_w, handle_h, 2, 2)
        
        # Lid (Rounded)
        path.addRoundedRect(x, y + handle_h + 2, lid_w, lid_h, 4, 4)
        
        # Body
        body_w = w * 0.75
        body_h = h * 0.7
        body_x = cx - body_w/2
        body_y = y + handle_h + lid_h + 6
        
        body = QPainterPath()
        body.addRoundedRect(body_x, body_y, body_w, body_h, 8, 8)
        
        # Stripes
        stripe_w = body_w * 0.12
        stripe_h = body_h * 0.5
        stripe_y = body_y + body_h * 0.25
        
        s1 = QPainterPath()
        s1.addRoundedRect(cx - stripe_w*1.8, stripe_y, stripe_w, stripe_h, 2, 2)
        s1.addRoundedRect(cx - stripe_w*0.0, stripe_y, stripe_w, stripe_h, 2, 2) # Center
        s1.addRoundedRect(cx + stripe_w*1.8, stripe_y, stripe_w, stripe_h, 2, 2)
        
        path.addPath(body.subtracted(s1))

    elif name == "pdf_extractor":
        # PDF Document
        doc_w = w * 0.75
        doc_h = h * 0.9
        doc_x = cx - doc_w/2
        doc_y = cy - doc_h/2
        
        # Main Doc
        path.addRoundedRect(doc_x, doc_y, doc_w, doc_h, 6, 6)
        
        # Text Lines (Subtracted)
        line_h = doc_h * 0.08
        line_gap = doc_h * 0.18
        start_y = doc_y + doc_h * 0.3
        
        lines = QPainterPath()
        for i in range(3):
            ly = start_y + i * line_gap
            lines.addRoundedRect(doc_x + doc_w*0.2, ly, doc_w*0.6, line_h, 2, 2)
            
        path = path.subtracted(lines)

    elif name == "sort":
        # Sort Icon (A-Z)
        font = painter.font()
        font.setBold(True)
        font.setPixelSize(int(h * 0.5))
        painter.setFont(font)
        
        # Draw Shadow for Text
        painter.setPen(QColor(0, 0, 0, 60))
        painter.drawText(QRectF(2, 2, size, size), Qt.AlignmentFlag.AlignCenter, "AZ")
        
        # Draw Main Text
        painter.setPen(base_color)
        painter.drawText(QRectF(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, "AZ")
        
        painter.end()
        return QIcon(pix)

    # --- Draw Shadow ---
    painter.save()
    painter.translate(3, 3)
    painter.setBrush(QColor(0, 0, 0, 60)) # Soft shadow
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawPath(path)
    painter.restore()

    # --- Draw Main Shape ---
    painter.drawPath(path)
    
    painter.end()
    return QIcon(pix)
