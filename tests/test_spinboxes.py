#!/usr/bin/env python3
"""
Test-Programm um Spinbox-Pfeile zu debuggen
"""

import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
from ui.spinboxes import StyledSpinBox, StyledDoubleSpinBox


class SpinboxTestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle("Spinbox Arrow Test")
        self.setGeometry(100, 100, 400, 300)
        
        layout = QVBoxLayout()
        
        # Test StyledSpinBox
        label1 = QLabel("StyledSpinBox (Ganzzahlen):")
        self.spin = StyledSpinBox()
        self.spin.setRange(0, 100)
        self.spin.setValue(50)
        layout.addWidget(label1)
        layout.addWidget(self.spin)
        
        # Test StyledDoubleSpinBox
        label2 = QLabel("StyledDoubleSpinBox (Dezimal):")
        self.double_spin = StyledDoubleSpinBox()
        self.double_spin.setRange(0.0, 100.0)
        self.double_spin.setValue(50.5)
        self.double_spin.setDecimals(2)
        layout.addWidget(label2)
        layout.addWidget(self.double_spin)
        
        layout.addStretch()
        
        # Instruktionen
        info = QLabel("""
        DEBUGGING-HINWEISE:
        1. Pfeile sollten oben/unten rechts sichtbar sein
        2. Versuche zu klicken und mit Pfeiltasten zu ändern
        3. Wenn keine Pfeile sichtbar: paintEvent() wird nicht aufgerufen
        4. Überprüfe: width > button_w + 8 (mindestens 22px breit)
        """)
        info.setWordWrap(True)
        layout.addWidget(info)
        
        self.setLayout(layout)
        self.show()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SpinboxTestWindow()
    sys.exit(app.exec())
