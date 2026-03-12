"""
Batch Equipment Dialog - Tabellen-Eingabe wie in Excel/Sheets
Ermöglicht das Hinzufügen mehrerer Equipments auf einmal
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QGroupBox, QCheckBox,
    QRadioButton, QButtonGroup, QWidget, QScrollArea, QFileDialog,
    QSplitter, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QFont, QColor, QBrush, QPixmap
from PIL.ImageQt import ImageQt
import qtawesome as qta
from core.models import SymbolType
from ui.glass_button import GlassGlowButton
from ui.spinboxes import StyledSpinBox  # Verwende vorhandene styled SpinBox
from ui.components import ModernComboBox  # Moderne ComboBox wie in der App

# UI Standards importieren
from ui.input_standards import (
    MIN_INPUT_HEIGHT, MIN_TABLE_ROW_HEIGHT,
    INPUT_TEXT_COLOR, INPUT_TEXT_COLOR_QT,
    INPUT_FONT_SIZE, INPUT_PADDING,
    INPUT_BG_COLOR, INPUT_BORDER_COLOR, INPUT_BORDER_RADIUS,
    FOCUS_BORDER_COLOR, FOCUS_BORDER_WIDTH,
    TABLE_HEADER_BG, TABLE_HEADER_COLOR, TABLE_GRID_COLOR,
    validate_input_params
)


class BatchEquipmentDialog(QDialog):
    """Dialog für Batch-Eingabe von Equipment wie in Excel/Sheets."""
    
    def __init__(self, parent, equipment_manager=None, existing_locations=None,
                 existing_systems=None):
        super().__init__(parent)
        self.equipment_manager = equipment_manager
        self.result_data = []  # Liste von Equipment-Daten
        
        self.existing_locations = existing_locations or []
        self.existing_systems = existing_systems or []
        
        self.setWindowTitle("Batch Equipment hinzufügen")
        self.setModal(True)
        self.setMinimumSize(900, 700)
        
        # Maximieren-Button aktivieren und maximiert öffnen
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMaximizeButtonHint)
        self.showMaximized()
        
        # QR-Code Pfad
        self.qr_code_path = None
        
        # Sticker-Generator vom Parent holen
        self.sticker_generator = None
        self.sticker_config = None
        if parent and hasattr(parent, 'sticker_generator'):
            self.sticker_generator = parent.sticker_generator
        if parent and hasattr(parent, 'sticker_config'):
            self.sticker_config = parent.sticker_config
        
        # Validiere Parameter vor dem Erstellen
        warnings = validate_input_params(row_height=MIN_TABLE_ROW_HEIGHT)
        if warnings:
            print("⚠️ UI Standards Check:", warnings)
        
        self._build_ui()
        
        # Preview-Update Timer
        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self._do_update_sticker_preview)
        
        # Initial Preview nach kurzer Verzögerung
        QTimer.singleShot(300, self._update_sticker_preview)
        self._add_initial_rows()
    
    def _build_ui(self):
        """UI aufbauen."""
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #f8fafc;
            }}
            QLabel {{
                color: {INPUT_TEXT_COLOR};
                font-size: {INPUT_FONT_SIZE}px;
            }}
            QLineEdit {{
                background-color: {INPUT_BG_COLOR};
                border: 1px solid {INPUT_BORDER_COLOR};
                border-radius: {INPUT_BORDER_RADIUS}px;
                padding: {INPUT_PADDING};
                font-size: {INPUT_FONT_SIZE}px;
                color: {INPUT_TEXT_COLOR};
                min-height: {MIN_INPUT_HEIGHT - 20}px;
            }}
            QLineEdit:focus {{
                border: {FOCUS_BORDER_WIDTH}px solid {FOCUS_BORDER_COLOR};
            }}
            QGroupBox {{
                font-weight: 600;
                font-size: 14px;
                color: {INPUT_TEXT_COLOR};
                border: 1px solid {INPUT_BORDER_COLOR};
                border-radius: 10px;
                margin-top: 12px;
                padding-top: 10px;
                background-color: {INPUT_BG_COLOR};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
                color: {FOCUS_BORDER_COLOR};
            }}
            QTableWidget {{
                background-color: {INPUT_BG_COLOR};
                border: 1px solid {INPUT_BORDER_COLOR};
                border-radius: {INPUT_BORDER_RADIUS}px;
                gridline-color: {TABLE_GRID_COLOR};
                font-size: {INPUT_FONT_SIZE}px;
                color: {INPUT_TEXT_COLOR};
            }}
            QTableWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {TABLE_GRID_COLOR};
                color: {INPUT_TEXT_COLOR};
                background-color: {INPUT_BG_COLOR};
            }}
            QTableWidget QLineEdit {{
                color: {INPUT_TEXT_COLOR};
                background-color: {INPUT_BG_COLOR};
                border: {FOCUS_BORDER_WIDTH}px solid {FOCUS_BORDER_COLOR};
                border-radius: 4px;
                padding: 6px 10px;
                font-size: {INPUT_FONT_SIZE}px;
                font-weight: 500;
                selection-background-color: {FOCUS_BORDER_COLOR};
                selection-color: #ffffff;
            }}
            QTableWidget::item:selected {{
                background-color: #dbeafe;
                color: {INPUT_TEXT_COLOR};
            }}
            QHeaderView::section {{
                background-color: {TABLE_HEADER_BG};
                color: {TABLE_HEADER_COLOR};
                font-weight: 600;
                font-size: 12px;
                padding: 10px 8px;
                border: none;
                border-bottom: 2px solid {TABLE_GRID_COLOR};
                border-right: 1px solid {TABLE_GRID_COLOR};
            }}
            QCheckBox {{
                color: {INPUT_TEXT_COLOR};
                font-size: {INPUT_FONT_SIZE}px;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 20px;
                height: 20px;
                border-radius: 5px;
                border: 2px solid #94a3b8;
                background-color: #ffffff;
            }}
            QCheckBox::indicator:hover {{
                border-color: #3b82f6;
            }}
            QCheckBox::indicator:checked {{
                background-color: #3b82f6;
                border-color: #3b82f6;
                image: url(none);
            }}
            QRadioButton {{
                color: {INPUT_TEXT_COLOR};
                font-size: {INPUT_FONT_SIZE}px;
                spacing: 8px;
                padding: 4px 8px;
            }}
            QRadioButton::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 9px;
                border: 2px solid #94a3b8;
                background-color: #ffffff;
            }}
            QRadioButton::indicator:hover {{
                border-color: #3b82f6;
            }}
            QRadioButton::indicator:checked {{
                background-color: #3b82f6;
                border-color: #3b82f6;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # === Header ===
        header = QLabel("Batch Equipment Eingabe")
        header.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header.setStyleSheet("color: #1e293b; margin-bottom: 5px;")
        layout.addWidget(header)
        
        subtitle = QLabel("Füge mehrere Equipments auf einmal hinzu - wie in Excel/Sheets")
        subtitle.setStyleSheet("color: #64748b; font-size: 12px; margin-bottom: 10px;")
        layout.addWidget(subtitle)
        
        # === Oberer Bereich: Einstellungen links, Vorschau rechts ===
        top_splitter = QSplitter(Qt.Orientation.Horizontal)
        top_splitter.setChildrenCollapsible(False)
        
        # Linker Bereich: Einstellungen
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(15)
        
        # === Gemeinsame Einstellungen ===
        common_group = QGroupBox("Gemeinsame Einstellungen (für alle Zeilen)")
        common_layout = QHBoxLayout(common_group)
        common_layout.setSpacing(20)
        
        # Standort - QLineEdit statt ComboBox
        loc_layout = QVBoxLayout()
        loc_label = QLabel("Standort:*")
        loc_label.setStyleSheet("font-weight: 600;")
        self.location_combo = QLineEdit()
        self.location_combo.setFixedWidth(180)
        self.location_combo.setPlaceholderText("z.B. HAM1")
        loc_layout.addWidget(loc_label)
        loc_layout.addWidget(self.location_combo)
        common_layout.addLayout(loc_layout)
        
        # System - QLineEdit statt ComboBox
        sys_layout = QVBoxLayout()
        sys_label = QLabel("System:*")
        sys_label.setStyleSheet("font-weight: 600;")
        self.system_combo = QLineEdit()
        self.system_combo.setFixedWidth(180)
        self.system_combo.setPlaceholderText("z.B. CONV1")
        sys_layout.addWidget(sys_label)
        sys_layout.addWidget(self.system_combo)
        common_layout.addLayout(sys_layout)
        
        # Symbol-Typ
        symbol_layout = QVBoxLayout()
        symbol_label = QLabel("Energie-Typ:")
        symbol_label.setStyleSheet("font-weight: 600;")
        self.symbol_combo = ModernComboBox(dark_mode=False)
        symbol_types = ["Electrical", "Pneumatic", "Hydraulic", "Mechanical", "Thermal", "Chemical", "Radiation", "Mixed", "Other"]
        self.symbol_combo.addItems(symbol_types)
        self.symbol_combo.setMinimumWidth(120)
        self.symbol_combo.currentIndexChanged.connect(self._update_sticker_preview)
        symbol_layout.addWidget(symbol_label)
        symbol_layout.addWidget(self.symbol_combo)
        common_layout.addLayout(symbol_layout)
        
        common_layout.addStretch()
        left_layout.addWidget(common_group)
        
        # === Auto-Nummerierung ===
        auto_group = QGroupBox("🔢 Auto-Nummerierung")
        auto_layout = QHBoxLayout(auto_group)
        
        self.auto_number_check = QCheckBox("Automatisch nummerieren")
        self.auto_number_check.setChecked(True)
        self.auto_number_check.toggled.connect(self._on_auto_number_changed)
        auto_layout.addWidget(self.auto_number_check)
        
        auto_layout.addWidget(QLabel("Prefix:"))
        self.prefix_entry = QLineEdit()
        self.prefix_entry.setPlaceholderText("z.B. SHP.01.LN01.RO1-")
        self.prefix_entry.setMinimumWidth(200)
        self.prefix_entry.textChanged.connect(self._update_preview)
        self.prefix_entry.textChanged.connect(self._update_sticker_preview)
        auto_layout.addWidget(self.prefix_entry)
        
        # Start-Spinner versteckt - beginnt immer bei 1
        self.start_spin = StyledSpinBox()
        self.start_spin.setRange(1, 9999)
        self.start_spin.setValue(1)
        self.start_spin.hide()  # Verstecken
        
        # Anzahl-Spinner entfernt - stattdessen + Button verwenden
        self.count_spin = StyledSpinBox()
        self.count_spin.setRange(1, 100)
        self.count_spin.setValue(1)  # Standard: 1 Zeile
        self.count_spin.hide()  # Verstecken
        
        auto_layout.addStretch()
        left_layout.addWidget(auto_group)
        left_layout.addStretch()
        
        top_splitter.addWidget(left_widget)
        
        # === Rechter Bereich: QR-Code und Sticker-Vorschau ===
        right_widget = QWidget()
        right_layout = QHBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(15)
        
        # QR-Code Bereich
        qr_group = QGroupBox("📱 QR-Code")
        qr_group.setMinimumWidth(220)
        qr_layout = QVBoxLayout(qr_group)
        qr_layout.setContentsMargins(15, 15, 15, 15)
        qr_layout.setSpacing(10)
        
        self.qr_preview_label = QLabel()
        self.qr_preview_label.setFixedSize(140, 140)
        self.qr_preview_label.setStyleSheet("""
            QLabel {
                background-color: #f1f5f9;
                border: 2px dashed #94a3b8;
                border-radius: 10px;
            }
        """)
        self.qr_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qr_preview_label.setText("Kein QR-Code")
        qr_layout.addWidget(self.qr_preview_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        qr_btn_layout = QHBoxLayout()
        qr_btn_layout.setSpacing(8)
        qr_select_btn = GlassGlowButton("Auswählen", dark_mode=False)
        qr_select_btn.setMinimumHeight(36)
        qr_select_btn.setMinimumWidth(90)
        qr_select_btn.clicked.connect(self._select_qr_code)
        qr_btn_layout.addWidget(qr_select_btn)
        
        qr_clear_btn = GlassGlowButton("Löschen", dark_mode=False)
        qr_clear_btn.setMinimumHeight(36)
        qr_clear_btn.setMinimumWidth(80)
        qr_clear_btn.clicked.connect(self._clear_qr_code)
        qr_btn_layout.addWidget(qr_clear_btn)
        
        qr_layout.addLayout(qr_btn_layout)
        right_layout.addWidget(qr_group)
        
        # Sticker-Vorschau Bereich
        preview_group = QGroupBox("Live Sticker Vorschau")
        preview_layout = QVBoxLayout(preview_group)
        preview_layout.setContentsMargins(15, 15, 15, 15)
        
        # Vorschau-Container mit hellem Hintergrund
        preview_container = QWidget()
        preview_container.setStyleSheet("""
            QWidget {
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
            }
        """)
        preview_container_layout = QVBoxLayout(preview_container)
        preview_container_layout.setContentsMargins(20, 20, 20, 20)
        preview_container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.sticker_preview_label = QLabel()
        self.sticker_preview_label.setMinimumSize(300, 150)
        self.sticker_preview_label.setStyleSheet("background: transparent; border: none;")
        self.sticker_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sticker_preview_label.setText("Vorschau wird geladen...")
        preview_container_layout.addWidget(self.sticker_preview_label)
        
        preview_layout.addWidget(preview_container, stretch=1)
        
        right_layout.addWidget(preview_group)
        
        top_splitter.addWidget(right_widget)
        
        # Splitter-Verhältnis setzen (60% links, 40% rechts)
        top_splitter.setSizes([600, 400])
        layout.addWidget(top_splitter)
        
        # === Tabelle ===
        table_group = QGroupBox("Equipment-Tabelle")
        table_layout = QVBoxLayout(table_group)
        
        # Toolbar für Tabelle
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        
        add_row_btn = GlassGlowButton("+", dark_mode=False)
        add_row_btn.setMinimumHeight(36)
        add_row_btn.setFixedWidth(60)
        add_row_btn.setToolTip("Zeile hinzufügen")
        add_row_btn.clicked.connect(self._add_row)
        toolbar.addWidget(add_row_btn)
        
        remove_row_btn = GlassGlowButton("-", dark_mode=False)
        remove_row_btn.setMinimumHeight(36)
        remove_row_btn.setFixedWidth(60)
        remove_row_btn.setToolTip("Zeile entfernen")
        remove_row_btn.clicked.connect(self._remove_row)
        toolbar.addWidget(remove_row_btn)
        
        clear_btn = GlassGlowButton("Löschen", dark_mode=False)
        clear_btn.setMinimumHeight(36)
        clear_btn.setFixedWidth(120)
        clear_btn.setToolTip("Tabelle leeren")
        clear_btn.clicked.connect(self._clear_table)
        toolbar.addWidget(clear_btn)
        
        toolbar.addStretch()
        
        # Info Label
        self.info_label = QLabel("0 Equipments")
        self.info_label.setStyleSheet("color: #64748b; font-weight: 600;")
        toolbar.addWidget(self.info_label)
        
        table_layout.addLayout(toolbar)
        
        # Tabelle erstellen
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "Equipment Name", "Energy ID", "Beschreibung", "✓"
        ])
        
        # Header Styling
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 120)
        self.table.setColumnWidth(3, 40)
        
        # Tabellen-Einstellungen (verwendet UI Standards)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setDefaultSectionSize(MIN_TABLE_ROW_HEIGHT)  # Standard: 45px
        self.table.setMinimumHeight(300)
        
        # Tabellen-Änderungen mit Vorschau verbinden
        self.table.cellChanged.connect(self._on_table_cell_changed)
        
        table_layout.addWidget(self.table)
        layout.addWidget(table_group)
        
        # === LOTO & Sticker Einstellungen ===
        settings_group = QGroupBox("Sticker Einstellungen")
        settings_layout = QHBoxLayout(settings_group)
        
        # LOTO Modus
        loto_layout = QVBoxLayout()
        loto_label = QLabel("LOTO Modus:")
        loto_label.setStyleSheet("font-weight: 600;")
        loto_layout.addWidget(loto_label)
        
        self.loto_group = QButtonGroup()
        self.single_radio = QRadioButton("Single-LOTO")
        self.multi_radio = QRadioButton("Multi-LOTO")
        self.multi_radio.setObjectName("multiLotoRadio")
        self.multi_radio.setStyleSheet("""
            QRadioButton#multiLotoRadio {
                color: #1e293b;
                font-size: 13px;
                font-weight: 600;
                spacing: 8px;
                padding: 4px 8px;
            }
            QRadioButton#multiLotoRadio::indicator {
                width: 18px;
                height: 18px;
                border-radius: 9px;
                border: 2px solid #94a3b8;
                background-color: #ffffff;
            }
            QRadioButton#multiLotoRadio::indicator:hover {
                border-color: #22c55e;
            }
            QRadioButton#multiLotoRadio::indicator:checked {
                background-color: #22c55e;
                border-color: #16a34a;
            }
        """)
        self.single_radio.setChecked(True)
        self.loto_group.addButton(self.single_radio)
        self.loto_group.addButton(self.multi_radio)
        loto_layout.addWidget(self.single_radio)
        loto_layout.addWidget(self.multi_radio)
        settings_layout.addLayout(loto_layout)
        
        settings_layout.addSpacing(30)
        
        # Sticker Preset (wie in Sticker-Einstellungen: 3 Presets)
        preset_layout = QVBoxLayout()
        preset_label = QLabel("Sticker Preset:")
        preset_label.setStyleSheet("font-weight: 600;")
        preset_layout.addWidget(preset_label)
        
        self.preset_combo = ModernComboBox(dark_mode=False)
        self.preset_combo.addItems(["Preset 1", "Preset 2", "Preset 3"])
        self.preset_combo.setMinimumWidth(150)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        preset_layout.addWidget(self.preset_combo)
        
        settings_layout.addLayout(preset_layout)
        
        settings_layout.addStretch()
        layout.addWidget(settings_group)
        
        # === Buttons ===
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_layout.addStretch()
        
        cancel_btn = GlassGlowButton("Abbrechen", dark_mode=False)
        cancel_btn.setMinimumHeight(44)
        cancel_btn.setFixedWidth(150)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        self.add_btn = GlassGlowButton("Hinzufügen", dark_mode=False)
        self.add_btn.setMinimumHeight(44)
        self.add_btn.setFixedWidth(150)
        self.add_btn.clicked.connect(self._on_add)
        btn_layout.addWidget(self.add_btn)
        
        layout.addLayout(btn_layout)
    
    def _add_initial_rows(self):
        """Initiale Zeilen hinzufügen."""
        self._generate_rows()
    
    def _generate_rows(self):
        """Generiert Zeilen basierend auf Auto-Nummerierung."""
        if not self.auto_number_check.isChecked():
            return
        
        count = self.count_spin.value()
        start = self.start_spin.value()
        prefix = self.prefix_entry.text()
        
        self.table.setRowCount(count)
        
        # Verwende Standard-Textfarbe aus UI Standards
        text_color = INPUT_TEXT_COLOR_QT
        
        for i in range(count):
            num = start + i
            name = f"{prefix}{num}" if prefix else str(num)
            
            # Equipment Name
            name_item = QTableWidgetItem(name)
            name_item.setForeground(QBrush(text_color))
            self.table.setItem(i, 0, name_item)
            
            # Energy ID (automatisch: E + Nummer)
            energy_item = QTableWidgetItem(f"E{num}")
            energy_item.setForeground(QBrush(text_color))
            self.table.setItem(i, 1, energy_item)
            
            # Beschreibung (leer)
            desc_item = QTableWidgetItem("")
            desc_item.setForeground(QBrush(text_color))
            self.table.setItem(i, 2, desc_item)
            
            # Checkbox
            check_item = QTableWidgetItem()
            check_item.setCheckState(Qt.CheckState.Checked)
            self.table.setItem(i, 3, check_item)
        
        self._update_info()
        self._update_sticker_preview()
    
    def _update_preview(self):
        """Aktualisiert die Vorschau bei Änderungen."""
        if self.auto_number_check.isChecked():
            self._generate_rows()
    
    def _on_auto_number_changed(self, checked):
        """Auto-Nummerierung ein/aus."""
        self.prefix_entry.setEnabled(checked)
        # start_spin und count_spin sind jetzt versteckt
        
        if not checked:
            # Manueller Modus - leere Tabelle mit einer Zeile
            self.table.setRowCount(1)
            text_color = INPUT_TEXT_COLOR_QT
            for col in range(3):
                item = QTableWidgetItem("")
                item.setForeground(QBrush(text_color))
                self.table.setItem(0, col, item)
            check_item = QTableWidgetItem()
            check_item.setCheckState(Qt.CheckState.Checked)
            self.table.setItem(0, 3, check_item)
        else:
            self._generate_rows()
    
    def _add_row(self):
        """Fügt eine neue Zeile hinzu und übernimmt Beschreibung, Prefix und Energy-ID automatisch."""
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # Beschreibung aus der ersten Zeile übernehmen
        first_row_description = ""
        if self.table.rowCount() > 1:  # Es gibt bereits mindestens eine Zeile
            desc_item = self.table.item(0, 2)
            if desc_item:
                first_row_description = desc_item.text()
        
        # Automatischer Equipment-Name mit Prefix und Nummer
        auto_name = ""
        auto_energy_id = ""
        if self.auto_number_check.isChecked():
            prefix = self.prefix_entry.text().strip()
            # Nächste Nummer berechnen (aktuelle Zeile + start_spin Wert)
            next_num = row + self.start_spin.value()
            auto_name = f"{prefix}{next_num}" if prefix else str(next_num)
            # Energy-ID automatisch erstellen: E + Nummer
            auto_energy_id = f"E{next_num}"
        
        text_color = INPUT_TEXT_COLOR_QT
        for col in range(3):
            item = QTableWidgetItem("")
            # Equipment-Name automatisch setzen
            if col == 0 and auto_name:
                item.setText(auto_name)
            # Energy-ID automatisch setzen
            if col == 1 and auto_energy_id:
                item.setText(auto_energy_id)
            # Beschreibung aus erster Zeile übernehmen
            if col == 2 and first_row_description:
                item.setText(first_row_description)
            item.setForeground(QBrush(text_color))
            self.table.setItem(row, col, item)
        
        check_item = QTableWidgetItem()
        check_item.setCheckState(Qt.CheckState.Checked)
        self.table.setItem(row, 3, check_item)
        
        self._update_info()
    
    def _remove_row(self):
        """Entfernt die ausgewählte Zeile."""
        current_row = self.table.currentRow()
        if current_row >= 0:
            self.table.removeRow(current_row)
        elif self.table.rowCount() > 0:
            self.table.removeRow(self.table.rowCount() - 1)
        
        self._update_info()
    
    def _clear_table(self):
        """Leert die Tabelle."""
        self.table.setRowCount(0)
        self._update_info()
    
    def _update_info(self):
        """Aktualisiert das Info-Label."""
        checked_count = 0
        for row in range(self.table.rowCount()):
            check_item = self.table.item(row, 3)
            if check_item and check_item.checkState() == Qt.CheckState.Checked:
                # Prüfe ob Name vorhanden
                name_item = self.table.item(row, 0)
                if name_item and name_item.text().strip():
                    checked_count += 1
        
        self.info_label.setText(f"{checked_count} Equipment(s) ausgewählt")
    
    def _get_loto_mode(self) -> str:
        """Gibt den LOTO-Modus zurück."""
        return "multi" if self.multi_radio.isChecked() else "single"
    
    def _get_preset_index(self) -> int:
        """Gibt den Preset-Index zurück (0, 1, oder 2)."""
        return self.preset_combo.currentIndex()
    
    def _on_add(self):
        """Validiert und speichert die Daten."""
        location = self.location_combo.text().strip()
        system = self.system_combo.text().strip()
        
        if not location:
            self._show_error("Bitte einen Standort angeben!")
            return
        
        if not system:
            self._show_error("Bitte ein System angeben!")
            return
        
        # Sammle alle markierten Zeilen
        self.result_data = []
        
        for row in range(self.table.rowCount()):
            check_item = self.table.item(row, 3)
            if not check_item or check_item.checkState() != Qt.CheckState.Checked:
                continue
            
            name_item = self.table.item(row, 0)
            energy_item = self.table.item(row, 1)
            desc_item = self.table.item(row, 2)
            
            name = name_item.text().strip() if name_item else ""
            if not name:
                continue
            
            energy_id = energy_item.text().strip() if energy_item else ""
            description = desc_item.text().strip() if desc_item else ""
            
            self.result_data.append({
                "location": location,
                "system": system,
                "name": name,
                "energy_id": energy_id,
                "description": description,
                "symbol_type": self.symbol_combo.currentText().upper(),
                "preset_index": self._get_preset_index(),
                "loto_mode": self._get_loto_mode(),
                "add_to_collection": False,
                "qr_code_path": self.qr_code_path  # QR-Code Pfad hinzufügen
            })
        
        if not self.result_data:
            self._show_error("Keine gültigen Equipments zum Hinzufügen!")
            return
        
        self.accept()
    
    def _show_error(self, message: str):
        """Zeigt eine Fehlermeldung."""
        from PyQt6.QtWidgets import QMessageBox
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Hinweis")
        msg.setText(message)
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #ffffff;
            }
            QMessageBox QLabel {
                color: #1e293b;
                font-size: 13px;
            }
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: 600;
            }
        """)
        msg.exec()
    
    def _select_qr_code(self):
        """QR-Code Bild auswählen."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "QR-Code auswählen",
            "",
            "Bilder (*.png *.jpg *.jpeg *.bmp *.gif);;Alle Dateien (*.*)"
        )
        
        if file_path:
            self.qr_code_path = file_path
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    140, 140,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.qr_preview_label.setPixmap(scaled_pixmap)
                self.qr_preview_label.setStyleSheet("""
                    QLabel {
                        background-color: #ffffff;
                        border: 2px solid #22c55e;
                        border-radius: 10px;
                        padding: 5px;
                    }
                """)
                # Sticker-Vorschau aktualisieren mit neuem QR-Code
                self._update_sticker_preview()
            else:
                self.qr_preview_label.setText("Fehler beim\nLaden")
    
    def _clear_qr_code(self):
        """QR-Code entfernen."""
        self.qr_code_path = None
        self.qr_preview_label.clear()
        self.qr_preview_label.setText("Kein QR-Code")
        self.qr_preview_label.setStyleSheet("""
            QLabel {
                background-color: #f1f5f9;
                border: 2px dashed #94a3b8;
                border-radius: 10px;
            }
        """)
        # Sticker-Vorschau aktualisieren ohne QR-Code
        self._update_sticker_preview()
    
    def _on_preset_changed(self, index):
        """Preset gewechselt - Konfiguration laden und Vorschau aktualisieren."""
        try:
            import json
            from core.paths import get_config_path
            
            config_path = get_config_path("config.json")
            if not config_path.exists():
                return
            
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            presets = data.get("sticker_presets", []) or []
            if not isinstance(presets, list) or index >= len(presets):
                return
            
            preset = presets[index]
            if not preset or not self.sticker_config:
                return
            
            # Preset-Werte anwenden
            if "width_mm" in preset:
                self.sticker_config.width_mm = float(preset["width_mm"])
            if "height_mm" in preset:
                self.sticker_config.height_mm = float(preset["height_mm"])
            if "dpi" in preset:
                self.sticker_config.dpi = int(preset["dpi"])
            if "corner_radius" in preset:
                self.sticker_config.corner_radius = int(preset["corner_radius"])
            if "outline_width" in preset:
                self.sticker_config.outline_width = int(preset["outline_width"])
            if "font_size_mm" in preset:
                self.sticker_config.font_size_mm = float(preset["font_size_mm"])
            if "line_height_mm" in preset:
                self.sticker_config.line_height_mm = float(preset["line_height_mm"])
            if "symbol_size_mm" in preset:
                self.sticker_config.symbol_size_mm = float(preset["symbol_size_mm"])
            if "symbol_corner_radius" in preset:
                self.sticker_config.symbol_corner_radius = int(preset["symbol_corner_radius"])
            if "symbol_offset_x_mm" in preset:
                self.sticker_config.symbol_offset_x_mm = float(preset["symbol_offset_x_mm"])
            if "symbol_offset_y_mm" in preset:
                self.sticker_config.symbol_offset_y_mm = float(preset["symbol_offset_y_mm"])
            if "sticker_color" in preset:
                self.sticker_config.sticker_color = preset["sticker_color"]
            if "font_path" in preset:
                self.sticker_config.font_path = preset["font_path"]
            
            # Generator mit neuer Konfiguration neu erstellen
            from generators.sticker_generator import StickerGenerator
            self.sticker_generator = StickerGenerator(self.sticker_config)
            
            # Vorschau aktualisieren
            self._update_sticker_preview()
            
        except Exception as e:
            print(f"Fehler beim Laden des Presets: {e}")
    
    def _on_table_cell_changed(self, row, column):
        """Tabellenzelle geändert - Vorschau aktualisieren wenn erste Zeile."""
        if row == 0 and column in (0, 1, 2):  # Equipment Name, Energy ID oder Beschreibung
            self._update_sticker_preview()
    
    def _update_sticker_preview(self):
        """Sticker-Vorschau mit Debounce aktualisieren."""
        if self.preview_timer.isActive():
            self.preview_timer.stop()
        self.preview_timer.start(33)  # ~30 FPS (1000ms / 30 = 33ms)
    
    def _do_update_sticker_preview(self):
        """Echte Sticker-Vorschau generieren."""
        try:
            if not self.sticker_generator:
                self.sticker_preview_label.setText("Generator nicht verfügbar")
                return
            
            # Cache leeren für frische Vorschau mit aktuellem QR-Code
            if hasattr(self.sticker_generator, '_img_cache'):
                self.sticker_generator._img_cache.clear()
            
            # Werte aus der ersten Zeile der Tabelle oder Beispielwerte
            energy_id = ""
            equipment_name = ""
            description = ""
            
            if self.table.rowCount() > 0:
                name_item = self.table.item(0, 0)
                energy_item = self.table.item(0, 1)
                desc_item = self.table.item(0, 2)
                if name_item:
                    equipment_name = name_item.text().strip()
                if energy_item:
                    energy_id = energy_item.text().strip()
                if desc_item:
                    description = desc_item.text().strip()
            
            # Fallback auf Beispielwerte
            if not equipment_name:
                prefix = self.prefix_entry.text().strip()
                start = self.start_spin.value()
                equipment_name = f"{prefix}{start}" if prefix else f"Equipment-{start}"
            
            if not energy_id:
                energy_id = "E-001"
            
            # Symbol-Typ ermitteln
            symbol_name = self.symbol_combo.currentText().upper()
            try:
                symbol_type = SymbolType[symbol_name]
            except (KeyError, AttributeError):
                symbol_type = SymbolType.ELECTRICAL
            
            # Zeilen für Sticker bauen (mit Beschreibung wenn vorhanden)
            if description:
                lines = [energy_id, equipment_name, description]
            else:
                lines = [energy_id, equipment_name]
            
            print(f"*** PREVIEW DEBUG: lines={lines} ***")
            
            # QR-Code temporär in Konfiguration setzen
            original_qr_enabled = getattr(self.sticker_config, 'qr_mode_enabled', False)
            original_qr_path = getattr(self.sticker_config, 'qr_image_path', None)
            
            if self.qr_code_path:
                self.sticker_config.qr_mode_enabled = True
                self.sticker_config.qr_image_path = self.qr_code_path
            else:
                self.sticker_config.qr_mode_enabled = False
                self.sticker_config.qr_image_path = None
            
            try:
                # Sticker generieren
                img = self.sticker_generator.generate(symbol_type, lines)
            finally:
                # Original-Konfiguration wiederherstellen
                self.sticker_config.qr_mode_enabled = original_qr_enabled
                self.sticker_config.qr_image_path = original_qr_path
            
            # PIL zu QPixmap konvertieren
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            qimage = ImageQt(img)
            pixmap = QPixmap.fromImage(qimage)
            
            # Skalieren für Vorschau (max 350px breit)
            scaled_pixmap = pixmap.scaled(
                350, 200,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            
            self.sticker_preview_label.setPixmap(scaled_pixmap)
            
        except Exception as e:
            print(f"Sticker-Vorschau-Fehler: {e}")
            import traceback
            traceback.print_exc()
            self.sticker_preview_label.setText(f"Fehler: {e}")
    
    def get_result(self) -> list:
        """Gibt die Liste der Equipment-Daten zurück."""
        return self.result_data


def show_batch_equipment_dialog(parent, equipment_manager=None,
                                pre_location: str = "", pre_system: str = "") -> list:
    """Zeigt den Batch-Equipment-Dialog an.
    
    Returns:
        Liste von Equipment-Dicts oder None bei Abbruch
    """
    existing_locations = []
    existing_systems = []
    
    if equipment_manager:
        try:
            hierarchy = equipment_manager.get_hierarchy()
            if hierarchy:
                existing_locations = list(hierarchy.keys())
                for loc_data in hierarchy.values():
                    if isinstance(loc_data, dict):
                        systems = loc_data.get("systems", [])
                        for sys in systems:
                            if isinstance(sys, dict):
                                sys_name = sys.get("name", "")
                                if sys_name and sys_name not in existing_systems:
                                    existing_systems.append(sys_name)
        except Exception:
            pass
    
    dialog = BatchEquipmentDialog(
        parent,
        equipment_manager=equipment_manager,
        existing_locations=existing_locations,
        existing_systems=existing_systems
    )
    
    # Vorauswahl setzen
    if pre_location:
        dialog.location_combo.setText(pre_location)
    if pre_system:
        dialog.system_combo.setText(pre_system)
    
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog.get_result()
    
    return None
