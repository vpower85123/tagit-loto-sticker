#!/usr/bin/env python3
"""
Vollst├ñndige PyQt6 Version der Sticker Generator App
Alle Funktionen aus der tkinter-Version integriert

Module:
- ui.wave_button: Custom animated button
- ui.theme: Theme management
- ui.dialogs: Dialog helpers
- dialogs.equipment_dialog: Equipment selection
"""

import sys
import json
import math
import logging
import os
import datetime
from pathlib import Path

# UI-Module importieren
from ui.glass_button import GlassGlowButton, ButtonSettings
from ui.theme import Theme, create_input_stylesheet, create_dialog_stylesheet, detect_system_dark_mode, get_unified_button_style
from ui.dialogs import show_info, show_warning, show_error, show_question
from ui.theme_applier import apply_main_window_theme
from ui.menu_builder import build_main_menu
from ui.builders import build_sticker_tab, build_equipment_tab, build_export_tab
from ui.components import ModernComboBox
from ui.spinboxes import StyledSpinBox, StyledDoubleSpinBox
from ui.magic_menu import MagicMenuBar
from ui.form_helpers import (
    style_text_input, style_combo_box, style_form_button,
    create_form_row, create_row_container, set_uniform_field_width,
    SPINBOX_INPUT_WIDTH, TEXT_INPUT_HEIGHT
)
from dialogs.sticker_settings_dialog import StickerSettingsDialog
from dialogs.count_settings_dialog import CountSettingsDialog
from dialogs.button_settings_dialog import ButtonSettingsDialog
from dialogs.pdf_import_dialog import PDFImportDialog
from dialogs.equipment_import_dialog import EquipmentImportDialog
from managers.license_manager import LicenseManager
from dialogs.license_dialog import LoginDialog
from typing import List, Dict, Optional, Any
import platform
import fitz  # PyMuPDF
import qtawesome as qta

# PyQt6 Imports
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QComboBox, QTreeWidget, QTreeWidgetItem,
    QTabWidget, QTabBar, QFrame, QScrollArea, QSplitter, QGroupBox, QCheckBox, QRadioButton,
    QButtonGroup, QMessageBox, QFileDialog, QColorDialog, QInputDialog, QProgressBar,
    QStatusBar, QMenuBar, QMenu, QTableWidget, QTableWidgetItem, QListWidget,
    QListWidgetItem, QDialog, QDialogButtonBox, QFormLayout, QSizePolicy,
    QSpinBox, QDoubleSpinBox, QGraphicsDropShadowEffect, QProgressDialog
)
from PyQt6.QtGui import (
    QPixmap, QImage, QPainter, QFont, QIcon, QPalette, QColor, QBrush, QPen,
    QFontDatabase
)
from PyQt6.QtCore import (
    Qt, QTimer, QSize, QRect, QPoint, QPointF, QThread, pyqtSignal, QEvent,
    QUrl, QDir, QFile, QIODevice, QStandardPaths, QPropertyAnimation, QEasingCurve,
    QSequentialAnimationGroup, QParallelAnimationGroup
)
from PyQt6.QtWidgets import QSplashScreen, QGraphicsOpacityEffect
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtGui import QTransform

# PIL f├╝r Bildverarbeitung
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageFilter, ImageQt
try:
    from PIL.Image import Resampling
    _LANCZOS = Resampling.LANCZOS
except Exception:
    try:
        _LANCZOS = Image.Resampling.LANCZOS
    except Exception:
        # Fallback for older PIL versions
        _LANCZOS = 3  # LANCZOS constant value

# ReportLab f├╝r PDF-Export (optional)
try:
    from reportlab.pdfgen import canvas as pdf_canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import ImageReader
    A4_SIZE = A4
    REPORTLAB_AVAILABLE = True
except ImportError:
    pdf_canvas = None
    A4_SIZE = None
    ImageReader = None
    REPORTLAB_AVAILABLE = False

# Feature flags
DISABLE_LOGIN_DIALOG = False
DISABLE_SPLASH_ANIMATION = True

# Logging Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from core.paths import PathManager
from core.models import SymbolType, StickerConfig as ModelStickerConfig, CountConfig, ExportConfig
from core.config_manager import ConfigManager
from managers.equipment_manager import EquipmentManager
from generators.count_manager import CountStickerGenerator
from generators.pdf_exporter_new import export_pdf_new
from core.constants import SETTINGS_DIALOG_WIDTH

# Services
from services import StickerService, CollectionService, EquipmentService

# Controllers
from controllers import CollectionController, EquipmentController, ExportController, ImportController, PreviewController, SettingsController


class _CountModeProxy:
    """Minimal get/set wrapper to mimic legacy Tkinter StringVar usage."""

    def __init__(self, initial: str = 'multi'):
        self._value = initial

    def get(self) -> str:
        return self._value

    def set(self, value: str) -> None:
        self._value = value

# ==================== MOVED TO MODULES ====================
# GlassGlowButton: ui/glass_button.py (einzige Button-Klasse)
# Theme: ui/theme.py
# Dialog helpers: ui/dialogs.py
# Equipment Dialog: dialogs/equipment_dialog.py
# License Dialog: dialogs/license_dialog.py
# =========================================================


class StickerApp(QMainWindow):
    """Hauptapplikation mit PyQt6 - alle Funktionen integriert"""

    # Type hints for UI elements
    add_location_btn: Any
    add_system_btn: Any
    add_equipment_btn: Any
    save_equipment_btn: Any
    energy_entry: Any
    equipment_entry: Any
    description_entry: Any
    collection_list: Any
    symbol_combo: Any
    equipment_tree: Any
    equipment_status_label: Any
    preview_label: Any
    scale_slider: Any
    scale_value_label: Any
    count_preview_label: Any
    single_loto_radio: Any
    multi_loto_radio: Any
    no_count_radio: Any
    collection_selection_timer: Any
    collection_scroll_cooldown_timer: Any
    tab_widget: Any
    width_label: Any
    width_container: Any
    width_spin: Any
    height_label: Any
    height_container: Any
    height_spin: Any

    def _create_styled_msgbox(self, title, text, icon=QMessageBox.Icon.Information, buttons=None):
        """Erstellt eine styled MessageBox mit Custom Dialog und GlassGlow Buttons"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel
        from ui.glass_button import GlassGlowButton
        from ui.theme import Theme
        import qtawesome as qta
        
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setModal(True)
        dialog.setFixedWidth(450)
        
        # Light theme styling
        bg_color = "#f4f6f9"
        text_color = "#2c3e50"
        
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_color};
                color: {text_color};
            }}
            QLabel {{
                color: {text_color};
            }}
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 20, 25, 20)
        
        # Icon + Nachricht
        content_layout = QHBoxLayout()
        
        # Phosphor Icon
        icon_name = None
        icon_color = text_color
        if icon == QMessageBox.Icon.Information:
            icon_name = "ph.info"
            icon_color = "#3b82f6"
        elif icon == QMessageBox.Icon.Warning:
            icon_name = "ph.warning"
            icon_color = "#f59e0b"
        elif icon == QMessageBox.Icon.Critical:
            icon_name = "ph.x-circle"
            icon_color = "#ef4444"
        elif icon == QMessageBox.Icon.Question:
            icon_name = "ph.question"
            icon_color = "#8b5cf6"
        
        if icon_name:
            icon_label = QLabel()
            icon_label.setPixmap(qta.icon(icon_name, color=icon_color).pixmap(28, 28))
            icon_label.setFixedSize(32, 32)
            icon_label.setStyleSheet("padding-right: 6px;")
            content_layout.addWidget(icon_label)
        
        # Text-Label
        msg_label = QLabel(text)
        msg_label.setStyleSheet(f"font-size: 12px; color: {text_color};")
        msg_label.setWordWrap(True)
        content_layout.addWidget(msg_label, 1)
        
        layout.addLayout(content_layout)
        layout.addSpacing(10)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        button_layout.addStretch()
        
        if buttons:
            # Custom Buttons
            if buttons & QMessageBox.StandardButton.No:
                no_btn = GlassGlowButton("Nein")
                no_btn.setFixedHeight(32)
                no_btn.setMinimumWidth(100)
                no_btn.clicked.connect(lambda: dialog.done(QMessageBox.StandardButton.No))
                button_layout.addWidget(no_btn)
            
            if buttons & QMessageBox.StandardButton.Yes:
                yes_btn = GlassGlowButton("Ja")
                yes_btn.setFixedHeight(32)
                yes_btn.setMinimumWidth(100)
                yes_btn.clicked.connect(lambda: dialog.done(QMessageBox.StandardButton.Yes))
                button_layout.addWidget(yes_btn)
            elif buttons & QMessageBox.StandardButton.Ok:
                ok_btn = GlassGlowButton("OK")
                ok_btn.setFixedHeight(32)
                ok_btn.setMinimumWidth(100)
                ok_btn.clicked.connect(lambda: dialog.done(QMessageBox.StandardButton.Ok))
                button_layout.addWidget(ok_btn)
        else:
            # Default: nur OK Button
            ok_btn = GlassGlowButton("OK")
            ok_btn.setFixedHeight(32)
            ok_btn.setMinimumWidth(100)
            ok_btn.clicked.connect(dialog.accept)
            button_layout.addWidget(ok_btn)
        
        layout.addLayout(button_layout)
        
        return dialog

    def logout(self):
        """Benutzer abmelden und Login-Screen zeigen."""
        msg = self._create_styled_msgbox(
            "Abmelden",
            "M├Âchten Sie sich wirklich abmelden?",
            QMessageBox.Icon.Question,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        reply = msg.exec()
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.license_manager.logout():
                # Fenster verstecken
                self.hide()
                
                # Login Dialog zeigen
                dialog = LoginDialog(self.license_manager)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    # Bei Erfolg: Men├╝ neu aufbauen (f├╝r Lizenz-Info Update) und Fenster zeigen
                    self._create_menu()
                    self.show()
                else:
                    # Bei Abbruch: App beenden
                    self.close()
            else:
                warn_msg = self._create_styled_msgbox("Fehler", "Abmelden fehlgeschlagen.", QMessageBox.Icon.Warning)
                warn_msg.exec()

    def _new_project(self):
        """Neues Projekt erstellen (Collection leeren und Felder zur├╝cksetzen)"""
        msg = self._create_styled_msgbox(
            "Neues Projekt",
            "M├Âchten Sie ein neues Projekt starten? Die aktuelle Sammlung wird geleert.",
            QMessageBox.Icon.Question,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        reply = msg.exec()
        
        if reply == QMessageBox.StandardButton.Yes:
            # Collection leeren
            self.clear_collection()
            
            # Eingabefelder zur├╝cksetzen
            if hasattr(self, 'energy_entry'):
                self.energy_entry.clear()
            if hasattr(self, 'equipment_entry'):
                self.equipment_entry.clear()
            if hasattr(self, 'description_entry'):
                self.description_entry.clear()
            
            # Preview zur├╝cksetzen
            if hasattr(self, 'preview_controller'):
                self.preview_controller.update_preview()
            
            logger.info("Neues Projekt erstellt")

    def reload_configs(self):
        """Konfiguration neu laden"""
        try:
            # Konfiguration neu laden
            self.sticker_config, self.count_config, self.theme_config = self.config_manager.load()
            self.export_config = self.config_manager.load_export()
            
            # Services aktualisieren
            if hasattr(self, 'sticker_service'):
                self.sticker_service.update_config(self.sticker_config)
            
            # Generator aktualisieren
            if hasattr(self, 'sticker_generator'):
                self.sticker_generator = self.sticker_service.generator
            
            if hasattr(self, 'count_generator'):
                self.count_generator = CountStickerGenerator(self.count_config)
            
            # Preview aktualisieren
            if hasattr(self, 'preview_controller'):
                self.preview_controller.sticker_config = self.sticker_config
                self.preview_controller.sticker_generator = self.sticker_generator
                self.preview_controller.update_preview()
            
            msg = self._create_styled_msgbox("Erfolg", "Konfiguration wurde neu geladen!")
            msg.exec()
            logger.info("Konfiguration neu geladen")
            
        except Exception as e:
            msg = self._create_styled_msgbox("Fehler", f"Fehler beim Neuladen der Konfiguration:\n{str(e)}", QMessageBox.Icon.Critical)
            msg.exec()
            logger.exception("Error reloading configs")

    def _show_about(self):
        """├£ber-Dialog anzeigen"""
        about_text = """
<h2>LOTO Sticker Generator</h2>
<p><b>Version:</b> 2.0</p>
<p><b>Beschreibung:</b> Generator f├╝r LOTO (Lock-Out Tag-Out) Sticker</p>
<p><b>Features:</b></p>
<ul>
    <li>Erstellen von einzelnen und mehreren LOTO Stickern</li>
    <li>Equipment-Verwaltung mit hierarchischer Struktur</li>
    <li>PDF-Export mit verschiedenen Formaten</li>
    <li>Count-Sticker f├╝r Single/Multi LOTO</li>
    <li>Konfigurierbare Einstellungen f├╝r Sticker und Count</li>
</ul>
<p><b>Entwicklung:</b> TAG!T Team</p>
        """
        
        QMessageBox.about(self, "├£ber LOTO Sticker Generator", about_text)


    def __init__(self):
        super().__init__()
        
        # Lizenzpr├╝fung
        self.license_manager = LicenseManager()
        if not DISABLE_LOGIN_DIALOG:
            is_valid, message, expiry = self.license_manager.check_license()
            if not is_valid:
                dialog = LoginDialog(self.license_manager)
                if dialog.exec() != QDialog.DialogCode.Accepted:
                    sys.exit(0)
        else:
            logger.info("Login dialog disabled, skipping license prompt at startup.")
        
        self.setWindowTitle("LOTO Sticker Generator")
        self.setMinimumSize(1400, 900)
        self.resize(1600, 1000)
        
        # App-Icon setzen (HQ PNG f├╝r beste Qualit├ñt in Taskbar)
        icon_path = Path(__file__).parent / "assets" / "icons" / "app_icon_hq.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        else:
            # Fallback auf ICO
            ico_path = Path(__file__).parent / "assets" / "icons" / "app_icon.ico"
            if ico_path.exists():
                self.setWindowIcon(QIcon(str(ico_path)))
        
        # Starte App maximiert (Vollbild-Fenstermodus)
        self.setWindowState(Qt.WindowState.WindowMaximized)

        # UI Skalierung
        self.ui_scale = 1.2

        # ConfigManager
        self.config_manager = ConfigManager()

        # Initialize UI attributes to None
        self.add_location_btn = None
        self.add_system_btn = None
        self.add_equipment_btn = None
        self.save_equipment_btn = None
        self.energy_entry = None
        self.equipment_entry = None
        self.description_entry = None
        self.collection_list = None
        self.symbol_combo = None
        self.equipment_tree = None
        self.count_sticker_copies_spinbox = None
        self._current_selected_count_sticker_row = None
        self.equipment_status_label = None
        self.preview_label = None
        self.scale_slider = None
        self.scale_value_label = None
        self.count_preview_label = None
        self.single_loto_radio = None
        self.multi_loto_radio = None
        self.no_count_radio = None
        self.loto_button_group = None
        self.collection_selection_timer = None
        self.collection_scroll_cooldown_timer = None
        self.count_sticker_copies_spinbox = None  # F├╝r editierbare pro-Sticker Kopien-Anzahl
        self.tab_widget = None
        self.format_combo = None
        self.width_label = None
        self.width_container = None
        self.width_spin = None
        self.height_label = None
        self.height_container = None
        self.height_spin = None
        self.roll_width_label = None
        self.roll_width_container = None
        self.roll_width_spin = None

        # Konfiguration laden - verwende Original ConfigManager API
        self.sticker_config, self.count_config, self.theme_config = self.config_manager.load()
        self.export_config = self.config_manager.load_export()

        # Form-spezifische Konfigurationen speichern
        self.current_form_type = "rectangle"  # Standard-Form
        self.form_configs = {
            "rectangle": None,  # Wird beim ersten Laden gef├╝llt
            "square": None,
            "circle": None
        }
        # Speichere die Initial-Konfiguration f├╝r Rechteck
        self._save_current_form_config()

        initial_mode = getattr(self.export_config, 'export_mode', 'multi') or 'multi'
        self.count_mode = _CountModeProxy(initial_mode)
        self.current_loto_mode = initial_mode

        initial_mode = getattr(self.export_config, 'export_mode', 'multi') or 'multi'
        self.count_mode = _CountModeProxy(initial_mode)
        self.current_loto_mode = initial_mode
        
        # Button-Einstellungen laden
        ButtonSettings.load_from_file()
        
        # Pfad f├╝r persistente Description-Einstellungen
        self.description_settings_path = Path(__file__).parent / "config" / "description_settings.json"

        # ========== SERVICES (Business Logic Layer) ==========
        # Sticker Service - verwaltet Sticker-Generierung
        self.sticker_service = StickerService(self.sticker_config)
        self.sticker_service.sticker_generated.connect(self._on_sticker_generated)
        self.sticker_service.config_changed.connect(self._on_sticker_config_changed)
        self.sticker_service.generation_error.connect(self._on_generation_error)
        
        # Collection Service - verwaltet Sticker-Collection
        self.collection_service = CollectionService()
        self.collection_service.collection_changed.connect(self._on_collection_changed)
        self.collection_service.item_added.connect(self._on_item_added_to_collection)
        
        # Equipment Service - verwaltet Equipment mit Suche
        self.equipment_path = Path(__file__).parent / "config" / "equipment.json"
        self.equipment_service = EquipmentService(self.equipment_path)
        self.equipment_service.equipment_changed.connect(self._on_equipment_changed)
        self.equipment_service.equipment_saved.connect(self._on_equipment_saved)
        
        # Legacy: Direkter Zugriff auf Manager (f├╝r R├╝ckw├ñrtskompatibilit├ñt)
        self.sticker_generator = self.sticker_service.generator
        self.equipment_manager = self.equipment_service.get_manager()
        # ======================================================

        # Count Generator (noch nicht in Service ausgelagert)
        self.count_generator = CountStickerGenerator(self.count_config)

        # Legacy: Collection als Liste (f├╝r R├╝ckw├ñrtskompatibilit├ñt)
        # TODO: Alle Zugriffe auf self.collection durch self.collection_service ersetzen
        self.collection = []
        self._manual_sort_mode = None
        self.collection_export_sources = set()
        
        # Theme initialisieren
        # Theme immer auf Light setzen
        self.theme = Theme.LIGHT

        # Preview-Scale f├╝r Count (an Sticker-Preview-Scale gekoppelt)
        # Stelle sicher, dass der geladene Wert das Maximum 2.0 nicht ├╝berschreitet
        loaded_scale = float(getattr(self.sticker_config, 'preview_scale', 2.0) or 2.0)
        if loaded_scale > 2.0:
            self.sticker_config.preview_scale = 2.0
            loaded_scale = 2.0
        self.count_preview_scale = loaded_scale

        # UI aufbauen
        self._build_ui()
        
        # Timer f├╝r Collection Selection Debouncing initialisieren
        self.collection_selection_timer = QTimer(self)
        self.collection_selection_timer.setSingleShot(True)
        self.collection_selection_timer.timeout.connect(self._on_collection_item_selected_debounced)
        
        # Equipment Controller - verwaltet Equipment-Tree UI (nach UI-Erstellung!)
        self.equipment_controller = EquipmentController(
            self.equipment_service.get_manager(),
            parent=self
        )
        self.equipment_controller.equipment_selected.connect(self._on_equipment_selected_from_tree)
        self.equipment_controller.equipment_saved.connect(self._on_equipment_saved)
        
        # Equipment Controller mit UI verbinden
        if hasattr(self, 'equipment_tree'):
            self.equipment_controller.set_tree_widget(self.equipment_tree)
            self.equipment_controller.set_status_label(self.equipment_status_label)
        
        # Equipment-Buttons mit Controller verbinden
        if hasattr(self, 'batch_equipment_btn') and self.batch_equipment_btn:
            self.batch_equipment_btn.clicked.connect(self.equipment_controller.add_equipment_batch)
        if hasattr(self, 'save_equipment_btn'):
            self.save_equipment_btn.clicked.connect(self.equipment_controller.save_equipment)
        
        # Export Controller - verwaltet PDF-Export (nach UI-Erstellung!)
        self.export_controller = ExportController(
            self.export_config,
            self.config_manager,
            parent=self
        )

        # Export-UI Elemente an Controller binden (damit Rollmodus-Visibility nach Neustart stimmt)
        if getattr(self, 'width_spin', None) is not None and getattr(self, 'height_spin', None) is not None and getattr(self, 'format_combo', None) is not None:
            self.export_controller.set_ui_elements(self.width_spin, self.height_spin, self.format_combo)
        
        # Preview Controller - verwaltet Sticker-Vorschau (nach UI-Erstellung!)
        self.preview_controller = PreviewController(
            self.sticker_generator,
            self.sticker_config,
            parent=self
        )
        # UI-Elemente an Preview Controller binden
        if hasattr(self, 'preview_label') and hasattr(self, 'scale_slider'):
            self.preview_controller.set_ui_elements(
                preview_label=self.preview_label,
                scale_slider=self.scale_slider,
                scale_value_label=self.scale_value_label,
                energy_entry=self.energy_entry,
                equipment_entry=self.equipment_entry,
                symbol_combo=self.symbol_combo,
                description_entry=getattr(self, 'description_entry', None)
            )
        
        # Settings Controller - verwaltet Dialog- und Konfigurations-Management
        self.settings_controller = SettingsController(
            self.config_manager,
            parent=self
        )

        # Collection Controller - verwaltet Collection-Operationen (nach UI-Erstellung!)
        self.collection_controller = CollectionController(parent=self)

        # Import Controller - verwaltet PDF-Import und Equipment-Import
        self.import_controller = ImportController(parent=self)

        # Timer f├╝r Updates
        # QR-Modus beim Start deaktivieren ÔÇö wird erst aktiviert wenn Equipment mit QR gew├ñhlt wird
        if hasattr(self, 'sticker_service') and hasattr(self.sticker_service, 'generator'):
            self.sticker_service.generator.cfg.qr_mode_enabled = False
            self.sticker_service.generator.cfg.qr_image_path = None
            self.sticker_service.generator._qr_cache.clear()
        QTimer.singleShot(150, self.preview_controller.update_preview)
        QTimer.singleShot(200, self.equipment_controller.refresh_tree)

    def _build_ui(self):
        """UI aufbauen"""
        central_widget = QWidget()
        central_widget.setStyleSheet("background-color: #f3f3f3;")
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Magic Menu Bar (Custom Tabs) - LINKS als Sidebar
        self.magic_menu = MagicMenuBar()
        main_layout.addWidget(self.magic_menu)

        # Tab Widget (Content) - RECHTS
        self.tab_widget = QTabWidget()
        self.tab_widget.tabBar().hide() # Hide native tabs
        main_layout.addWidget(self.tab_widget, 1)  # Stretch factor 1 f├╝r mehr Platz
        
        # Connect Magic Menu to Tab Widget
        self.magic_menu.tabSelected.connect(self.tab_widget.setCurrentIndex)
        self.tab_widget.currentChanged.connect(self.magic_menu.set_current_index)

        # Alle Tabs erstellen - nutze Builders aus ui.builders
        # build_start_tab(self)  # Start-Tab entfernt
        build_sticker_tab(self)
        build_equipment_tab(self)
        build_export_tab(self)
        
        # PDF Import Tab (Dummy Tab that triggers action)
        # We need a widget for the tab, but we want to trigger the dialog instead.
        # However, QTabWidget needs a widget.
        # Let's create a simple placeholder widget that explains PDF import.
        from ui.builders import build_pdf_import_tab
        build_pdf_import_tab(self)

        # Verwandle die Tab-Reiter in farbige Marker - DEAKTIVIERT f├╝r Magic Menu
        # self._apply_tab_marker_buttons()

        # Status Bar
        self.status_bar = self.statusBar()
        if self.status_bar:
            status_layout = QHBoxLayout()
            status_label = QLabel("LOTO Sticker Generator bereit")
            status_layout.addWidget(status_label)
            status_layout.addStretch()
            
            status_widget = QWidget()
            status_widget.setLayout(status_layout)
            self.status_bar.addWidget(status_widget, 1)

        # Men├╝ erstellen (nach setCentralWidget)
        self._create_menu()
        
        # Theme anwenden
        self._apply_theme_styles()
        
        # Lade gespeicherte Description-Einstellungen (nach vollst├ñndiger Initialisierung)
        QTimer.singleShot(100, self._load_description_settings_on_startup)
    
    # ========== SERVICE EVENT HANDLERS ==========
    
    def _on_equipment_selected_from_tree(self, energy_id: str, equipment: str, symbol: str, qr_path: str = ""):
        """Handler wenn Equipment aus Tree ausgew├ñhlt wird"""
        # Felder ausf├╝llen (wenn vorhanden)
        if hasattr(self, 'energy_entry'):
            self.energy_entry.setText(energy_id)
        if hasattr(self, 'equipment_entry'):
            self.equipment_entry.setText(equipment)
        if hasattr(self, 'symbol_combo') and symbol:
            index = self.symbol_combo.findText(symbol, Qt.MatchFlag.MatchFixedString)
            if index >= 0:
                self.symbol_combo.setCurrentIndex(index)
        
        # QR-Modus je nach Equipment aktivieren/deaktivieren
        if hasattr(self, 'sticker_service') and hasattr(self.sticker_service, 'generator'):
            cfg = self.sticker_service.generator.cfg
            if qr_path and qr_path.strip():
                cfg.qr_mode_enabled = True
                cfg.qr_image_path = qr_path
            else:
                cfg.qr_mode_enabled = False
                cfg.qr_image_path = None
            self.sticker_service.generator._qr_cache.clear()
    
    def _on_sticker_generated(self, img):
        """Handler: Sticker wurde generiert"""
        logger.info("Sticker generiert via StickerService")
    
    def _on_sticker_config_changed(self, config):
        """Handler: Sticker-Konfiguration hat sich ge├ñndert"""
        self.sticker_config = config
        
        # Update Preview Controller
        if hasattr(self, 'preview_controller'):
            self.preview_controller.sticker_config = config
            # Also update generator reference if service has a new one
            if hasattr(self, 'sticker_service') and hasattr(self.sticker_service, 'generator'):
                self.preview_controller.sticker_generator = self.sticker_service.generator
            self.preview_controller.update_preview()
        
        # Aktualisiere Visualisierung
        if hasattr(self, 'dimensions_widget'):
            self.dimensions_widget.set_dimensions(
                self.export_config.sheet_width_mm,
                self.export_config.sheet_height_mm,
                self.export_config.margin_mm,
                self.export_config.gap_mm,
                self.export_config.roll_mode,
                self.sticker_config.width_mm,
                self.sticker_config.height_mm,
                self.export_config.roll_width_mm
            )
            
        logger.info("Sticker-Konfiguration aktualisiert")
    
    def _on_generation_error(self, error_msg):
        """Handler: Fehler bei Sticker-Generierung"""
        show_error(self, "Generierungsfehler", error_msg)
    
    def _on_collection_changed(self):
        """Handler: Collection hat sich ge├ñndert"""
        # Aktualisiere UI-Liste
        self.update_collection_list()
    
    def _on_item_added_to_collection(self, index):
        """Handler: Item wurde zur Collection hinzugef├╝gt"""
        logger.info(f"Item {index} zur Collection hinzugef├╝gt")
    
    def _on_equipment_changed(self):
        """Handler: Equipment-Daten haben sich ge├ñndert"""
        if hasattr(self, 'equipment_controller'):
            self.equipment_controller.refresh_tree()
        self.equipment_service.clear_search_cache()
    
    def _on_equipment_saved(self):
        """Handler: Equipment wurde gespeichert"""
        show_info(self, "Gespeichert", "Equipment-Daten wurden gespeichert.")
    
    # ============================================

    def create_wave_button(self, text=""):
        """Helper: Erstelle einen GlassGlowButton"""
        btn = GlassGlowButton(text, dark_mode=False)
        return btn

    def _import_equipment_from_excel(self):
        """Excel-Import delegiert an EquipmentController."""
        self.equipment_controller.import_equipment_from_excel()

    def _export_equipment_database(self):
        """Exportiert die Equipment-Datenbank ├╝ber EquipmentController."""
        self.equipment_controller.export_equipment_database()

    def _import_equipment_database(self):
        """Importiert die Equipment-Datenbank ├╝ber EquipmentController."""
        self.equipment_controller.import_equipment_database()

    def _create_menu(self):
        """Menue erstellen (delegiert an ui.menu_builder)."""
        build_main_menu(self)

    # === Export-Funktionen (delegieren an Export Controller) ===
    
    def export_pdf(self):
        """PDF Export der Sammlung - delegiert an Export Controller"""
        self.export_controller.export_pdf(self.collection)
    
    def _on_format_preset_changed(self, text: str):
        """Handler: Papierformat Preset gewechselt - delegiert an Export Controller"""
        self.export_controller.on_format_preset_changed(text)
        
        # Aktualisiere Visualisierung
        if hasattr(self, 'dimensions_widget'):
            self.dimensions_widget.set_dimensions(
                self.export_config.sheet_width_mm,
                self.export_config.sheet_height_mm,
                self.export_config.margin_mm,
                self.export_config.gap_mm,
                self.export_config.roll_mode,
                self.sticker_config.width_mm,
                self.sticker_config.height_mm,
                self.export_config.roll_width_mm
            )
    
    def _on_sheet_size_changed(self):
        """Handler: Papierbreite oder -h├Âhe ge├ñndert - delegiert an Export Controller"""
        self.export_controller.on_sheet_size_changed()
        
        # Aktualisiere Visualisierung
        if hasattr(self, 'dimensions_widget'):
            self.dimensions_widget.set_dimensions(
                self.export_config.sheet_width_mm,
                self.export_config.sheet_height_mm,
                self.export_config.margin_mm,
                self.export_config.gap_mm,
                self.export_config.roll_mode,
                self.sticker_config.width_mm,
                self.sticker_config.height_mm,
                self.export_config.roll_width_mm
            )
    
    def _on_export_settings_changed(self):
        """Handler: Export-Einstellungen ge├ñndert - delegiert an Export Controller"""
        # Lese aktuelle Werte aus Spinboxen
        if hasattr(self, 'margin_spin') and self.margin_spin:
            self.export_config.margin_mm = self.margin_spin.value()
        if hasattr(self, 'gap_spin') and self.gap_spin:
            self.export_config.gap_mm = self.gap_spin.value()
        
        self.export_controller.on_export_settings_changed()
        
        # Aktualisiere Visualisierung
        if hasattr(self, 'dimensions_widget'):
            self.dimensions_widget.set_dimensions(
                self.export_config.sheet_width_mm,
                self.export_config.sheet_height_mm,
                self.export_config.margin_mm,
                self.export_config.gap_mm,
                self.export_config.roll_mode,
                self.sticker_config.width_mm,
                self.sticker_config.height_mm,
                self.export_config.roll_width_mm
            )
    
    def _on_roll_width_changed(self):
        """Handler: Rollen-Breite ge├ñndert"""
        roll_spin = getattr(self, 'roll_width_spin', None)
        if roll_spin is not None:
            val = roll_spin.value()
            self.export_config.roll_width_mm = val
            self.export_controller.on_roll_width_changed(val)
            
            # Aktualisiere Visualisierung
            if hasattr(self, 'dimensions_widget'):
                self.dimensions_widget.set_dimensions(
                    self.export_config.sheet_width_mm,
                    self.export_config.sheet_height_mm,
                    self.export_config.margin_mm,
                    self.export_config.gap_mm,
                    self.export_config.roll_mode,
                    self.sticker_config.width_mm,
                    self.sticker_config.height_mm,
                    self.export_config.roll_width_mm
                )
    
    def _reset_rotation_lock(self):
        """Reset die gespeicherte Sticker-Rotation - nicht mehr ben├Âtigt (Auto-Rotation)"""
        pass
    
    def _calculate_roll_height(self):
        """Berechne Rollenh├Âhe - noch nicht implementiert"""
        pass

    # === Preview-Funktionen (delegieren an Preview Controller) ===
    
    def update_sticker_preview(self):
        """Sticker-Vorschau aktualisieren - delegiert an Preview Controller"""
        self.preview_controller.update_preview()
    
    def safe_update_count_preview(self):
        """Sichere Count-Vorschau-Aktualisierung (f├╝r externe Aufrufe)"""
        self.preview_controller.safe_update_count_preview()
    
    def update_count_preview(self):
        """Count-Sticker-Vorschau aktualisieren"""
        self.preview_controller.update_count_preview()
    
    def increase_sticker_scale(self):
        """Sticker-Skalierung erh├Âhen - delegiert an Preview Controller"""
        self.preview_controller.increase_scale()
    
    def decrease_sticker_scale(self):
        """Sticker-Skalierung verringern - delegiert an Preview Controller"""
        self.preview_controller.decrease_scale()
    
    def _safe_update_sticker_scale(self, value):
        """Sichere Aktualisierung der Sticker-Skalierung - delegiert an Preview Controller"""
        self.preview_controller.update_scale(value)
    
    def _safe_update_sticker_scale_from_dial(self, dial_value):
        """Aktualisiere Skalierung vom Drehregler - delegiert an Preview Controller"""
        self.preview_controller.update_scale_from_dial(dial_value)
    
    def _on_preview_text_changed(self, _value):
        """Debounce f├╝r Texteingaben - delegiert an Preview Controller"""
        self.preview_controller.on_text_changed(_value)
    
    def _on_symbol_changed(self, _index):
        """Sofortige Vorschau nach Symbolwechsel - delegiert an Preview Controller"""
        self.preview_controller.on_symbol_changed(_index)
    
    def _apply_sticker_preset(self, preset_type: str):
        """Wendet ein Sticker-Preset an (Form)"""
        controller = getattr(self, 'preview_controller', None)
        if controller is not None:
            controller.apply_sticker_preset(preset_type)
            return

        logger.warning("_apply_sticker_preset aufgerufen bevor preview_controller initialisiert ist")
    
    def _save_current_form_config(self):
        """Speichert die aktuellen Sticker-Einstellungen f├╝r die aktuelle Form"""
        controller = getattr(self, 'preview_controller', None)
        if controller is not None:
            controller.save_current_form_config()
            return

        # Fallback f├╝r fr├╝he __init__-Phase vor Controller-Initialisierung
        if not hasattr(self, 'current_form_type') or not hasattr(self, 'form_configs'):
            return

        from dataclasses import replace
        self.form_configs[self.current_form_type] = replace(self.sticker_config)
    
    def _load_form_config(self, form_type: str):
        """L├ñdt die gespeicherten Einstellungen f├╝r eine Form"""
        controller = getattr(self, 'preview_controller', None)
        if controller is not None:
            controller.load_form_config(form_type)
            return

        # Fallback f├╝r fr├╝he __init__-Phase vor Controller-Initialisierung
        if not hasattr(self, 'form_configs') or form_type not in self.form_configs:
            return

        saved_config = self.form_configs[form_type]
        if saved_config is None:
            return

        self.sticker_config.width_mm = saved_config.width_mm
        self.sticker_config.height_mm = saved_config.height_mm
        self.sticker_config.corner_radius = saved_config.corner_radius
        self.sticker_config.dpi = saved_config.dpi
        self.sticker_config.outline_width = saved_config.outline_width
        self.sticker_config.font_size_mm = saved_config.font_size_mm
        self.sticker_config.line_height_mm = saved_config.line_height_mm
        self.sticker_config.symbol_size_mm = saved_config.symbol_size_mm
        self.sticker_config.symbol_corner_radius = saved_config.symbol_corner_radius
        self.sticker_config.sticker_color = saved_config.sticker_color
        self.sticker_config.font_path = saved_config.font_path
    
    def _load_preset_by_index(self, preset_index: int):
        """L├ñdt ein gespeichertes Sticker-Preset nach Index (0, 1, 2) f├╝r Preset 1, 2, 3"""
        controller = getattr(self, 'preview_controller', None)
        if controller is not None:
            controller.load_preset_by_index(preset_index)
            return

        logger.warning("_load_preset_by_index aufgerufen bevor preview_controller initialisiert ist")
    
    # === Count-Funktionen (delegieren an Count Controller) ===
    
    def update_count_sticker_preview(self):
        """Count Sticker Vorschau aktualisieren - delegiert an Count Controller"""
        self.count_controller.update_count_sticker_preview()
    
    def _show_startup_welcome_sticker(self):
        """Zeige Welcome-Sticker beim Start"""
        try:
            # Zeige einfach die Standard-Preview
            self.update_sticker_preview()
        except Exception as e:
            logger.error(f"Welcome Sticker Fehler: {e}")
    
    # === Settings-Funktionen (delegieren an Settings Controller) ===
    
    def open_sticker_settings(self):
        """Sticker-Einstellungen ├Âffnen - delegiert an Settings Controller"""
        self.settings_controller.open_sticker_settings()
    
    def open_count_settings(self):
        """Count-Einstellungen ├Âffnen - delegiert an Settings Controller"""
        self.settings_controller.open_count_settings()
    
    def save_and_update_sticker(self):
        """Konfiguration speichern und Sticker-Generator aktualisieren - delegiert an Settings Controller"""
        self.settings_controller.save_and_update_sticker()
    
    def save_and_update_count(self):
        """Konfiguration speichern und Count-Generator aktualisieren - delegiert an Settings Controller"""
        self.settings_controller.save_and_update_count()

    # === LOTO Modus Handling ===

    def _on_loto_mode_changed(self, mode_or_bool):
        """Synchronisiere Toggle-Zustand mit Export-Konfiguration und Legacy-State.
        
        Args:
            mode_or_bool: Entweder ein String ('single', 'multi', 'none') oder ein Boolean (f├╝r R├╝ckw├ñrtskompatibilit├ñt)
        """
        # R├╝ckw├ñrtskompatibilit├ñt: Boolean zu String konvertieren
        if isinstance(mode_or_bool, bool):
            mode = 'multi' if mode_or_bool else 'single'
        else:
            mode = mode_or_bool  # 'single', 'multi', oder 'none'
        
        previous_mode = getattr(self, 'current_loto_mode', None)
        self.current_loto_mode = mode

        if getattr(self, 'count_mode', None):
            try:
                self.count_mode.set(mode)
            except Exception:
                self.count_mode = _CountModeProxy(mode)
        else:
            self.count_mode = _CountModeProxy(mode)

        if getattr(self, 'export_config', None):
            self.export_config.export_mode = mode
            # IMMER speichern wenn Modus ge├ñndert wird (nicht nur wenn anders als previous)
            try:
                self.config_manager.save_export(self.export_config)
                logger.info(f"LOTO Modus gespeichert: {mode}")
            except Exception as exc:
                logger.warning(f"Export-Config konnte nicht gespeichert werden (LOTO Modus): {exc}")
    
    # === Export-Helper-Funktionen ===
    
    def _update_roll_mode_visibility(self):
        """Aktualisiere Sichtbarkeit von Roll-Mode-Elementen - delegiert an Export Controller"""
        if hasattr(self, 'export_controller'):
            self.export_controller._update_roll_mode_visibility()

    def compute_auto_sheet_height(self, count_mode, regular_items, count_single_items, sheet_w_mm, header_h_mm=0.0):
        """Berechnet automatische Seitenh├Âhe ├╝ber den ExportController."""
        return self.export_controller.compute_auto_sheet_height(
            count_mode,
            regular_items,
            count_single_items,
            sheet_w_mm,
            header_h_mm=header_h_mm,
        )

    # === Description Settings Management ===
    def load_description_settings(self):
        """Lade gespeicherte Description-Einstellungen"""
        try:
            if self.description_settings_path.exists():
                with open(self.description_settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    return settings.get('description', ''), settings.get('is_locked', False)
        except Exception as e:
            logger.warning(f"Description-Einstellungen konnten nicht geladen werden: {e}")
        return '', False
    
    def save_description_settings(self, description: str, is_locked: bool):
        """Speichere Description-Einstellungen persistent"""
        try:
            self.description_settings_path.parent.mkdir(parents=True, exist_ok=True)
            settings = {
                'description': description,
                'is_locked': is_locked
            }
            with open(self.description_settings_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Description-Einstellungen speichern fehlgeschlagen: {e}")
    
    def _load_description_settings_on_startup(self):
        """Lade Description-Einstellungen nach Startup (nach voller Initialisierung)"""
        try:
            saved_description, is_locked = self.load_description_settings()
            # Speichere die Einstellung intern (nicht ins UI-Feld)
            self._saved_description = saved_description
            self._saved_description_locked = is_locked
            
            # Zeige Lock-Button visuell wenn gespeichert
            if saved_description and is_locked and hasattr(self, 'description_lock_btn'):
                self.description_lock_btn.setIcon(qta.icon('ph.lock', color='#856404'))
                self.description_lock_btn.setIconSize(QSize(20, 20))
                self.description_lock_btn.setStyleSheet("""
                    QPushButton {
                        border: 1px solid #ffeeba;
                        border-radius: 18px;
                        background-color: #fff3cd;
                    }
                    QPushButton:hover { background-color: #ffe8a1; }
                """)
                self.description_is_locked = True
                
                # Aber NICHT ins Textfeld eingeben - Feld bleibt leer!
                # Das verhindert, dass der Start-Sticker die Description erh├ñlt
                if hasattr(self, 'description_entry'):
                    self.description_entry.setText("")  # Feld bleibt leer
                    self.description_entry.setReadOnly(True)
                    # Stelle auch das Input-Styling auf readonly
                    try:
                        custom_colors = getattr(self.theme_config, 'custom_colors', {}) if hasattr(self, 'theme_config') else {}
                        input_bg = custom_colors.get('input_bg', '#f8f9fa')
                        input_fg = custom_colors.get('input_fg', '#2c3e50')
                        border_color = custom_colors.get('border', '#dce1e6')
                        focus_color = custom_colors.get('accent', '#3498db')
                        base_style = f"""
                            QLineEdit {{
                                border: 1px solid {border_color};
                                border-radius: 6px;
                                padding: 6px 10px;
                                background-color: {input_bg};
                                color: {input_fg};
                                font-size: 13px;
                            }}
                            QLineEdit:focus {{
                                border: 1px solid {focus_color};
                                background-color: #ffffff;
                            }}
                            QLineEdit:disabled {{
                                background-color: #f0f2f5;
                                color: #95a5a6;
                            }}
                        """
                        self.description_entry.setStyleSheet(base_style + "QLineEdit { background-color: #f9f9f9; color: #7f8c8d; }")
                    except Exception:
                        pass  # Fallback zu Standard-Styling
        except Exception as e:
            logger.warning(f"Fehler beim Laden der Description-Einstellungen: {e}")

    # === Sticker-Funktionen (delegiert an CollectionController) ===
    def _is_count_multi(self, item):
        return CollectionController._is_count_multi(item)

    def _is_count_single(self, item):
        return CollectionController._is_count_single(item)

    def add_to_collection(self, auto_add_count: bool = True):
        self.collection_controller.add_to_collection(auto_add_count=auto_add_count)

    def _remove_duplicate_count_stickers(self):
        self.collection_controller._remove_duplicate_count_stickers()

    def _add_to_collection_with_thumbnail(self, img, symbol_type_name, energy_id, equipment_name, description, full_info):
        self.collection_controller._add_to_collection_with_thumbnail(img, symbol_type_name, energy_id, equipment_name, description, full_info)

    def update_collection_list(self, skip_sort: bool = False):
        self.collection_controller.update_collection_list(skip_sort=skip_sort)

    def _on_collection_item_selected_trigger(self):
        self.collection_controller._on_collection_item_selected_trigger()

    def _on_collection_item_selected_debounced(self):
        self.collection_controller._on_collection_item_selected_debounced()

    def _on_collection_scroll_value_changed(self, _value):
        self.collection_controller._on_collection_scroll_value_changed(_value)

    def _on_collection_scroll_finished(self):
        self.collection_controller._on_collection_scroll_finished()

    def _clear_collection_preview_cache(self, drop_base: bool = False):
        self.collection_controller._clear_collection_preview_cache(drop_base=drop_base)

    def _on_collection_item_selected(self):
        self.collection_controller._on_collection_item_selected()

    def _edit_count_sticker_copies(self, row: int) -> None:
        self.collection_controller._edit_count_sticker_copies(row)

    def _show_collection_context_menu(self, pos):
        self.collection_controller._show_collection_context_menu(pos)

    def _add_collection_item_to_equipment_manager(self, row: int) -> None:
        self.collection_controller._add_collection_item_to_equipment_manager(row)

    def _duplicate_collection_item(self, row):
        self.collection_controller._duplicate_collection_item(row)

    def _remove_collection_item(self, row):
        self.collection_controller._remove_collection_item(row)

    def _remove_multiple_collection_items(self, rows: list):
        self.collection_controller._remove_multiple_collection_items(rows)

    def regenerate_all_stickers(self):
        self.collection_controller.regenerate_all_stickers()

    def clear_collection(self):
        self.collection_controller.clear_collection()

    def register_collection_source(self, source: str):
        self.collection_controller.register_collection_source(source)

    # === Import-Funktionen (delegieren an Import Controller) ===

    @staticmethod
    def _extract_group_key(energy_id, equipment='', description=''):
        return ImportController._extract_group_key(energy_id, equipment, description)

    def _detect_missing_stickers(self, extracted_data, count_sticker_groups):
        return self.import_controller._detect_missing_stickers(extracted_data, count_sticker_groups)

    def _detect_missing_from_group_gaps(self, extracted_data, count_sticker_groups=None):
        return self.import_controller._detect_missing_from_group_gaps(extracted_data, count_sticker_groups)

    def _show_missing_stickers_dialog(self, missing_entries):
        return self.import_controller._show_missing_stickers_dialog(missing_entries)

    def _create_stickers_from_entries(self, extracted_data, entries):
        return self.import_controller._create_stickers_from_entries(extracted_data, entries)

    def _show_loto_grouping_dialog(self, extracted_data, count_sticker_groups=None):
        return self.import_controller._show_loto_grouping_dialog(extracted_data, count_sticker_groups)

    def import_stickers_from_pdf(self):
        self.import_controller.import_stickers_from_pdf()

    def _serialize_current_sticker_config(self) -> dict:
        return self.import_controller._serialize_current_sticker_config()

    def _sync_settings_to_equipment_manager(self):
        self.import_controller._sync_settings_to_equipment_manager()

    def import_collection_to_equipment_manager(self):
        self.import_controller.import_collection_to_equipment_manager()

    def sort_collection_by_energy_id(self):
        """Delegiert an CollectionController"""
        self.collection_controller.sort_collection_by_energy_id()

    def _regenerate_multi_count_sticker(self):
        """Delegiert an CollectionController"""
        self.collection_controller._regenerate_multi_count_sticker()

    def move_item_up(self):
        """Gew├ñhltes Element nach oben ÔÇö delegiert an CollectionController"""
        self.collection_controller.move_item_up()

    def move_item_down(self):
        """Gew├ñhltes Element nach unten ÔÇö delegiert an CollectionController"""
        self.collection_controller.move_item_down()

    def delete_selected_items(self):
        """Gew├ñhlte Elemente aus der Sammlung l├Âschen ÔÇö delegiert an CollectionController"""
        self.collection_controller.delete_selected_items()

    def _apply_theme_styles(self):
        """Wendet Theme-Styles auf das Hauptfenster an."""
        apply_main_window_theme(self)


    
    def _select_equipment(self):
        """Equipment-Auswahl-Dialog ├Âffnen (delegiert an EquipmentController)."""
        self.equipment_controller.select_equipment_for_form()


if __name__ == '__main__':
    import sys
    import time
    import random
    import math
    app = QApplication(sys.argv)
    
    # Setze globale Light Palette - deaktiviere Windows Dark Mode f├╝r diese App
    from PyQt6.QtGui import QPalette, QColor
    light_palette = QPalette()
    light_palette.setColor(QPalette.ColorRole.Window, QColor(243, 243, 243))
    light_palette.setColor(QPalette.ColorRole.WindowText, QColor(31, 42, 55))
    light_palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
    light_palette.setColor(QPalette.ColorRole.Text, QColor(31, 42, 55))
    light_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(240, 240, 240))
    light_palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))
    light_palette.setColor(QPalette.ColorRole.ButtonText, QColor(31, 42, 55))
    light_palette.setColor(QPalette.ColorRole.Highlight, QColor(179, 215, 255))
    light_palette.setColor(QPalette.ColorRole.HighlightedText, QColor(31, 42, 55))
    app.setPalette(light_palette)
    
    # Setze globalen Light Stylesheet (nur die wichtigsten Teile)
    app.setStyle("Fusion")  # Verwende Fusion Style f├╝r konsistente mit Palette
    
    # Animierter Splash Screen mit Partikel-Effekt
    splash_pixmap = None
    svg_renderer = None
    logo_size = QSize(400, 400)
    
    # Zuerst SVG versuchen
    svg_path = Path(__file__).parent.parent / "LOGO Tag!T.svg"
    pdf_path = Path(__file__).parent.parent / "LOGO Tag!T.pdf"
    
    if svg_path.exists():
        try:
            svg_renderer = QSvgRenderer(str(svg_path))
            if svg_renderer.isValid():
                svg_size = svg_renderer.defaultSize()
                if svg_size.isValid():
                    logo_size = svg_size * 2
        except Exception as e:
            logger.warning(f"Konnte SVG nicht laden: {e}")
            svg_renderer = None
    
    # Fallback auf PDF
    if not svg_renderer and pdf_path.exists():
        try:
            pdf_doc = fitz.open(str(pdf_path))
            page = pdf_doc[0]
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat, alpha=True)
            img_data = pix.tobytes("png")
            splash_pixmap = QPixmap()
            splash_pixmap.loadFromData(img_data)
            logo_size = splash_pixmap.size()
            pdf_doc.close()
        except Exception as e:
            logger.warning(f"Konnte PDF nicht laden: {e}")
    
    splash = None
    
    if (not DISABLE_SPLASH_ANIMATION) and (svg_renderer or (splash_pixmap and not splash_pixmap.isNull())):
        from PyQt6.QtCore import QRectF
        
        class ParticleSplash(QWidget):
            def __init__(self, svg_renderer=None, pixmap=None, size=QSize(400, 400)):
                super().__init__()
                self.setWindowFlags(
                    Qt.WindowType.WindowStaysOnTopHint | 
                    Qt.WindowType.FramelessWindowHint |
                    Qt.WindowType.Tool
                )
                self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
                self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
                
                self.svg_renderer = svg_renderer
                self.original_pixmap = pixmap
                self.logo_size = size
                self.progress = 0.0
                self._opacity = 1.0
                self._logo_opacity = 0.0
                
                # Canvas Gr├Â├ƒe
                self.canvas_size = max(size.width(), size.height()) + 200
                self.setFixedSize(self.canvas_size, self.canvas_size)
                
                # Zentrieren
                screen = app.primaryScreen().geometry()
                self.move(
                    (screen.width() - self.width()) // 2,
                    (screen.height() - self.height()) // 2
                )
                
                # Logo als Bild rendern
                self.logo_image = self._render_logo_to_image()
                
                # Partikel extrahieren (weniger f├╝r Performance)
                self._extract_particles()
            
            def _render_logo_to_image(self):
                img = QImage(self.logo_size, QImage.Format.Format_ARGB32_Premultiplied)
                img.fill(QColor(0, 0, 0, 0))  # Transparent
                
                painter = QPainter(img)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                
                if self.svg_renderer:
                    self.svg_renderer.render(painter)
                elif self.original_pixmap:
                    painter.drawPixmap(0, 0, self.original_pixmap)
                
                painter.end()
                return img
            
            def _extract_particles(self):
                self.particles = []
                
                # Weniger Partikel f├╝r bessere Performance
                step = 8
                
                center_x = self.canvas_size // 2
                center_y = self.canvas_size // 2
                offset_x = center_x - self.logo_size.width() // 2
                offset_y = center_y - self.logo_size.height() // 2
                
                for y in range(0, self.logo_image.height(), step):
                    for x in range(0, self.logo_image.width(), step):
                        color = QColor(self.logo_image.pixel(x, y))
                        # Nur sichtbare Pixel, keine schwarzen
                        if color.alpha() > 80 and (color.red() > 30 or color.green() > 30 or color.blue() > 30):
                            target_x = offset_x + x
                            target_y = offset_y + y
                            
                            # Startposition au├ƒerhalb
                            angle = random.uniform(0, 2 * math.pi)
                            dist = random.uniform(250, 450)
                            start_x = target_x + math.cos(angle) * dist
                            start_y = target_y + math.sin(angle) * dist
                            
                            self.particles.append({
                                'tx': target_x, 'ty': target_y,
                                'sx': start_x, 'sy': start_y,
                                'color': color,
                                'delay': random.uniform(0, 0.4),
                                'size': random.uniform(0.5, 1.5)
                            })
                
                random.shuffle(self.particles)
            
            def paintEvent(self, event):
                painter = QPainter(self)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                
                # Partikel zeichnen
                if self.progress < 1.0 or self._logo_opacity < 1.0:
                    painter.setPen(Qt.PenStyle.NoPen)
                    
                    for p in self.particles:
                        # Progress mit Delay
                        adj_prog = max(0, min(1, (self.progress - p['delay']) / (1 - p['delay'])))
                        
                        # Easing
                        eased = 1 - pow(1 - adj_prog, 3) if adj_prog > 0 else 0
                        
                        # Position
                        x = p['sx'] + (p['tx'] - p['sx']) * eased
                        y = p['sy'] + (p['ty'] - p['sy']) * eased
                        
                        # Farbe
                        c = QColor(p['color'])
                        c.setAlpha(int(c.alpha() * self._opacity * (1 - self._logo_opacity * 0.8)))
                        painter.setBrush(c)
                        painter.drawEllipse(QPointF(x, y), p['size'], p['size'])
                
                # Logo zeichnen
                if self._logo_opacity > 0:
                    painter.setOpacity(self._logo_opacity * self._opacity)
                    
                    cx = self.canvas_size // 2
                    cy = self.canvas_size // 2
                    
                    if self.svg_renderer:
                        svg_size = self.svg_renderer.defaultSize()
                        target_rect = QRectF(
                            cx - svg_size.width() // 2,
                            cy - svg_size.height() // 2,
                            svg_size.width(),
                            svg_size.height()
                        )
                        self.svg_renderer.render(painter, target_rect)
                    elif self.original_pixmap:
                        painter.drawPixmap(
                            cx - self.original_pixmap.width() // 2,
                            cy - self.original_pixmap.height() // 2,
                            self.original_pixmap
                        )
                
                painter.end()
        
        splash = ParticleSplash(svg_renderer, splash_pixmap, logo_size)
        splash.show()
        app.processEvents()
        
        # === ANIMATION (optimiert) ===
        
        # Phase 1: Partikel fliegen zusammen
        duration = 4.5
        start_time = time.time()
        
        while True:
            elapsed = time.time() - start_time
            if elapsed >= duration:
                break
            splash.progress = elapsed / duration
            splash.update()
            app.processEvents()
            time.sleep(0.025)
        
        splash.progress = 1.0
        
        # Phase 2: Logo einblenden
        duration = 1.2
        start_time = time.time()
        
        while True:
            elapsed = time.time() - start_time
            if elapsed >= duration:
                break
            splash._logo_opacity = elapsed / duration
            splash.update()
            app.processEvents()
            time.sleep(0.025)
        
        splash._logo_opacity = 1.0
        splash.update()
        
        # Phase 3: Kurz anzeigen
        time.sleep(1.5)
        
        # Phase 4: Fade-Out
        duration = 1.0
        start_time = time.time()
        
        while True:
            elapsed = time.time() - start_time
            if elapsed >= duration:
                break
            splash._opacity = 1.0 - (elapsed / duration)
            splash.update()
            app.processEvents()
            time.sleep(0.025)
    
    # App starten
    window = StickerApp()
    
    if splash:
        splash.close()
    
    window.show()
    sys.exit(app.exec())
