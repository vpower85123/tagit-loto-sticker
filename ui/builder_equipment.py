"""Equipment-Tab UI Builder.

Enthält:
- build_equipment_tab: Equipment-Verwaltungs-Tab
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTreeWidget, QFrame
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt
import qtawesome as qta

from ui.theme import Theme, get_contrasting_text_color, get_theme_colors
from ui.builder_utils import add_depth_shadow, _create_glass_button


def build_equipment_tab(self):
    """Equipment-Verwaltungs-Tab (modernes Layout analog Generator)"""
    equipment_widget = QWidget()
    
    content_layout = QHBoxLayout(equipment_widget)
    content_layout.setSpacing(20)
    content_layout.setContentsMargins(16, 16, 16, 16)

    if self.equipment_manager is None:
        error_label = QLabel("Equipment Management nicht verfügbar aufgrund eines Fehlers beim Laden.")
        error_label.setStyleSheet("color: red; font-weight: bold; padding: 20px;")
        content_layout.addWidget(error_label)
        self.tab_widget.addTab(equipment_widget, "Equipment")
        return

    # Equipment Tree (Links)
    tree_card = QWidget()
    tree_card.setObjectName("tree_card")
    tree_card.setStyleSheet("""
        QWidget#tree_card {
            background-color: #ffffff;
            border-radius: 20px;
            border: none;
        }
    """)
    tree_card_layout = QVBoxLayout(tree_card)
    tree_card_layout.setContentsMargins(18, 16, 18, 16)
    tree_card_layout.setSpacing(14)

    heading_font = QFont("Bahnschrift", 13)
    heading_font.setWeight(QFont.Weight.Bold)
    subheading_font = QFont("Bahnschrift", 11)
    primary_text = "#1f2a37"
    secondary_text = "#5f6c80"

    tree_title = QLabel("Equipment-Verwaltung")
    tree_title.setFont(heading_font)
    tree_title.setStyleSheet(f"color: {primary_text}; letter-spacing: 0.6px; background-color: transparent;")
    tree_card_layout.addWidget(tree_title)

    tree_subtitle = QLabel("Standorte, Systeme und Betriebsmittel organisieren")
    tree_subtitle.setFont(subheading_font)
    tree_subtitle.setStyleSheet(f"color: {secondary_text}; background-color: transparent;")
    tree_subtitle.setWordWrap(True)
    tree_card_layout.addWidget(tree_subtitle)

    tree_card_layout.addSpacing(6)

    self.equipment_tree = QTreeWidget()
    self.equipment_tree.setHeaderHidden(True)
    self.equipment_tree.setMinimumHeight(450)
    self.equipment_tree.setAlternatingRowColors(True)
    self.equipment_tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
    self.equipment_tree.setStyleSheet(
        "QTreeWidget{border:1px solid #ddd; border-radius:4px; background:white;}"
        "QTreeWidget::item{padding:6px; font-size:11pt;}"
        "QTreeWidget::item:selected{background:#e0e0e0; color:black;}"
        "QTreeWidget::item:hover{background:#f5f5f5;}"
    )
    font = QFont("Bahnschrift", 11)
    self.equipment_tree.setFont(font)

    tree_card_layout.addWidget(self.equipment_tree)
    add_depth_shadow(tree_card)
    content_layout.addWidget(tree_card, stretch=1)
    
    # Aktionsbereich (Rechts)
    actions_card = QWidget()
    actions_card.setObjectName("actions_card")
    actions_card.setStyleSheet("""
        QWidget#actions_card {
            background-color: #ffffff;
            border-radius: 20px;
            border: none;
        }
    """)
    actions_card_layout = QVBoxLayout(actions_card)
    actions_card_layout.setContentsMargins(18, 16, 18, 16)
    actions_card_layout.setSpacing(14)

    actions_title = QLabel("Aktionen")
    actions_title.setFont(heading_font)
    actions_title.setStyleSheet(f"color: {primary_text}; letter-spacing: 0.6px; background-color: transparent;")
    actions_card_layout.addWidget(actions_title)

    actions_subtitle = QLabel("Equipment hinzufügen, bearbeiten oder löschen")
    actions_subtitle.setFont(subheading_font)
    actions_subtitle.setStyleSheet(f"color: {secondary_text}; background-color: transparent;")
    actions_subtitle.setWordWrap(True)
    actions_card_layout.addWidget(actions_subtitle)

    actions_card_layout.addSpacing(6)

    add_depth_shadow(actions_card)

    actions_layout = QVBoxLayout()
    actions_layout.setSpacing(12)
    
    # Buttons
    button_frame = QWidget()
    button_frame.setStyleSheet("QWidget { background-color: transparent; }")
    button_main_layout = QVBoxLayout(button_frame)
    button_main_layout.setSpacing(20)
    button_main_layout.setContentsMargins(0, 0, 0, 0)
    
    # Erste Gruppe: Hinzufügen (Vertikal)
    add_button_layout = QVBoxLayout()
    add_button_layout.setSpacing(15)
    add_button_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
    
    self.batch_equipment_btn = _create_glass_button(self, "Batch")
    self.batch_equipment_btn.setToolTip("Mehrere Equipments auf einmal hinzufügen")
    self.batch_equipment_btn.setFixedWidth(150)
    add_button_layout.addWidget(self.batch_equipment_btn)
    
    button_main_layout.addLayout(add_button_layout)
    
    # Trenner
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFrameShadow(QFrame.Shadow.Sunken)
    line.setStyleSheet("background-color: #ddd;")
    button_main_layout.addWidget(line)
    
    # Zweite Gruppe: Datei-Aktionen (Vertikal)
    action_button_layout = QVBoxLayout()
    action_button_layout.setSpacing(15)
    action_button_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

    self.import_equipment_btn = _create_glass_button(self, "Excel-Import")
    self.import_equipment_btn.setToolTip("Equipment aus Excel importieren")
    self.import_equipment_btn.setFixedWidth(150)
    self.import_equipment_btn.clicked.connect(self._import_equipment_from_excel)
    action_button_layout.addWidget(self.import_equipment_btn)

    self.save_equipment_btn = _create_glass_button(self, "Speichern")
    self.save_equipment_btn.setToolTip("Equipment speichern")
    self.save_equipment_btn.setFixedWidth(150)
    action_button_layout.addWidget(self.save_equipment_btn)
    
    button_main_layout.addLayout(action_button_layout)
    
    # Trenner für Export/Import
    line2 = QFrame()
    line2.setFrameShape(QFrame.Shape.HLine)
    line2.setFrameShadow(QFrame.Shadow.Sunken)
    line2.setStyleSheet("background-color: #ddd;")
    button_main_layout.addWidget(line2)
    
    # Dritte Gruppe: Datenbank Export/Import
    db_button_layout = QVBoxLayout()
    db_button_layout.setSpacing(15)
    db_button_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
    
    self.export_db_btn = _create_glass_button(self, "DB Export")
    self.export_db_btn.setIcon(qta.icon('ph.export', color='#1f2937'))
    self.export_db_btn.setToolTip("Equipment-Datenbank als JSON exportieren")
    self.export_db_btn.setFixedWidth(150)
    self.export_db_btn.clicked.connect(self._export_equipment_database)
    db_button_layout.addWidget(self.export_db_btn)
    
    self.import_db_btn = _create_glass_button(self, "DB Import")
    self.import_db_btn.setIcon(qta.icon('ph.download-simple', color='#1f2937'))
    self.import_db_btn.setToolTip("Equipment-Datenbank aus JSON importieren")
    self.import_db_btn.setFixedWidth(150)
    self.import_db_btn.clicked.connect(self._import_equipment_database)
    db_button_layout.addWidget(self.import_db_btn)
    
    button_main_layout.addLayout(db_button_layout)
    button_main_layout.addStretch()
    
    actions_layout.addWidget(button_frame)
    
    # Hilfetext
    help_label = QLabel("Tipp: Rechtsklick für Optionen, Doppelklick zum Bearbeiten")
    
    # Calculate text color
    custom_colors = getattr(self.theme_config, 'custom_colors', {}) if hasattr(self, 'theme_config') else {}
    element_bg = custom_colors.get('element_bg')
    help_text_color = "#666"
    if element_bg:
        help_text_color = get_contrasting_text_color(element_bg)
        # Make it slightly transparent/dimmer if it's white/black to keep "help text" look
        if help_text_color == "#ffffff":
             help_text_color = "rgba(255, 255, 255, 0.7)"
        else:
             help_text_color = "rgba(0, 0, 0, 0.6)"

    help_label.setStyleSheet(f"""
        font-size: 10pt; 
        color: {help_text_color}; 
        font-style: italic;
        padding: 8px 4px 4px 4px;
    """)
    help_label.setWordWrap(True)
    actions_layout.addWidget(help_label)
    
    actions_card_layout.addLayout(actions_layout)
    content_layout.addWidget(actions_card)

    self.tab_widget.addTab(equipment_widget, "Equipment")
