"""
Collapsible Section Widget mit Hover-Expand Funktionalität

Diese Komponente erstellt Sektionen, die automatisch eingeklappt sind
und sich beim Hovern ausklappen. Sektionen bleiben offen bis eine andere
Sektion gehovert wird.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer
from PyQt6.QtGui import QFont, QEnterEvent
import qtawesome as qta


# Globale Registry für alle CollapsibleSection Instanzen
_all_sections = []


class CollapsibleSection(QWidget):
    """
    Eine einklappbare Sektion die sich beim Hovern ausklappt.
    Bleibt offen bis eine andere Sektion gehovert wird.
    
    Args:
        title: Der Titel der Sektion
        content_widget: Das Widget das eingeklappt/ausgeklappt wird
        collapsed_height: Höhe im eingeklappten Zustand (default: 60)
        animation_duration: Dauer der Animation in ms (default: 300)
    """
    
    def __init__(self, title: str, content_widget: QWidget = None, 
                 collapsed_height: int = 40, animation_duration: int = 300,
                 parent=None):
        super().__init__(parent)
        
        self._collapsed_height = collapsed_height
        self._expanded_height = 16777215  # Qt Maximum - nutzt gesamten verfügbaren Platz
        self._animation_duration = animation_duration
        self._is_collapsed = True
        
        # Registriere diese Sektion global
        _all_sections.append(self)
        
        # Enable mouse tracking
        self.setMouseTracking(True)
        
        # Setup UI
        self._setup_ui(title, content_widget)
        
        # Animation für Höhe
        self._height_animation = QPropertyAnimation(self, b"maximumHeight")
        self._height_animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._height_animation.setDuration(self._animation_duration)
        
        # Initial collapsed state
        self.setMaximumHeight(self._collapsed_height)
        if self._content_container:
            self._content_container.hide()
        
        # SizePolicy - initial auf Fixed (eingeklappt)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
    
    def __del__(self):
        """Entferne aus globaler Registry beim Löschen"""
        if self in _all_sections:
            _all_sections.remove(self)
    
    def _setup_ui(self, title: str, content_widget: QWidget = None):
        """UI aufbauen"""
        # Setze Styling für outer container - durchgehender Border
        self.setStyleSheet("""
            CollapsibleSection {
                background-color: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 16px;
            }
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Header (immer sichtbar)
        self._header = QFrame()
        self._header.setFixedHeight(self._collapsed_height)
        self._header.setMouseTracking(True)
        self._header.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
            }
        """)
        
        header_layout = QHBoxLayout(self._header)
        header_layout.setContentsMargins(20, 0, 20, 0)
        header_layout.setSpacing(0)
        
        # Title Label - mit CSS padding-top für Position oben
        self._title_label = QLabel(title)
        title_font = QFont("Bahnschrift", 13)
        title_font.setWeight(QFont.Weight.Bold)
        self._title_label.setFont(title_font)
        self._title_label.setStyleSheet("color: #1f2a37; background-color: transparent; padding-top: 8px; padding-bottom: 0px;")
        self._title_label.setFixedHeight(40)
        header_layout.addWidget(self._title_label)
        
        header_layout.addStretch()
        
        # Expand/Collapse Indicator
        self._indicator = QLabel()
        self._indicator.setFixedSize(24, 40)
        self._indicator.setStyleSheet("background-color: transparent; padding-top: 8px; padding-bottom: 0px;")
        self._indicator.setPixmap(qta.icon('ph.caret-down', color='#6b7280').pixmap(14, 14))
        self._indicator.setFixedHeight(40)
        header_layout.addWidget(self._indicator)
        
        main_layout.addWidget(self._header)
        
        # Content Container (wird ein-/ausgeklappt)
        self._content_container = QWidget()
        self._content_container.setMouseTracking(True)
        self._content_container.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border: none;
            }
        """)
        
        content_layout = QVBoxLayout(self._content_container)
        content_layout.setContentsMargins(20, 10, 20, 20)
        
        if content_widget:
            content_layout.addWidget(content_widget)
        
        main_layout.addWidget(self._content_container)
    
    def set_content(self, widget: QWidget):
        """Setzt oder ersetzt den Content"""
        # Entferne altes Content
        layout = self._content_container.layout()
        if layout:
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
        
        # Füge neues Content hinzu
        if widget:
            layout.addWidget(widget)
    
    def enterEvent(self, event: QEnterEvent):
        """Wird aufgerufen wenn Maus über Widget kommt"""
        if self._is_collapsed:
            # Klappe alle anderen Sektionen ein
            for section in _all_sections:
                if section is not self and not section._is_collapsed:
                    section._collapse()
            # Dann diese aufklappen
            self._expand()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Wird aufgerufen wenn Maus Widget verlässt - NICHTS TUN"""
        # Sektion bleibt offen bis eine andere gehovert wird
        super().leaveEvent(event)
    
    def _expand(self):
        """Klappt die Sektion aus"""
        self._is_collapsed = False
        
        # Ändere SizePolicy zu Expanding
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        
        # Update indicator
        self._indicator.setPixmap(qta.icon('ph.caret-up', color='#6b7280').pixmap(14, 14))
        
        # Content sichtbar machen
        if self._content_container:
            self._content_container.show()
        
        # Animate height
        self._height_animation.stop()
        self._height_animation.setStartValue(self.maximumHeight())
        self._height_animation.setEndValue(self._expanded_height)
        self._height_animation.start()
        
        # Update outer container styling - blauer Border
        self.setStyleSheet("""
            CollapsibleSection {
                background-color: #ffffff;
                border: 2px solid #3b82f6;
                border-radius: 16px;
            }
        """)
    
    def _collapse(self):
        """Klappt die Sektion ein"""
        self._is_collapsed = True
        
        # Ändere SizePolicy zurück zu Fixed
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        
        # Update indicator
        self._indicator.setPixmap(qta.icon('ph.caret-down', color='#6b7280').pixmap(14, 14))
        
        # Animate height
        self._height_animation.stop()
        self._height_animation.setStartValue(self.maximumHeight())
        self._height_animation.setEndValue(self._collapsed_height)
        self._height_animation.start()
        
        # Content verstecken nach Animation
        QTimer.singleShot(self._animation_duration, self._hide_content)
        
        # Update outer container styling - grauer Border
        self.setStyleSheet("""
            CollapsibleSection {
                background-color: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 16px;
            }
        """)
    
    def _hide_content(self):
        """Versteckt Content nach Animation"""
        if self._is_collapsed and self._content_container:
            self._content_container.hide()
    
    def set_collapsed(self, collapsed: bool):
        """Manuell collapsed state setzen"""
        if collapsed and not self._is_collapsed:
            self._collapse()
        elif not collapsed and self._is_collapsed:
            self._expand()
    
    def is_collapsed(self) -> bool:
        """Gibt zurück ob Sektion eingeklappt ist"""
        return self._is_collapsed
