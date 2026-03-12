"""
Widget zur Visualisierung der Export-Einstellungen (Maße)
"""
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QPainterPath
from PyQt6.QtCore import QRectF


class DimensionsVisualizationWidget(QWidget):
    """Widget zur visuellen Darstellung der Export-Maße"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(450, 350)
        self.setMaximumHeight(400)
        
        # Standardwerte
        self.width_mm = 210
        self.height_mm = 297
        self.margin_mm = 8
        self.spacing_mm = 4
        self.is_roll_mode = False
        self.roll_width_mm = 500
        self.sticker_width_mm = 50
        self.sticker_height_mm = 50
        
        # UI Farben
        self.bg_color = QColor("#f8f9fa")
        self.page_color = QColor("#ffffff")
        self.margin_color = QColor("#e8f4ff")
        self.sticker_color = QColor("#d4edda")
        self.border_color = QColor("#343a40")
        self.margin_border_color = QColor("#007bff")
        self.spacing_color = QColor("#ff6b6b")
        self.text_color = QColor("#212529")
        self.roll_color = QColor("#fff3cd")
        
    def set_dimensions(self, width_mm, height_mm, margin_mm, spacing_mm, is_roll_mode=False, sticker_width_mm=50, sticker_height_mm=50, roll_width_mm=500):
        """Aktualisiert die angezeigten Maße"""
        self.width_mm = width_mm
        self.height_mm = height_mm
        self.margin_mm = margin_mm
        self.spacing_mm = spacing_mm
        self.is_roll_mode = is_roll_mode
        self.roll_width_mm = roll_width_mm
        self.sticker_width_mm = sticker_width_mm
        self.sticker_height_mm = sticker_height_mm
        print(f"[DEBUG] DimensionsWidget: Sticker={sticker_width_mm}x{sticker_height_mm}mm, Seite={width_mm}x{height_mm}mm")
        self.update()
        
    def paintEvent(self, event):
        """Zeichnet die Visualisierung"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Hintergrund
        painter.fillRect(self.rect(), self.bg_color)
        
        if self.is_roll_mode:
            self._draw_roll_mode(painter)
        else:
            self._draw_sheet_mode(painter)
        
        painter.end()
    
    def _draw_roll_mode(self, painter):
        """Zeichnet Rollenmodus-Darstellung"""
        # Berechne Skalierung für Rollenbreite
        padding = 60
        available_width = self.width() - 2 * padding
        available_height = self.height() - 2 * padding
        
        # Verwende Rollenbreite aus Einstellungen
        actual_width = self.roll_width_mm if self.is_roll_mode else self.width_mm
        scale = available_width / actual_width
        
        # Zentrierte Position
        roll_width = actual_width * scale
        roll_height = available_height  # Verwende verfügbare Höhe
        x_offset = (self.width() - roll_width) / 2
        y_offset = (self.height() - roll_height) / 2
        
        # Rolle (gelber/beiger Hintergrund für kontinuierliches Papier)
        roll_rect = QRectF(x_offset, y_offset, roll_width, roll_height)
        painter.fillRect(roll_rect, self.roll_color)
        painter.setPen(QPen(self.border_color, 2, Qt.PenStyle.DashLine))
        painter.drawRect(roll_rect)
        
        # Margin-Bereich (nur links/rechts, oben/unten gestrichelt)
        margin_scaled = self.margin_mm * scale
        margin_rect = QRectF(
            x_offset + margin_scaled,
            y_offset,
            roll_width - 2 * margin_scaled,
            roll_height
        )
        painter.fillRect(margin_rect, self.margin_color)
        painter.setPen(QPen(self.margin_border_color, 1, Qt.PenStyle.DashLine))
        painter.drawLine(int(margin_rect.left()), int(margin_rect.top()), 
                        int(margin_rect.left()), int(margin_rect.bottom()))
        painter.drawLine(int(margin_rect.right()), int(margin_rect.top()), 
                        int(margin_rect.right()), int(margin_rect.bottom()))
        
        # Verwende tatsächliche Sticker-Maße und berechne optimale Anordnung
        spacing_scaled = self.spacing_mm * scale
        
        # Berechne optimale Anordnung für Rolle (nur horizontal optimieren)
        available_width_mm = (margin_rect.width() / scale)
        
        # Teste beide Orientierungen
        cols_normal = max(1, int((available_width_mm + self.spacing_mm) / (self.sticker_width_mm + self.spacing_mm)))
        cols_rotated = max(1, int((available_width_mm + self.spacing_mm) / (self.sticker_height_mm + self.spacing_mm)))
        
        # Wähle Orientierung mit mehr Spalten
        if cols_rotated > cols_normal:
            sticker_w_mm = self.sticker_height_mm
            sticker_h_mm = self.sticker_width_mm
            cols = cols_rotated
        else:
            sticker_w_mm = self.sticker_width_mm
            sticker_h_mm = self.sticker_height_mm
            cols = cols_normal
        
        # Skaliere Sticker-Größen
        sticker_width_scaled = sticker_w_mm * scale
        sticker_height_scaled = sticker_h_mm * scale
        
        # Berechne Grid-Breite und zentriere horizontal
        grid_width = cols * sticker_width_scaled + (cols - 1) * spacing_scaled
        start_x = (margin_rect.width() - grid_width) / 2
        
        # Zeige 2 Reihen von Stickern (zentriert)
        rows_to_show = 2
        for row in range(rows_to_show):
            for col in range(cols):
                sticker_x = margin_rect.left() + start_x + col * (sticker_width_scaled + spacing_scaled)
                sticker_y = margin_rect.top() + 15 + row * (sticker_height_scaled + spacing_scaled)
                
                sticker_rect = QRectF(sticker_x, sticker_y, sticker_width_scaled, sticker_height_scaled)
                painter.fillRect(sticker_rect, self.sticker_color)
                painter.setPen(QPen(QColor("#28a745"), 1.5))
                painter.drawRect(sticker_rect)
        
        # Beschriftungen
        font = QFont("Segoe UI", 8)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QPen(self.text_color, 1))
        
        # Rand-Beschriftung (links)
        margin_label = f"{self.margin_mm} mm"
        painter.save()
        painter.translate(x_offset + margin_scaled/2, y_offset + roll_height/2)
        painter.rotate(-90)
        painter.drawText(-20, 5, margin_label)
        painter.restore()
        
        # Abstand-Beschriftung (nur wenn mehr als 1 Spalte)
        if cols > 1:
            spacing_x = margin_rect.left() + sticker_width_scaled + spacing_scaled/2
            spacing_y = margin_rect.top() + 20 + sticker_height_scaled/2
            painter.setPen(QPen(self.spacing_color, 1))
            spacing_label = f"{self.spacing_mm} mm"
            painter.drawText(int(spacing_x - 15), int(spacing_y), spacing_label)
        
        # Format-Info oben
        painter.setPen(QPen(self.text_color, 1))
        font_info = QFont("Segoe UI", 9)
        font_info.setBold(True)
        painter.setFont(font_info)
        format_text = f"Rollenmodus: {self.roll_width_mm} mm Breite (variable Höhe)"
        text_rect = painter.boundingRect(self.rect(), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter, format_text)
        painter.drawText(self.width()//2 - text_rect.width()//2, 15, format_text)
        
        # Legende unten
        self._draw_legend(painter, is_roll=True)
    
    def _draw_sheet_mode(self, painter):
        """Zeichnet normalen Seitenmodus"""
        # Berechne Skalierung - weniger Padding für größere Darstellung
        padding = 15
        available_width = self.width() - 2 * padding
        available_height = self.height() - 2 * padding
        
        # Skalierungsfaktor (A4 ist höher als breit)
        scale = min(available_width / self.width_mm, available_height / self.height_mm)
        
        # Zentrierte Position
        page_width = self.width_mm * scale
        page_height = self.height_mm * scale
        x_offset = (self.width() - page_width) / 2
        y_offset = (self.height() - page_height) / 2
        
        # A4-Seite
        page_rect = QRectF(x_offset, y_offset, page_width, page_height)
        painter.fillRect(page_rect, self.page_color)
        painter.setPen(QPen(self.border_color, 2))
        painter.drawRect(page_rect)
        
        # Margin-Bereich
        margin_scaled = self.margin_mm * scale
        margin_rect = QRectF(
            x_offset + margin_scaled,
            y_offset + margin_scaled,
            page_width - 2 * margin_scaled,
            page_height - 2 * margin_scaled
        )
        painter.fillRect(margin_rect, self.margin_color)
        painter.setPen(QPen(self.margin_border_color, 1, Qt.PenStyle.DashLine))
        painter.drawRect(margin_rect)
        
        # Berechne optimale Anordnung mit Auto-Rotation
        layout = self._calculate_optimal_layout()
        
        # Zeichne Sticker basierend auf berechnetem Layout
        for sticker_info in layout:
            sticker_x = x_offset + margin_scaled + sticker_info['x'] * scale
            sticker_y = y_offset + margin_scaled + sticker_info['y'] * scale
            sticker_w = sticker_info['width'] * scale
            sticker_h = sticker_info['height'] * scale
            
            sticker_rect = QRectF(sticker_x, sticker_y, sticker_w, sticker_h)
            painter.fillRect(sticker_rect, self.sticker_color)
            painter.setPen(QPen(QColor("#28a745"), 1.5))
            painter.drawRect(sticker_rect)
        
        # Abstand-Beschriftung (nur wenn Sticker vorhanden)
        if len(layout) > 1:
            spacing_scaled = self.spacing_mm * scale
            first = layout[0]
            # Finde zweiten Sticker in gleicher Reihe
            second = None
            for s in layout[1:]:
                if abs(s['y'] - first['y']) < 1:  # Gleiche Reihe
                    second = s
                    break
            
            if second:
                spacing_x = x_offset + margin_scaled + (first['x'] + first['width'] + second['x']) / 2 * scale
                spacing_y = y_offset + margin_scaled + (first['y'] + first['height']/2) * scale
                painter.setPen(QPen(self.spacing_color, 1))
                spacing_label = f"{self.spacing_mm} mm"
                painter.drawText(int(spacing_x - 15), int(spacing_y), spacing_label)
        
        # Beschriftungen
        font = QFont("Segoe UI", 8)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QPen(self.text_color, 1))
        
        # Rand-Beschriftung (links)
        margin_label = f"{self.margin_mm} mm"
        painter.save()
        painter.translate(x_offset + margin_scaled/2, y_offset + page_height/2)
        painter.rotate(-90)
        painter.drawText(-20, 5, margin_label)
        painter.restore()
        
        # Format-Info oben
        painter.setPen(QPen(self.text_color, 1))
        font_info = QFont("Segoe UI", 9)
        font_info.setBold(True)
        painter.setFont(font_info)
        format_text = f"{self.width_mm} × {self.height_mm} mm"
        text_rect = painter.boundingRect(self.rect(), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter, format_text)
        painter.drawText(self.width()//2 - text_rect.width()//2, 15, format_text)
        
        # Legende unten
        self._draw_legend(painter, is_roll=False)
    
    def _calculate_optimal_layout(self):
        """Berechnet optimale Sticker-Anordnung mit Auto-Rotation"""
        available_width = self.width_mm - 2 * self.margin_mm
        available_height = self.height_mm - 2 * self.margin_mm
        
        # Teste beide Orientierungen
        layout_normal = self._calculate_grid_layout(
            self.sticker_width_mm, self.sticker_height_mm,
            available_width, available_height
        )
        
        layout_rotated = self._calculate_grid_layout(
            self.sticker_height_mm, self.sticker_width_mm,  # Gedreht
            available_width, available_height
        )
        
        # Wähle die Orientierung mit mehr Stickern
        if len(layout_rotated) > len(layout_normal):
            return layout_rotated
        return layout_normal
    
    def _calculate_grid_layout(self, sticker_w, sticker_h, available_w, available_h):
        """Berechnet Grid-Layout für gegebene Sticker-Dimensionen (zentriert)"""
        layout = []
        
        # Berechne wie viele Sticker passen
        cols = max(1, int((available_w + self.spacing_mm) / (sticker_w + self.spacing_mm)))
        rows = max(1, int((available_h + self.spacing_mm) / (sticker_h + self.spacing_mm)))
        
        # Berechne tatsächliche Grid-Größe
        grid_width = cols * sticker_w + (cols - 1) * self.spacing_mm
        grid_height = rows * sticker_h + (rows - 1) * self.spacing_mm
        
        # Zentriere das Grid horizontal und vertikal
        start_x = (available_w - grid_width) / 2
        start_y = (available_h - grid_height) / 2
        
        # Platziere Sticker
        for row in range(rows):
            for col in range(cols):
                x = start_x + col * (sticker_w + self.spacing_mm)
                y = start_y + row * (sticker_h + self.spacing_mm)
                
                # Prüfe ob Sticker noch passt
                if x + sticker_w <= available_w and y + sticker_h <= available_h:
                    layout.append({
                        'x': x,
                        'y': y,
                        'width': sticker_w,
                        'height': sticker_h
                    })
        
        return layout
    
    def _draw_legend(self, painter, is_roll=False):
        """Zeichnet die Legende"""
        legend_font = QFont("Segoe UI", 7)
        painter.setFont(legend_font)
        legend_y = self.height() - 10
        
        if is_roll:
            # Rollen-Legende
            painter.fillRect(10, legend_y - 8, 12, 8, self.roll_color)
            painter.setPen(QPen(self.border_color, 1))
            painter.drawRect(10, legend_y - 8, 12, 8)
            painter.setPen(QPen(self.text_color, 1))
            painter.drawText(26, legend_y, "Rolle")
        else:
            # Rand-Legende
            painter.fillRect(10, legend_y - 8, 12, 8, self.margin_color)
            painter.setPen(QPen(self.margin_border_color, 1))
            painter.drawRect(10, legend_y - 8, 12, 8)
            painter.setPen(QPen(self.text_color, 1))
            painter.drawText(26, legend_y, "Rand")
        
        # Sticker-Legende
        painter.fillRect(70, legend_y - 8, 12, 8, self.sticker_color)
        painter.setPen(QPen(QColor("#28a745"), 1))
        painter.drawRect(70, legend_y - 8, 12, 8)
        painter.setPen(QPen(self.text_color, 1))
        painter.drawText(86, legend_y, "Sticker")
        
        # Abstand-Legende
        painter.setPen(QPen(self.spacing_color, 1))
        painter.drawText(140, legend_y, f"Abstand ({self.spacing_mm} mm)")
