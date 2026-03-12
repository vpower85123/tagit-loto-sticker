#!/usr/bin/env python3
"""
Vollständige PyQt6 Version der Sticker Generator App
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
from ui.theme import Theme, get_theme_colors, create_input_stylesheet, create_dialog_stylesheet, detect_system_dark_mode, get_unified_button_style
from ui.dialogs import show_info, show_warning, show_error, show_question
from ui.builders import build_sticker_tab, build_equipment_tab, build_export_tab
from ui.components import ModernComboBox
from ui.spinboxes import StyledSpinBox, StyledDoubleSpinBox
from ui.magic_menu import MagicMenuBar
from ui.form_helpers import (
    style_text_input, style_combo_box, style_form_button,
    create_form_row, create_row_container, set_uniform_field_width,
    SPINBOX_INPUT_WIDTH, TEXT_INPUT_HEIGHT
)
from dialogs.equipment_dialog import EquipmentSelectionDialog
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
    QFontDatabase, QActionGroup, QAction
)
from PyQt6.QtCore import (
    Qt, QTimer, QSize, QRect, QPoint, QPointF, QThread, pyqtSignal, QEvent,
    QUrl, QDir, QFile, QIODevice, QStandardPaths, QPropertyAnimation, QEasingCurve,
    QSequentialAnimationGroup, QParallelAnimationGroup
)
from PyQt6.QtWidgets import QSplashScreen, QGraphicsOpacityEffect
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtGui import QTransform

# PIL für Bildverarbeitung
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

# ReportLab für PDF-Export (optional)
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
from generators.sticker_generator import StickerGenerator
from core.models import SymbolType, StickerConfig as ModelStickerConfig, CountConfig, ExportConfig
from core.config_manager import ConfigManager
from managers.equipment_manager import EquipmentManager
from generators.count_manager import CountStickerGenerator
from generators.pdf_exporter_new import export_pdf_new
from core.constants import SETTINGS_DIALOG_WIDTH

# Services
from services import StickerService, CollectionService, EquipmentService

# Controllers
from controllers import EquipmentController, ExportController, PreviewController, SettingsController


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
            "Möchten Sie sich wirklich abmelden?",
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
                    # Bei Erfolg: Menü neu aufbauen (für Lizenz-Info Update) und Fenster zeigen
                    self._create_menu()
                    self.show()
                else:
                    # Bei Abbruch: App beenden
                    self.close()
            else:
                warn_msg = self._create_styled_msgbox("Fehler", "Abmelden fehlgeschlagen.", QMessageBox.Icon.Warning)
                warn_msg.exec()

    def _new_project(self):
        """Neues Projekt erstellen (Collection leeren und Felder zurücksetzen)"""
        msg = self._create_styled_msgbox(
            "Neues Projekt",
            "Möchten Sie ein neues Projekt starten? Die aktuelle Sammlung wird geleert.",
            QMessageBox.Icon.Question,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        reply = msg.exec()
        
        if reply == QMessageBox.StandardButton.Yes:
            # Collection leeren
            self.clear_collection()
            
            # Eingabefelder zurücksetzen
            if hasattr(self, 'energy_entry'):
                self.energy_entry.clear()
            if hasattr(self, 'equipment_entry'):
                self.equipment_entry.clear()
            if hasattr(self, 'description_entry'):
                self.description_entry.clear()
            
            # Preview zurücksetzen
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
        """Über-Dialog anzeigen"""
        about_text = """
<h2>LOTO Sticker Generator</h2>
<p><b>Version:</b> 2.0</p>
<p><b>Beschreibung:</b> Generator für LOTO (Lock-Out Tag-Out) Sticker</p>
<p><b>Features:</b></p>
<ul>
    <li>Erstellen von einzelnen und mehreren LOTO Stickern</li>
    <li>Equipment-Verwaltung mit hierarchischer Struktur</li>
    <li>PDF-Export mit verschiedenen Formaten</li>
    <li>Count-Sticker für Single/Multi LOTO</li>
    <li>Konfigurierbare Einstellungen für Sticker und Count</li>
</ul>
<p><b>Entwicklung:</b> TAG!T Team</p>
        """
        
        QMessageBox.about(self, "Über LOTO Sticker Generator", about_text)


    def __init__(self):
        super().__init__()
        
        # Lizenzprüfung
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
        
        # App-Icon setzen (HQ PNG für beste Qualität in Taskbar)
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
        self.count_sticker_copies_spinbox = None  # Für editierbare pro-Sticker Kopien-Anzahl
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
            "rectangle": None,  # Wird beim ersten Laden gefüllt
            "square": None,
            "circle": None
        }
        # Speichere die Initial-Konfiguration für Rechteck
        self._save_current_form_config()

        initial_mode = getattr(self.export_config, 'export_mode', 'multi') or 'multi'
        self.count_mode = _CountModeProxy(initial_mode)
        self.current_loto_mode = initial_mode

        initial_mode = getattr(self.export_config, 'export_mode', 'multi') or 'multi'
        self.count_mode = _CountModeProxy(initial_mode)
        self.current_loto_mode = initial_mode
        
        # Button-Einstellungen laden
        ButtonSettings.load_from_file()
        
        # Pfad für persistente Description-Einstellungen
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
        
        # Legacy: Direkter Zugriff auf Manager (für Rückwärtskompatibilität)
        self.sticker_generator = self.sticker_service.generator
        self.equipment_manager = self.equipment_service.get_manager()
        # ======================================================

        # Count Generator (noch nicht in Service ausgelagert)
        self.count_generator = CountStickerGenerator(self.count_config)

        # Legacy: Collection als Liste (für Rückwärtskompatibilität)
        # TODO: Alle Zugriffe auf self.collection durch self.collection_service ersetzen
        self.collection = []
        self._manual_sort_mode = None
        self.collection_export_sources = set()
        
        # Theme initialisieren
        # Theme immer auf Light setzen
        self.theme = Theme.LIGHT

        # Preview-Scale für Count (an Sticker-Preview-Scale gekoppelt)
        # Stelle sicher, dass der geladene Wert das Maximum 2.0 nicht überschreitet
        loaded_scale = float(getattr(self.sticker_config, 'preview_scale', 2.0) or 2.0)
        if loaded_scale > 2.0:
            self.sticker_config.preview_scale = 2.0
            loaded_scale = 2.0
        self.count_preview_scale = loaded_scale

        # UI aufbauen
        self._build_ui()
        
        # Timer für Collection Selection Debouncing initialisieren
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

        # Timer für Updates
        # QR-Modus beim Start deaktivieren — wird erst aktiviert wenn Equipment mit QR gewählt wird
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
        main_layout.addWidget(self.tab_widget, 1)  # Stretch factor 1 für mehr Platz
        
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

        # Verwandle die Tab-Reiter in farbige Marker - DEAKTIVIERT für Magic Menu
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

        # Menü erstellen (nach setCentralWidget)
        self._create_menu()
        
        # Theme anwenden
        self._apply_theme_styles()
        
        # Lade gespeicherte Description-Einstellungen (nach vollständiger Initialisierung)
        QTimer.singleShot(100, self._load_description_settings_on_startup)
    
    # ========== SERVICE EVENT HANDLERS ==========
    
    def _on_equipment_selected_from_tree(self, energy_id: str, equipment: str, symbol: str, qr_path: str = ""):
        """Handler wenn Equipment aus Tree ausgewählt wird"""
        # Felder ausfüllen (wenn vorhanden)
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
        """Handler: Sticker-Konfiguration hat sich geändert"""
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
        """Handler: Collection hat sich geändert"""
        # Aktualisiere UI-Liste
        self.update_collection_list()
    
    def _on_item_added_to_collection(self, index):
        """Handler: Item wurde zur Collection hinzugefügt"""
        logger.info(f"Item {index} zur Collection hinzugefügt")
    
    def _on_equipment_changed(self):
        """Handler: Equipment-Daten haben sich geändert"""
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
        """Excel-Import für Equipment - Feature deaktiviert"""
        msg = self._create_styled_msgbox("Info", "Excel-Import ist derzeit nicht verfügbar.")
        msg.exec()

    def _export_equipment_database(self):
        """Exportiert die Equipment-Datenbank als JSON-Datei."""
        try:
            from PyQt6.QtWidgets import QFileDialog
            import json
            
            # Speicherdialog öffnen
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Equipment-Datenbank exportieren",
                "equipment_backup.json",
                "JSON Dateien (*.json);;Alle Dateien (*.*)"
            )
            
            if not file_path:
                return  # Abgebrochen
            
            # Daten exportieren
            data = self.equipment_manager.equipment_data
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            msg = self._create_styled_msgbox("Erfolg", f"Equipment-Datenbank erfolgreich exportiert!\n\n{file_path}")
            msg.exec()
            
        except Exception as e:
            msg = self._create_styled_msgbox("Fehler", f"Export fehlgeschlagen:\n{str(e)}")
            msg.exec()

    def _import_equipment_database(self):
        """Importiert Equipment-Datenbank aus JSON-Datei."""
        try:
            from PyQt6.QtWidgets import QFileDialog, QDialog, QVBoxLayout, QHBoxLayout, QLabel
            from ui.glass_button import GlassGlowButton
            import json
            
            # Öffnungsdialog
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Equipment-Datenbank importieren",
                "",
                "JSON Dateien (*.json);;Alle Dateien (*.*)"
            )
            
            if not file_path:
                return  # Abgebrochen
            
            # Gestylter Bestätigungsdialog
            dialog = QDialog(self)
            dialog.setWindowTitle("Import bestätigen")
            dialog.setModal(True)
            dialog.setFixedWidth(500)
            dialog.setStyleSheet("""
                QDialog {
                    background-color: #f4f6f9;
                }
                QLabel {
                    color: #2c3e50;
                }
            """)
            
            layout = QVBoxLayout(dialog)
            layout.setSpacing(15)
            layout.setContentsMargins(25, 20, 25, 20)
            
            # Frage
            question_label = QLabel("Möchten Sie die aktuelle Datenbank ersetzen\noder die Daten zusammenführen?")
            question_label.setStyleSheet("font-size: 13px; font-weight: bold;")
            layout.addWidget(question_label)
            
            info_label = QLabel("• Ersetzen = Alte Daten werden überschrieben\n• Zusammenführen = Neue Daten werden hinzugefügt")
            info_label.setStyleSheet("font-size: 11px; color: #666;")
            layout.addWidget(info_label)
            
            layout.addSpacing(10)
            
            # Buttons
            button_layout = QHBoxLayout()
            button_layout.setSpacing(10)
            
            replace_btn = GlassGlowButton("Ändern")
            replace_btn.setIcon(qta.icon('ph.arrows-clockwise', color='#374151'))
            replace_btn.setFixedHeight(38)
            replace_btn.setMinimumWidth(140)
            
            merge_btn = GlassGlowButton("Zusammenführen")
            merge_btn.setFixedHeight(38)
            merge_btn.setMinimumWidth(180)
            
            cancel_btn = GlassGlowButton("Abbrechen")
            cancel_btn.setFixedHeight(38)
            cancel_btn.setMinimumWidth(120)
            
            # Result speichern
            dialog.result_action = None
            
            def on_replace():
                dialog.result_action = "replace"
                dialog.accept()
            
            def on_merge():
                dialog.result_action = "merge"
                dialog.accept()
            
            replace_btn.clicked.connect(on_replace)
            merge_btn.clicked.connect(on_merge)
            cancel_btn.clicked.connect(dialog.reject)
            
            button_layout.addWidget(replace_btn)
            button_layout.addWidget(merge_btn)
            button_layout.addStretch()
            button_layout.addWidget(cancel_btn)
            layout.addLayout(button_layout)
            
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            
            action = dialog.result_action
            
            # Datei laden
            with open(file_path, 'r', encoding='utf-8') as f:
                imported_data = json.load(f)
            
            if not isinstance(imported_data, dict):
                msg = self._create_styled_msgbox("Fehler", "Ungültiges Dateiformat!")
                msg.exec()
                return
            
            if action == "replace":
                # Ersetzen
                self.equipment_manager.equipment_data = imported_data
            else:
                # Zusammenführen
                for location, location_data in imported_data.items():
                    if location not in self.equipment_manager.equipment_data:
                        self.equipment_manager.equipment_data[location] = location_data
                    else:
                        # Location existiert - Systeme zusammenführen
                        existing_systems = self.equipment_manager.equipment_data[location].get('systems', [])
                        imported_systems = location_data.get('systems', [])
                        
                        for imp_sys in imported_systems:
                            # Prüfen ob System bereits existiert
                            sys_exists = False
                            for ex_sys in existing_systems:
                                if ex_sys.get('name') == imp_sys.get('name'):
                                    # Equipment zusammenführen
                                    ex_equip = ex_sys.get('equipment', [])
                                    imp_equip = imp_sys.get('equipment', [])
                                    
                                    for eq in imp_equip:
                                        # Prüfen ob Equipment bereits existiert
                                        eq_exists = any(e.get('name') == eq.get('name') for e in ex_equip)
                                        if not eq_exists:
                                            ex_equip.append(eq)
                                    
                                    ex_sys['equipment'] = ex_equip
                                    sys_exists = True
                                    break
                            
                            if not sys_exists:
                                existing_systems.append(imp_sys)
                        
                        self.equipment_manager.equipment_data[location]['systems'] = existing_systems
            
            # Speichern und Tree aktualisieren
            self.equipment_manager.save()
            self.equipment_controller.refresh_tree()
            
            count_locations = len(imported_data)
            msg = self._create_styled_msgbox(
                "Erfolg", 
                f"Import erfolgreich!\n\n{count_locations} Standort(e) importiert."
            )
            msg.exec()
            
        except json.JSONDecodeError as e:
            msg = self._create_styled_msgbox("Fehler", f"Ungültige JSON-Datei:\n{str(e)}")
            msg.exec()
        except Exception as e:
            msg = self._create_styled_msgbox("Fehler", f"Import fehlgeschlagen:\n{str(e)}")
            msg.exec()

    def _create_menu(self):
        """Menü erstellen"""
        try:
            menubar = self.menuBar()
            if menubar is None:
                return

            # Menü leeren, falls es bereits existiert (verhindert Dopplungen)
            menubar.clear()

            # Datei-Menü
            file_menu = menubar.addMenu("&Datei")
            if file_menu:
                new_action = QAction("&Neu", self)
                new_action.triggered.connect(self._new_project)
                new_action.setShortcut("Ctrl+N")
                file_menu.addAction(new_action)

                file_menu.addSeparator()
                
                logout_action = QAction("&Abmelden", self)
                logout_action.triggered.connect(self.logout)
                file_menu.addAction(logout_action)

                file_menu.addSeparator()

                exit_action = QAction("&Beenden", self)
                exit_action.triggered.connect(self.close)
                exit_action.setShortcut("Ctrl+Q")
                file_menu.addAction(exit_action)

            # Bearbeiten-Menü
            edit_menu = menubar.addMenu("&Bearbeiten")
            if edit_menu:
                settings_action = QAction("&Sticker-Einstellungen", self)
                settings_action.triggered.connect(self.open_sticker_settings)
                settings_action.setShortcut("Ctrl+S")
                edit_menu.addAction(settings_action)

                count_settings_action = QAction("&Count-Einstellungen", self)
                count_settings_action.triggered.connect(self.open_count_settings)
                edit_menu.addAction(count_settings_action)
                
            # --- LIZENZ INFO IM MENÜ (RECHTS) ---
            if hasattr(self, 'license_manager'):
                is_valid, msg, expiry = self.license_manager.check_license()
                if is_valid and expiry:
                    # Container für Lizenz-Info
                    license_widget = QWidget()
                    license_widget.setFixedHeight(36)
                    license_widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
                    l_layout = QHBoxLayout(license_widget)
                    l_layout.setContentsMargins(0, 0, 12, 0)
                    l_layout.setSpacing(6)
                    
                    # Icon
                    icon = QLabel("🔐")
                    icon.setStyleSheet("font-size: 14px;")
                    l_layout.addWidget(icon)
                    
                    # Text Info
                    days_left = (expiry - datetime.datetime.now()).days
                    info_text = f"Lizenz aktiv: {days_left} Tage"
                    
                    # Wenn weniger als 30 Tage, rot markieren
                    color = "#27ae60" if days_left > 30 else "#e74c3c"
                    
                    lbl = QLabel(info_text)
                    lbl.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 12px;")
                    l_layout.addWidget(lbl)
                    
                    # Logout Button
                    logout_btn = GlassGlowButton("Abmelden")
                    logout_btn.setFixedHeight(34)
                    logout_btn.clicked.connect(self.logout)
                    l_layout.addWidget(logout_btn)

                    license_widget.adjustSize()
                    
                    license_widget.setToolTip(f"Gültig bis: {expiry.strftime('%d.%m.%Y')}")
                    menubar.setCornerWidget(license_widget, Qt.Corner.TopRightCorner)

        except Exception as e:
            logger.error(f"Menü-Erstellung fehlgeschlagen: {e}")

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
        """Handler: Papierbreite oder -höhe geändert - delegiert an Export Controller"""
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
        """Handler: Export-Einstellungen geändert - delegiert an Export Controller"""
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
        """Handler: Rollen-Breite geändert"""
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
        """Reset die gespeicherte Sticker-Rotation - nicht mehr benötigt (Auto-Rotation)"""
        pass
    
    def _calculate_roll_height(self):
        """Berechne Rollenhöhe - noch nicht implementiert"""
        pass

    # === Preview-Funktionen (delegieren an Preview Controller) ===
    
    def update_sticker_preview(self):
        """Sticker-Vorschau aktualisieren - delegiert an Preview Controller"""
        self.preview_controller.update_preview()
    
    def safe_update_count_preview(self):
        """Sichere Count-Vorschau-Aktualisierung (für externe Aufrufe)"""
        try:
            self.update_count_preview()
        except Exception as e:
            logger.error(f"Fehler bei safe_update_count_preview: {e}")
    
    def update_count_preview(self):
        """Count-Sticker-Vorschau aktualisieren"""
        from PyQt6.QtGui import QPixmap
        from PyQt6.QtCore import Qt
        from PIL.ImageQt import ImageQt
        
        try:
            # Zähle nur reguläre Items (keine COUNT-Sticker)
            regular_items = [it for it in self.collection 
                           if not (self._is_count_single(it) or self._is_count_multi(it))]
            actual_count = len(regular_items)
            
            if actual_count == 0:
                actual_count = 1  # Mindestens 1 für Vorschau
                detail = "Beispiel Equipment"
            else:
                # Details aus Collection extrahieren - in Reihenfolge!
                detail_parts = []
                for item in regular_items:
                    e_id = item[2] if len(item) > 2 else ""
                    equip = item[3] if len(item) > 3 else ""
                    # Kombiniere Energy-ID und Equipment-Name
                    if e_id and equip:
                        detail_parts.append(f"{e_id} {equip}")
                    elif e_id:
                        detail_parts.append(e_id)
                    elif equip:
                        detail_parts.append(equip)
                
                import re as _re_sort
                detail_parts.sort(key=lambda s: [int(t) if t.isdigit() else t.lower() for t in _re_sort.split(r'(\d+)', s)])
                # Als komma-separierte Liste für Count-Sticker
                detail = ", ".join(detail_parts)
            
            # Count-Sticker generieren mit aktuellem Generator
            preview_img = self.count_generator.generate(detail=detail, count=actual_count)
            
            # Bild zu QPixmap konvertieren
            if preview_img.mode != 'RGBA':
                preview_img = preview_img.convert('RGBA')
            qimage = ImageQt(preview_img)
            pixmap = QPixmap.fromImage(qimage)
            
            # Vorschau im Hauptfenster aktualisieren
            if hasattr(self, 'preview_label'):
                scaled_pixmap = pixmap.scaled(
                    800, 600,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.preview_label.setPixmap(scaled_pixmap)
        except Exception as e:
            logger.error(f"Count-Vorschau-Fehler: {e}")
            import traceback
            traceback.print_exc()
    
    def increase_sticker_scale(self):
        """Sticker-Skalierung erhöhen - delegiert an Preview Controller"""
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
        """Debounce für Texteingaben - delegiert an Preview Controller"""
        self.preview_controller.on_text_changed(_value)
    
    def _on_symbol_changed(self, _index):
        """Sofortige Vorschau nach Symbolwechsel - delegiert an Preview Controller"""
        self.preview_controller.on_symbol_changed(_index)
    
    def _apply_sticker_preset(self, preset_type: str):
        """Wendet ein Sticker-Preset an (Form)"""
        try:
            # Speichere aktuelle Form-Einstellungen bevor wir wechseln
            if hasattr(self, 'current_form_type') and self.current_form_type != preset_type:
                self._save_current_form_config()
            
            # Wenn wir bereits gespeicherte Einstellungen für diese Form haben, lade sie
            if hasattr(self, 'form_configs') and self.form_configs.get(preset_type) is not None:
                self._load_form_config(preset_type)
                self.current_form_type = preset_type
            else:
                # Ansonsten verwende Standard-Preset-Werte
                px_per_mm = self.sticker_config.dpi / 25.4
                
                if preset_type == "rectangle":
                    # Rechteck: Standard LOTO-Format 85mm x 25mm mit stark abgerundeten Ecken
                    self.sticker_config.width_mm = 85.0
                    self.sticker_config.height_mm = 25.0
                    # 12mm Eckenradius für sehr runden Look (fast halbe Höhe)
                    self.sticker_config.corner_radius = int(12.0 * px_per_mm)
                    
                elif preset_type == "square":
                    # Quadrat: 85mm x 85mm für bessere Lesbarkeit und Proportionen
                    self.sticker_config.width_mm = 85.0
                    self.sticker_config.height_mm = 85.0
                    # Stark abgerundete Ecken (20mm) für sehr weichen Look
                    self.sticker_config.corner_radius = int(20.0 * px_per_mm)
                    
                elif preset_type == "circle":
                    # Kreis: 70mm Durchmesser für ausgewogene Größe
                    size_mm = 70.0
                    self.sticker_config.width_mm = size_mm
                    self.sticker_config.height_mm = size_mm
                    # Perfekter Kreis: Radius = halbe Breite in Pixel
                    size_px = int(size_mm * px_per_mm)
                    self.sticker_config.corner_radius = size_px // 2
                    
                elif preset_type == "rounded":
                    # Abgerundetes Rechteck: 85mm x 25mm mit deutlichen Eckenradius
                    self.sticker_config.width_mm = 85.0
                    self.sticker_config.height_mm = 25.0
                    # 5mm Eckenradius für abgerundetes Rechteck
                    self.sticker_config.corner_radius = int(5.0 * px_per_mm)
                
                # Speichere diese neue Konfiguration für diese Form
                self.current_form_type = preset_type
                self._save_current_form_config()
            
            # Speichere die Änderungen
            self.config_manager.save(self.sticker_config, self.count_config, self.theme_config)
            
            # Update Generator und Preview
            self.sticker_generator = StickerGenerator(self.sticker_config)
            self.update_sticker_preview()
            
            if self.status_bar:
                self.status_bar.showMessage(f"Preset '{preset_type}' angewendet", 2000)
                
        except Exception as e:
            logger.error(f"Fehler beim Anwenden des Presets: {e}")
            msg = self._create_styled_msgbox("Fehler", f"Preset konnte nicht angewendet werden: {e}", QMessageBox.Icon.Warning)
            msg.exec()
    
    def _save_current_form_config(self):
        """Speichert die aktuellen Sticker-Einstellungen für die aktuelle Form"""
        if not hasattr(self, 'current_form_type') or not hasattr(self, 'form_configs'):
            return
        
        # Erstelle eine Kopie der relevanten Konfigurationswerte
        from dataclasses import replace
        self.form_configs[self.current_form_type] = replace(self.sticker_config)
    
    def _load_form_config(self, form_type: str):
        """Lädt die gespeicherten Einstellungen für eine Form"""
        if not hasattr(self, 'form_configs') or form_type not in self.form_configs:
            return
        
        saved_config = self.form_configs[form_type]
        if saved_config is None:
            return
        
        # Übertrage die gespeicherten Werte
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
        """Lädt ein gespeichertes Sticker-Preset nach Index (0, 1, 2) für Preset 1, 2, 3"""
        try:
            import json
            from core.paths import get_config_path
            
            config_path = get_config_path("config.json")
            if not config_path.exists():
                logger.warning("config.json nicht gefunden")
                return
            
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            presets = data.get("sticker_presets", []) or []
            if not isinstance(presets, list) or preset_index >= len(presets):
                logger.warning(f"Preset {preset_index + 1} nicht gefunden")
                return
            
            preset = presets[preset_index]
            if not preset:
                logger.warning(f"Preset {preset_index + 1} ist leer")
                return
            
            # Preset-Werte anwenden
            px_per_mm = self.sticker_config.dpi / 25.4
            
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
            
            # Speichere und aktualisiere
            self.config_manager.save(self.sticker_config, self.count_config, self.theme_config)
            self.sticker_generator = StickerGenerator(self.sticker_config)
            self.update_sticker_preview()
            
            if self.status_bar:
                self.status_bar.showMessage(f"Preset {preset_index + 1} geladen", 2000)
            
            logger.info(f"Preset {preset_index + 1} erfolgreich geladen")
            
        except Exception as e:
            logger.error(f"Fehler beim Laden des Presets: {e}")
    
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
        """Sticker-Einstellungen öffnen - delegiert an Settings Controller"""
        self.settings_controller.open_sticker_settings()
    
    def open_count_settings(self):
        """Count-Einstellungen öffnen - delegiert an Settings Controller"""
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
            mode_or_bool: Entweder ein String ('single', 'multi', 'none') oder ein Boolean (für Rückwärtskompatibilität)
        """
        # Rückwärtskompatibilität: Boolean zu String konvertieren
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
            # IMMER speichern wenn Modus geändert wird (nicht nur wenn anders als previous)
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
        """
        Berechne automatische Seitenhöhe (mm), so dass ALLE Sticker auf EINE Seite passen.
        Layout: (optional Header) -> Raster reguläre Sticker -> Raster Count-Sticker (single mode).
        header_h_mm: Echte Header-Höhe in mm (optional, wird berechnet wenn nicht angegeben)
        """
        margin = self.export_config.margin_mm
        gap = self.export_config.gap_mm

        # Basis-Dimensionen
        st_w = self.sticker_config.width_mm
        st_h = self.sticker_config.height_mm

        # Header (nur Multi)
        header_block_h = 0.0
        if count_mode == 'multi' and self.export_config.include_count_header and regular_items:
            if header_h_mm > 0:
                # Nutze die echte Header-Höhe wenn übergeben
                header_block_h = header_h_mm + gap
            else:
                # Fallback: Approximation
                header_block_h = self.count_config.height_mm + gap

        # Rotation beurteilen (nur für reguläre Sticker)
        rotate_mode = getattr(self.export_config, 'sticker_rotate_mode', 'none')
        
        def cols_for(w_s, h_s):
            usable_w = sheet_w_mm - 2 * margin
            return max(1, int((usable_w + gap) // (w_s + gap)))

        if rotate_mode == 'always':
            use_rot = True
        elif rotate_mode == 'auto':
            cols_norm = cols_for(st_w, st_h)
            cols_rot = cols_for(st_h, st_w)
            use_rot = cols_rot > cols_norm
        else:
            use_rot = False
        
        if use_rot:
            st_w, st_h = st_h, st_w

        # Reguläre Sticker Raster (nur im Multi-Modus!)
        n_reg = len(regular_items)
        cols_reg = cols_for(st_w, st_h)
        rows_reg = math.ceil(n_reg / cols_reg) if n_reg else 0
        reg_block_h = 0.0
        
        # Im Single-Modus werden reguläre Sticker mit Count-Stickern als Paare behandelt
        if count_mode != 'single':
            if rows_reg:
                reg_block_h = rows_reg * st_h + (rows_reg - 1) * gap

        # Count-Singles Block (nur single Mode)
        count_block_h = 0.0
        if count_mode == 'single':
            # Single-Modus: identische Logik wie beim PDF-Export verwenden
            ct_w_orig = self.count_config.width_mm
            ct_h_orig = self.count_config.height_mm
            count_copies = max(1, int(getattr(self.count_config, 'count_print_copies', 1)))
            st_w_orig = st_w  # Nach Rotation aus oben
            st_h_orig = st_h
            usable_w = sheet_w_mm - 2 * margin
            total_pairs = len(regular_items)

            def evaluate(lo_rot: bool, ct_rot: bool):
                loto_w = st_h_orig if lo_rot else st_w_orig
                loto_h = st_w_orig if lo_rot else st_h_orig
                count_w = ct_h_orig if ct_rot else ct_w_orig
                count_h = ct_w_orig if ct_rot else ct_h_orig
                pair_width_local = loto_w + gap + count_w
                if usable_w <= 0:
                    pairs_per_row_local = 1
                else:
                    pairs_per_row_local = max(1, int((usable_w + gap) // (pair_width_local + gap)))
                rows_local = math.ceil(total_pairs / pairs_per_row_local) if total_pairs else 0
                stacked_count_h = count_copies * (count_h + gap)
                pair_height_local = max(loto_h, stacked_count_h)
                total_height_local = rows_local * pair_height_local + max(rows_local - 1, 0) * gap
                pairs_in_row = pairs_per_row_local if total_pairs >= pairs_per_row_local else (total_pairs or pairs_per_row_local)
                width_used = pairs_in_row * pair_width_local + max(pairs_in_row - 1, 0) * gap
                width_penalty = max(usable_w - width_used, 0.0)
                rotation_penalty = 0 if lo_rot == ct_rot else 1
                return (
                    -pairs_per_row_local,
                    width_penalty,
                    rotation_penalty,
                    total_height_local,
                    total_height_local,
                )

            option_metrics = [
                evaluate(False, False),
                evaluate(True, True),
                evaluate(True, False),
                evaluate(False, True),
            ]

            # count_block_h entspricht total_height der besten Option (Index 4)
            best_option = min(option_metrics, key=lambda item: item[:4])
            count_block_h = best_option[4]
            
            # Im Single-Modus sind die regulären Sticker bereits in count_block_h enthalten
            reg_block_h = 0.0
        elif count_mode == 'single' and count_single_items:
            ct_w = self.count_config.width_mm
            ct_h = self.count_config.height_mm
            usable_w = sheet_w_mm - 2 * margin
            ct_cols = max(1, int((usable_w + gap) // (ct_w + gap)))
            rows_ct = math.ceil(len(count_single_items) / ct_cols)
            count_block_h = rows_ct * ct_h + (rows_ct - 1) * gap
            if rows_reg:
                count_block_h += gap  # Abstand zwischen regulär und Count

        total_h = margin + header_block_h + reg_block_h + count_block_h + margin
        return math.ceil(total_h + 0.0001)

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
                # Das verhindert, dass der Start-Sticker die Description erhält
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

    # === Sticker-Funktionen ===
    def _is_count_multi(self, item):
        """Prüft ob ein Item ein Count-Multi Sticker ist"""
        if len(item) < 6:
            return False
        marker = item[5]
        if isinstance(marker, dict):
            return marker.get("type") == "count_multi"
        return marker == "count_multi"
    
    def _is_count_single(self, item):
        """Prüft ob ein Item ein Count-Single Sticker ist"""
        if len(item) < 6:
            return False
        marker = item[5]
        if isinstance(marker, dict):
            return marker.get("type") == "count_single"
        return marker == "count_single"
    
    def add_to_collection(self, auto_add_count: bool = True):
        """Sticker zur Sammlung hinzufügen - nutzt Services
        
        Args:
            auto_add_count: Wenn False, werden keine Count-Sticker automatisch hinzugefügt
        """
        try:
            energy_id = self.energy_entry.text().strip()
            equipment = self.equipment_entry.text().strip()
            
            # Prüfe ob es der Start-Sticker ist (WELCOME TO + TAG!T)
            is_welcome_sticker = (energy_id == "WELCOME TO" and equipment == "TAG!T")
            
            # Verwende Description nur wenn es nicht der Start-Sticker ist
            if is_welcome_sticker:
                # Start-Sticker: keine Description
                description = ""
            else:
                # Normale Sticker: verwende Description aus UI oder gespeicherte Description
                description = self.description_entry.text().strip() if hasattr(self, 'description_entry') else ""
                
                # Falls Description leer ist, aber eine gespeicherte & gesperrte Description existiert, verwende diese
                if not description and hasattr(self, '_saved_description_locked') and self._saved_description_locked:
                    description = getattr(self, '_saved_description', "")

            logger.info(f"add_to_collection: energy_id='{energy_id}', equipment='{equipment}', description='{description}'")

            # Validierung via StickerService
            is_valid, error_msg = self.sticker_service.validate_input(energy_id, equipment)
            if not is_valid:
                msg = self._create_styled_msgbox("Fehler", error_msg, QMessageBox.Icon.Warning)
                msg.exec()
                return

            symbol_name = self.symbol_combo.currentText().upper()
            
            # Sticker generieren via StickerService
            img = self.sticker_service.generate_sticker(
                energy_id=energy_id,
                equipment=equipment,
                symbol_name=symbol_name,
                description=description
            )
            
            if img is None:
                # Fehler wurde bereits via Signal gehandelt
                return

            # Thumbnail erstellen
            img_thumbnail = img.copy()
            img_thumbnail.thumbnail((400, 300), Image.Resampling.LANCZOS)
            
            # Prüfe ob Sticker bereits in Collection existiert (Duplikat-Prüfung) - VOR dem Hinzufügen
            sticker_exists = any(
                not (self._is_count_single(item) or self._is_count_multi(item)) and
                len(item) > 3 and item[2] == energy_id and item[3] == equipment
                for item in self.collection
            )
            
            if sticker_exists:
                logger.info(f"Sticker {energy_id} {equipment} bereits in Collection - übersprungen")
                return  # Sticker existiert bereits, nicht nochmal hinzufügen
            
            # Item zur Collection hinzufügen via CollectionService
            self.collection_service.add_item(
                energy_id=energy_id,
                equipment=equipment,
                symbol_type=symbol_name,
                description=description,
                image=img,
                thumbnail=img_thumbnail
            )
            
            # Legacy: Auch in alte self.collection schreiben (für Rückwärtskompatibilität)
            # QR-Pfad aus aktuellem Sticker-Generator Config holen
            qr_path = ""
            if hasattr(self.sticker_service.generator, 'cfg'):
                cfg = self.sticker_service.generator.cfg
                if getattr(cfg, 'qr_mode_enabled', False) and getattr(cfg, 'qr_image_path', None):
                    qr_path = cfg.qr_image_path
                    logger.info(f"QR-Code-Pfad aus Generator übernommen: {qr_path}")
            
            current_group = getattr(self, '_current_collection_group', '') or ''
            current_location = getattr(self, '_current_collection_location', '') or ''
            current_system = getattr(self, '_current_collection_system', '') or ''
            full_info = {
                "text": f"{energy_id} {equipment} {description}".strip(),
                "qr_path": qr_path,
                "group": current_group,
                "location": current_location,
                "system": current_system
            }
            self.collection.append([img_thumbnail, symbol_name, energy_id, equipment, description, full_info, img])
            
            # Determine LOTO mode from radio buttons
            is_single_mode = getattr(self, 'single_loto_radio', None) and self.single_loto_radio.isChecked()
            is_multi_mode = getattr(self, 'multi_loto_radio', None) and self.multi_loto_radio.isChecked()
            is_no_count_mode = getattr(self, 'no_count_radio', None) and self.no_count_radio.isChecked()
            
            logger.info(f"LOTO Mode: single={is_single_mode}, multi={is_multi_mode}, no_count={is_no_count_mode}, auto_add_count={auto_add_count}")

            # Count-Sticker nur hinzufügen wenn auto_add_count=True UND nicht "Kein Count" Modus
            if auto_add_count and not is_no_count_mode:
                # Bei Single LOTO Modus auch Count Sticker hinzufügen
                if is_single_mode:
                    try:
                        # Count Sticker für einzelnes LOTO generieren - mit Description
                        count_detail = f"{energy_id} {equipment} {description}".strip()
                        count_id = f"C_{energy_id}"
                        
                        # Prüfe ob bereits ein identischer Count-Sticker existiert (mehrere Methoden)
                        # Methode 1: Über _is_count_single
                        existing_count_ids_m1 = [item[2] for item in self.collection if self._is_count_single(item) and len(item) > 2]
                        # Methode 2: Über symbol_type == "COUNT_SINGLE"
                        existing_count_ids_m2 = [item[2] for item in self.collection if len(item) > 2 and item[1] == "COUNT_SINGLE"]
                        # Kombiniere beide
                        all_existing = set(existing_count_ids_m1) | set(existing_count_ids_m2)
                        
                        logger.debug(f"COUNT CHECK: count_id={count_id}, existing_m1={existing_count_ids_m1}, existing_m2={existing_count_ids_m2}")
                        
                        count_exists = count_id in all_existing
                        
                        if not count_exists:
                            count_img = self.count_generator.generate(count_detail, 1)
                            count_copies_default = max(1, int(getattr(getattr(self, 'count_config', None), 'count_print_copies', 1)))
                            self.collection.append([count_img, "COUNT_SINGLE", count_id, "", count_detail, {"type": "count_single", "copies": count_copies_default}, count_img])
                            logger.debug(f"COUNT ADDED: {count_id}, collection size: {len(self.collection)}")
                        else:
                            logger.debug(f"COUNT SKIPPED: {count_id} already exists")
                    except Exception as e:
                        logger.warning(f"Count Sticker konnte nicht generiert werden: {e}")
                        import traceback
                        logger.warning(traceback.format_exc())
                
                # Bei Multi LOTO Modus den Count Sticker am Ende aktualisieren
                elif is_multi_mode:
                    self._regenerate_multi_count_sticker()

            # DUPLIKAT-BEREINIGUNG: Entferne doppelte Count-Sticker
            self._remove_duplicate_count_stickers()
            
            self.update_collection_list()

            # QMessageBox.information(self, "Erfolg", "Sticker zur Sammlung hinzugefügt!")

        except Exception as e:
            msg = self._create_styled_msgbox("Fehler", f"Fehler beim Hinzufügen:\n{e}", QMessageBox.Icon.Critical)
            msg.exec()
    
    def _remove_duplicate_count_stickers(self):
        """Entfernt doppelte Count-Sticker aus der Collection"""
        seen_count_ids = set()
        items_to_remove = []
        
        for i, item in enumerate(self.collection):
            if len(item) > 2 and (self._is_count_single(item) or item[1] == "COUNT_SINGLE"):
                count_id = item[2]
                if count_id in seen_count_ids:
                    items_to_remove.append(i)
                    logger.debug(f"REMOVING DUPLICATE COUNT: {count_id} at index {i}")
                else:
                    seen_count_ids.add(count_id)
        
        # Rückwärts entfernen um Indizes nicht zu verschieben
        for i in reversed(items_to_remove):
            self.collection.pop(i)
        
        if items_to_remove:
            logger.debug(f"REMOVED {len(items_to_remove)} DUPLICATE COUNT STICKERS")

    def _add_to_collection_with_thumbnail(self, img, symbol_type_name, energy_id, equipment_name, description, full_info):
        """Helper: Füge Sticker zur Collection mit Thumbnail hinzu"""
        # Thumbnail speichern für schnelles Rendering
        img_thumbnail = img.copy()
        img_thumbnail.thumbnail((400, 300), Image.Resampling.LANCZOS)
        # Format: [img_thumbnail, symbol_type, energy_id, equipment, description, full_info, img_fullsize]
        self.collection.append([img_thumbnail, symbol_type_name, energy_id, equipment_name, description, full_info, img])

    def update_collection_list(self, skip_sort: bool = False):
        """Sammlungsliste aktualisieren
        
        Args:
            skip_sort: Wenn True, wird die automatische Sortierung übersprungen
                      (z.B. nach manueller Sortierung durch den User)
        """
        # Speichere aktuelle Selection
        current_row = self.collection_list.currentRow()
        
        # Lösche und baue neu (schneller als inkrementell bei Änderungen)
        self.collection_list.clear()

        manual_mode = getattr(self, "_manual_sort_mode", None)
        effective_skip_sort = skip_sort or manual_mode == "energy_id"
        count_copies = max(1, int(getattr(getattr(self, 'count_config', None), 'count_print_copies', 1)))

        # Wenn skip_sort, direkt zur Anzeige springen (keine Umsortierung)
        if effective_skip_sort:
            multi_count = 0
            skipped_items = 0
            for idx, item in enumerate(self.collection, start=1):
                # Prüfe item Länge
                if len(item) < 4:
                    logger.warning(f"Item {idx} übersprungen (len={len(item)})")
                    skipped_items += 1
                    continue
                    
                symbol_type = item[1] if len(item) > 1 else "?"
                energy_id = item[2] if len(item) > 2 else f"IDX{idx}"
                equipment = item[3] if len(item) > 3 else ""
                description = item[4] if len(item) > 4 else ""
                
                is_count_single = self._is_count_single(item)
                is_count_multi = self._is_count_multi(item)
                
                if is_count_single:
                    # Extract copies from marker or use default
                    marker = item[5] if len(item) > 5 else {}
                    copies = 1
                    if isinstance(marker, dict):
                        copies = marker.get("copies", 1)
                    text = f"{idx:02d} | C | {energy_id} | 1 LOTOPOINT | x{copies}"
                elif is_count_multi:
                    # Extract copies from marker or use default
                    marker = item[5] if len(item) > 5 else {}
                    copies = 1
                    if isinstance(marker, dict):
                        copies = marker.get("copies", 1)
                        count_group = marker.get("group", "")
                    else:
                        count_group = ""
                    # Zähle reguläre Sticker der gleichen Gruppe
                    regular_count = sum(
                        1 for it in self.collection
                        if not (self._is_count_single(it) or self._is_count_multi(it))
                        and (isinstance(it[5], dict) and it[5].get("group", "") == count_group if len(it) > 5 else count_group == "")
                    )
                    group_label = count_group if count_group else "TOTAL"
                    text = f"{idx:02d} | C | {group_label} | {regular_count} LOTOPOINTS | x{copies}"
                else:
                    multi_count += 1
                    base = getattr(symbol_type, 'name', str(symbol_type))
                    symbol_short = (base[:1].upper() or "?")
                    if description:
                        text = f"{idx:02d} | {symbol_short} | {energy_id} | {equipment} | {description} | #{multi_count}"
                    else:
                        text = f"{idx:02d} | {symbol_short} | {energy_id} | {equipment} | #{multi_count}"
                
                self.collection_list.addItem(text)
            
            if skipped_items > 0:
                logger.debug(f"TOTAL: {skipped_items} Items übersprungen, {self.collection_list.count()} Items angezeigt")
            
            # Stelle Selection wieder her wenn möglich
            if current_row >= 0 and current_row < self.collection_list.count():
                self.collection_list.setCurrentRow(current_row)
            return

        # Logische Sortierung: nach gemeinsamen Equipment-Präfixen gruppieren
        import re
        from collections import Counter
        
        def _natural_key(text: str):
            """Natürliche Sortierung für Strings mit Zahlen (UV-1, UV-2, UV-10)"""
            parts = re.split(r"(\d+)", text.upper())
            key = []
            for part in parts:
                if part.isdigit():
                    key.append(int(part))
                else:
                    key.append(part)
            return tuple(key)

        def _normalize_equipment(equipment: str) -> str:
            if not equipment:
                return ""
            # Entferne " - " Pattern (kommt in manchen Namen vor)
            normalized = re.sub(r"\s*-\s*", "-", equipment)
            normalized = re.sub(r"\s+", "", normalized)
            normalized = re.sub(r"\.+", ".", normalized)
            return normalized.strip(".")

        def _split_segments(equipment: str) -> list[str]:
            normalized = _normalize_equipment(equipment)
            return [seg for seg in normalized.split(".") if seg]

        def _strip_suffix(segment: str) -> str:
            """Entfernt numerische Suffixe wie _0001, -0021"""
            return re.sub(r"[_-]?\d+$", "", segment)

        def _find_base_segment(segments: list[str]) -> tuple[int | None, str]:
            """Findet das Base-Segment (z.B. UV-1, SC-2) in der Segment-Liste"""
            for idx, segment in enumerate(segments):
                if re.search(r"[A-Z]+-\d+", segment, re.IGNORECASE):
                    return idx, segment
            return None, ""

        def _extract_group_key(equipment: str, segment_counts: Counter) -> str:
            """Extrahiert Gruppierungs-Schlüssel aus Equipment-Namen.
            
            Beispiele:
            'ELEC.DP.UV-1' -> 'UV-1'
            'ELEC.DP.UV-1.ALFEN' -> 'UV-1.ALFEN' (wenn ALFEN mehrfach)
            'ELEC.DP.UV-1.ALFEN.DBY8_0001' -> 'UV-1.ALFEN.DBY8' (wenn beide mehrfach)
            'ELEC.DP.UV-1.DBY8_0021' -> 'UV-1.DBY8' (wenn DBY8 mehrfach)
            """
            if not equipment:
                return ""
            # Suche nach SC_XX.XX oder SC_XX Pattern (mit optionalem trailing Punkt)
            match = re.search(r"SC[_-]?(\d+)\.?(\d*)", equipment, re.IGNORECASE)
            if match:
                sc_num = match.group(1)
                sub_num = match.group(2) if match.group(2) else "00"
                return f"SC_{sc_num}.{sub_num}"
            
            # Dynamische Gruppierung basierend auf wiederholten Segmenten
            segments = _split_segments(equipment)
            base_index, base_segment = _find_base_segment(segments)
            
            if base_index is not None:
                # Sammle alle Segmente nach dem Base die mehrfach vorkommen
                group_parts = [base_segment]
                for i in range(base_index + 1, len(segments)):
                    candidate = _strip_suffix(segments[i])
                    if candidate and segment_counts.get(candidate, 0) > 1:
                        group_parts.append(candidate)
                return ".".join(group_parts)

            # Fallback: Extrahiere alles vor dem letzten numerischen Suffix
            prefix = re.sub(r"[._-]\d+\.?$", "", equipment)
            while prefix != equipment:
                equipment = prefix
                prefix = re.sub(r"[._-]\d+\.?$", "", equipment)
            return prefix

        def _energy_id_sort_key(energy_id: str):
            """Sortiert Energy-IDs natürlich: E1, E2, ... E10, E11"""
            if not energy_id:
                return (float('inf'), "")
            return _natural_key(energy_id)

        def _equipment_sort_key(item):
            equipment = item[3] if len(item) > 3 else ""
            energy_id = item[2] if len(item) > 2 else ""
            # Primär: Gruppe aus full_info (= System/loto_group aus Equipment-Manager)
            full_info = item[5] if len(item) > 5 and isinstance(item[5], dict) else {}
            group = full_info.get("group", "")
            return (_natural_key(group), _energy_id_sort_key(energy_id), _natural_key(equipment))

        regular_items = [it for it in self.collection if not (self._is_count_single(it) or self._is_count_multi(it))]
        count_singles = [it for it in self.collection if self._is_count_single(it)]
        count_multis = [it for it in self.collection if self._is_count_multi(it)]
        
        # Nur sortieren wenn nicht übersprungen werden soll
        if not skip_sort:
            regular_items.sort(key=_equipment_sort_key)
            # Count-Singles in gleicher Reihenfolge wie zugehörige LOTO-Sticker sortieren
            count_singles.sort(key=lambda it: _energy_id_sort_key(
                it[2][2:] if len(it) > 2 and it[2].startswith("C_") else (it[2] if len(it) > 2 else "")
            ))
            # Count-Multis nach Gruppenname sortieren
            count_multis.sort(key=lambda it: _natural_key(
                it[5].get("group", "") if len(it) > 5 and isinstance(it[5], dict) else ""
            ))
            self.collection = regular_items + count_singles + count_multis
        
        multi_count = 0
        skipped_items = 0
        
        for idx, item in enumerate(self.collection, start=1):
            if len(item) >= 4:
                symbol_type = item[1] if len(item) > 1 else "?"
                energy_id = item[2] if len(item) > 2 else f"IDX{idx}"
                equipment = item[3] if len(item) > 3 else ""
                description = item[4] if len(item) > 4 else ""
                
                # Check if it's a count single sticker
                # Robust check: item[1] is type name, item[5] is marker (can be string or dict)
                is_count_single = self._is_count_single(item) or (str(symbol_type) == "COUNT_SINGLE")
                is_count_multi = self._is_count_multi(item) or (str(symbol_type) == "COUNT_MULTI")
                
                if is_count_single:
                    # Extract copies from marker or use default
                    marker = item[5] if len(item) > 5 else {}
                    copies = 1
                    if isinstance(marker, dict):
                        copies = marker.get("copies", 1)
                    text = f"{idx:02d} | C | {energy_id} | 1 LOTOPOINT | x{copies}"
                elif is_count_multi:
                    # Zähle reguläre Sticker der gleichen Gruppe
                    count_group = ""
                    marker = item[5] if len(item) > 5 else {}
                    copies = 1
                    if isinstance(marker, dict):
                        count_group = marker.get("group", "")
                        copies = marker.get("copies", 1)
                    regular_count = sum(
                        1 for it in self.collection
                        if not (self._is_count_single(it) or self._is_count_multi(it))
                        and (isinstance(it[5], dict) and it[5].get("group", "") == count_group if len(it) > 5 else count_group == "")
                    )
                    group_label = count_group if count_group else "TOTAL"
                    text = f"{idx:02d} | C | {group_label} | {regular_count} LOTOPOINTS | x{copies}"
                else:
                    # Regular sticker - increments multi count
                    multi_count += 1
                    
                    # Regular sticker - extract symbol short name robustly
                    base = getattr(symbol_type, 'name', str(symbol_type))
                    symbol_short = (base[:1].upper() or "?")
                    # Description hinzufügen wenn vorhanden
                    if description:
                        text = f"{idx:02d} | {symbol_short} | {energy_id} | {equipment} | {description} | #{multi_count}"
                    else:
                        text = f"{idx:02d} | {symbol_short} | {energy_id} | {equipment} | #{multi_count}"
                    
                self.collection_list.addItem(text)
            else:
                logger.warning(f"Item {idx} übersprungen (sortiert, len={len(item)})")
                skipped_items += 1
        
        if skipped_items > 0:
            logger.debug(f"TOTAL (sortiert): {skipped_items} Items übersprungen, {self.collection_list.count()} Items angezeigt")
        
        # Stelle Selection wieder her wenn möglich
        if current_row >= 0 and current_row < self.collection_list.count():
            self.collection_list.setCurrentRow(current_row)

    def _on_collection_item_selected_trigger(self):
        """Trigger für Collection Item Selection - startet Debounce Timer"""
        current_row = self.collection_list.currentRow()
        self._pending_collection_preview_row = current_row

        if getattr(self, "_is_collection_scrolling", False):
            return

        delay = getattr(self, "_collection_preview_delay_ms", 150)
        self.collection_selection_timer.stop()
        self.collection_selection_timer.start(delay)

    def _on_collection_item_selected_debounced(self):
        """Debounced Collection Item Selection"""
        self._on_collection_item_selected()

    def _on_collection_scroll_value_changed(self, _value):
        """Unterdrücke Vorschauupdates während des Scrollens."""
        try:
            self._is_collection_scrolling = True
            if hasattr(self, "collection_selection_timer"):
                self.collection_selection_timer.stop()
            if hasattr(self, "collection_scroll_cooldown_timer"):
                self.collection_scroll_cooldown_timer.start(250)
        except Exception as exc:
            logger.debug(f"Scroll handler error: {exc}")

    def _on_collection_scroll_finished(self):
        """Reaktiviere Vorschauupdates nachdem das Scrollen gestoppt hat."""
        self._is_collection_scrolling = False
        row = self._pending_collection_preview_row
        self._pending_collection_preview_row = None

        list_widget = getattr(self, "collection_list", None)
        if list_widget is None:
            return

        count = list_widget.count()

        if row is None or row < 0 or row >= count:
            row = list_widget.currentRow()

        if row is not None and row >= 0 and row < count:
            if row != list_widget.currentRow():
                list_widget.setCurrentRow(row)
                return

            delay = getattr(self, "_collection_preview_delay_ms", 150)
            if hasattr(self, "collection_selection_timer"):
                self.collection_selection_timer.start(delay)

    def _clear_collection_preview_cache(self, drop_base: bool = False):
        """Leere gecachte Pixmaps für Sammlungselemente."""
        cache_index = 7
        for item in getattr(self, "collection", []):
            if len(item) <= cache_index:
                continue
            cache_entry = item[cache_index]

            if isinstance(cache_entry, dict):
                if drop_base:
                    cache_entry["base"] = None
                cache_entry["scaled"] = {}
            elif cache_entry is not None:
                if drop_base:
                    item[cache_index] = None
                else:
                    item[cache_index] = {"base": cache_entry, "scaled": {}}

    def _on_collection_item_selected(self):
        """Handler: Wenn ein Sticker in der Collection angewählt wird, zeige ihn in der Vorschau und lade seine Daten"""
        import time
        start_time = time.time()
        
        try:
            current_row = self.collection_list.currentRow()
            if current_row < 0 or current_row >= len(self.collection):
                logger.debug(f"Collection selection: invalid row {current_row}")
                return
            
            logger.debug(f"Collection item selected: row {current_row}")
            
            # Hole den Sticker aus der Collection
            item = self.collection[current_row]
            if not item or len(item) < 1:
                logger.debug("Collection item is empty")
                return

            # Shimmer-Maske immer zuerst zurücksetzen (sonst bleibt der letzte Effekt sichtbar)
            if hasattr(self, 'preview_label') and hasattr(self.preview_label, 'set_mask_pixmap'):
                self.preview_label.set_mask_pixmap(None)
            
            # Collection-Struktur (neuer Format): [img_thumbnail, symbol_type, energy_id, equipment_name, description, full_info, img_fullsize]
            # Collection-Struktur (alter Format): [img_fullsize, symbol_type, energy_id, equipment, description, full_info]
            
            # Entscheide welches Format - wenn Index 6 exists und ist PIL Image, dann neuer Format
            use_thumbnail = len(item) > 6 and item[6] is not None
            img = item[6] if use_thumbnail else item[0]  # Vollbild für Daten, aber zum Anzeigen Thumbnail
            
            if not img:
                return
            
            # Lade die Daten in die Eingabefelder (nur bei normalen Stickern, nicht bei COUNT)
            if len(item) >= 5:
                symbol_type = item[1] if len(item) > 1 else ""
                energy_id = item[2] if len(item) > 2 else ""
                equipment_name = item[3] if len(item) > 3 else ""
                description = item[4] if len(item) > 4 else ""
                
                # Nur laden, wenn es kein COUNT-Sticker ist
                if symbol_type and not symbol_type.startswith("COUNT"):
                    # Setze die Eingabefelder
                    if hasattr(self, 'energy_entry'):
                        self.energy_entry.setText(energy_id or "")
                    if hasattr(self, 'equipment_entry'):
                        self.equipment_entry.setText(equipment_name or "")
                    if hasattr(self, 'description_entry'):
                        self.description_entry.setText(description or "")
                    if hasattr(self, 'symbol_combo'):
                        # Finde den passenden Symbol-Typ im Combo-Box
                        try:
                            # symbol_type ist z.B. "ELECTRICAL", wir brauchen "Electrical"
                            symbol_display = symbol_type.capitalize()
                            index = self.symbol_combo.findText(symbol_display)
                            if index >= 0:
                                self.symbol_combo.setCurrentIndex(index)
                        except Exception as e:
                            logger.debug(f"Konnte Symbol-Typ nicht setzen: {e}")
            
            convert_start = time.time()
            
            # WICHTIG: Verwende THUMBNAIL zum Anzeigen (Index 0 falls neu, oder item[0] falls alt)
            display_img = item[0]  # Das ist immer das Thumbnail (neu) oder Vollbild (alt)
            
            # Schnelle PIL zu QPixmap Konvertierung - mit erweitertem Cache
            cache_index = 7
            cache_container = None
            if len(item) > cache_index and item[cache_index] is not None:
                existing_cache = item[cache_index]
                if isinstance(existing_cache, dict):
                    cache_container = existing_cache
                else:
                    cache_container = {"base": existing_cache, "scaled": {}}
                    item[cache_index] = cache_container

            base_was_cached = bool(cache_container and cache_container.get("base") is not None)

            if not base_was_cached:
                # from PIL import ImageQt - removed, use global import

                if display_img.mode != 'RGBA':
                    display_img_rgba = display_img.convert('RGBA')
                else:
                    display_img_rgba = display_img

                qimage = ImageQt.ImageQt(display_img_rgba)
                base_pixmap = QPixmap.fromImage(qimage)
                logger.debug(f"[PERF] PIL->QPixmap Konvertierung: {time.time() - convert_start:.3f}s, size={display_img_rgba.size}")

                if cache_container is None:
                    cache_container = {"base": base_pixmap, "scaled": {}}
                else:
                    cache_container["base"] = base_pixmap
                    cache_container.setdefault("scaled", {})

                if len(item) <= cache_index:
                    while len(item) <= cache_index:
                        item.append(None)
                item[cache_index] = cache_container
            if cache_container is None or not isinstance(cache_container, dict):
                cache_container = {"base": cache_container if isinstance(cache_container, QPixmap) else None, "scaled": {}}
                if len(item) <= cache_index:
                    while len(item) <= cache_index:
                        item.append(None)
                item[cache_index] = cache_container

            base_pixmap = cache_container.get("base")
            if base_pixmap is None:
                logger.warning("[PERF] Basis-Pixmap konnte nicht erzeugt werden.")
                return
            if base_was_cached:
                logger.debug(f"[PERF] QPixmap Basis aus Cache: {time.time() - convert_start:.3f}s")
            
            # Skaliere für Vorschau
            try:
                scale = float(self.sticker_config.preview_scale or 1.0)
            except Exception:
                scale = 1.0
            
            if not math.isfinite(scale) or scale <= 0:
                scale = 1.0
            
            scale_start = time.time()
            if not isinstance(cache_container, dict):
                logger.warning("[PERF] Ungültiger Cache-Typ, breche Vorschauupdate ab.")
                return

            cache_container.setdefault("scaled", {})
            scale_key = f"{scale:.2f}"
            scaled_pixmap = cache_container["scaled"].get(scale_key)

            if scaled_pixmap is None:
                scaled_pixmap = base_pixmap.scaled(
                    int(400 * scale), int(300 * scale),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                cache_container["scaled"][scale_key] = scaled_pixmap
                logger.debug(f"[PERF] Pixmap Skalierung neu: {time.time() - scale_start:.3f}s")
            else:
                logger.debug(f"[PERF] Pixmap Skalierung aus Cache: {time.time() - scale_start:.3f}s")
            
            # Maske behandeln
            mask_pixmap = None

            # Prüfen ob es ein Count-Sticker ist
            is_count = isinstance(symbol_type, str) and symbol_type.startswith("COUNT")

            if is_count:
                # Für Count-Sticker neuen Preview generieren und Shimmer aktivieren
                try:
                    marker = item[5] if len(item) > 5 else None
                    if isinstance(marker, dict):
                        detail_str = marker.get("details", "")
                    else:
                        detail_str = description

                    count = 1
                    if symbol_type == "COUNT_MULTI":
                        if detail_str:
                            items = [it for it in detail_str.split(',') if it.strip()]
                            count = len(items)
                    elif symbol_type == "COUNT_SINGLE":
                        detail_str = f"{description}"

                    new_img = self.count_generator.generate(detail_str, count)
                    if new_img:
                        if new_img.mode != 'RGBA':
                            new_img = new_img.convert('RGBA')
                        qim = ImageQt.ImageQt(new_img)
                        new_pixmap = QPixmap.fromImage(qim)

                        try:
                            scale = float(self.sticker_config.preview_scale or 1.0)
                        except Exception:
                            scale = 1.0

                        scaled_new_pixmap = new_pixmap.scaled(
                            int(400 * scale), int(300 * scale),
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation
                        )

                        if hasattr(self, 'preview_label') and self.preview_label is not None:
                            self.preview_label.setPixmap(scaled_new_pixmap)
                            # Shimmer-Maske für Count-Sticker setzen
                            mask_image = self.count_generator.get_last_text_mask()
                            if mask_image and hasattr(self.preview_label, 'set_mask_pixmap'):
                                mask_rgba = Image.new("RGBA", mask_image.size, (255, 255, 255, 0))
                                mask_rgba.putalpha(mask_image)
                                qim_mask = ImageQt.ImageQt(mask_rgba)
                                mask_pm = QPixmap.fromImage(qim_mask)
                                mask_pixmap = mask_pm.scaled(
                                    scaled_new_pixmap.width(), scaled_new_pixmap.height(),
                                    Qt.AspectRatioMode.IgnoreAspectRatio,
                                    Qt.TransformationMode.SmoothTransformation
                                )
                                self.preview_label.set_mask_pixmap(mask_pixmap)
                    return
                except Exception as e:
                    logger.warning(f"Konnte Count-Sticker Vorschau nicht generieren: {e}")

            # Normale Sticker Vorschau
            if hasattr(self, 'preview_label') and self.preview_label is not None:
                logger.debug(f"Setting preview pixmap, size: {scaled_pixmap.width()}x{scaled_pixmap.height()}")
                self.preview_label.setPixmap(scaled_pixmap)
                self.preview_label.update()  # Force repaint
                logger.debug("Preview label updated successfully")
            else:
                logger.warning("preview_label not available!")

            # Setze Maske (bei normalen Stickern aktuell keine Shimmer-Maske)
            if hasattr(self.preview_label, 'set_mask_pixmap'):
                self.preview_label.set_mask_pixmap(mask_pixmap)
            
            logger.info(f"[PERF] Collection item selected total: {time.time() - start_time:.3f}s, row={current_row}")
        except Exception as e:
            logger.error(f"Error displaying collection item: {e}", exc_info=True)

    def _edit_count_sticker_copies(self, row: int) -> None:
        """Bearbeite Kopienanzahl für einen Count-Sticker"""
        from PyQt6.QtWidgets import QSpinBox, QDialog, QVBoxLayout, QLabel, QDialogButtonBox
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QColor
        
        try:
            if row < 0 or row >= len(self.collection):
                return
            
            coll_item = self.collection[row]
            if not coll_item or len(coll_item) < 6:
                return
            
            full_info = coll_item[5]
            if not isinstance(full_info, dict):
                return
            
            # Extrahiere aktuellen Wert
            current_copies = full_info.get("copies", 1)
            
            # Erstelle Dialog
            dialog = QDialog(self)
            dialog.setWindowTitle("Kopien für Export")
            dialog.setFixedWidth(300)
            
            # Style Dialog mit hellen Farben
            dialog.setStyleSheet("""
                QDialog {
                    background-color: #ffffff;
                }
                QLabel {
                    color: #000000;
                }
                QSpinBox {
                    border: 1px solid #cccccc;
                    border-radius: 4px;
                    padding: 4px;
                    background-color: #ffffff;
                    color: #000000;
                    selection-background-color: #0078d4;
                }
                QPushButton {
                    border: 1px solid #cccccc;
                    border-radius: 4px;
                    padding: 4px 12px;
                    background-color: #f0f0f0;
                    color: #000000;
                }
                QPushButton:hover {
                    background-color: #e1e1e1;
                }
                QPushButton:pressed {
                    background-color: #d0d0d0;
                }
            """)
            
            layout = QVBoxLayout()
            
            # Label
            label = QLabel("Anzahl Kopien zum Exportieren:")
            layout.addWidget(label)
            
            # Spinbox
            spinbox = QSpinBox()
            spinbox.setMinimum(1)
            spinbox.setMaximum(999)
            spinbox.setValue(current_copies)
            spinbox.setFocus()
            spinbox.selectAll()
            layout.addWidget(spinbox)
            
            # Dialog Buttons
            button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)
            layout.addWidget(button_box)
            
            dialog.setLayout(layout)
            
            # Zeige Dialog
            if dialog.exec() == QDialog.DialogCode.Accepted:
                new_copies = spinbox.value()
                
                # Update marker
                full_info["copies"] = new_copies
                
                # Aktualisiere Display
                self.update_collection_list()
                
                logger.info(f"Updated count sticker copies: row={row}, new_copies={new_copies}")
                
                # Optionale Bestätigungsmeldung
                from PyQt6.QtWidgets import QMessageBox
                # QMessageBox.information(self, "Erfolg", f"Kopien aktualisiert zu {new_copies}")
            
        except Exception as e:
            logger.error(f"Error editing count sticker copies: {e}", exc_info=True)

    def _show_collection_context_menu(self, pos):
        """Zeige Kontextmenü für Collection Items beim Rechtsklick"""
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QAction
        
        item = self.collection_list.itemAt(pos)
        if not item:
            return
        
        # Prüfe ob mehrere Items ausgewählt sind
        selected_items = self.collection_list.selectedItems()
        selected_rows = sorted([self.collection_list.row(it) for it in selected_items], reverse=True)
        
        # Falls angeklicktes Item nicht in Auswahl, nur dieses auswählen
        clicked_row = self.collection_list.row(item)
        if clicked_row not in selected_rows:
            self.collection_list.setCurrentRow(clicked_row)
            selected_rows = [clicked_row]
        
        # Erstelle Kontextmenü
        menu = QMenu(self)
        
        is_multi_select = len(selected_rows) > 1
        
        if not is_multi_select:
            # Einzelauswahl: Alle Optionen
            current_row = selected_rows[0]
            
            # Check if it's a count sticker
            if current_row >= 0 and current_row < len(self.collection):
                coll_item = self.collection[current_row]
                is_count_single = self._is_count_single(coll_item)
                is_count_multi = self._is_count_multi(coll_item)
                
                if is_count_single or is_count_multi:
                    # Count-Sticker: Kopien-Anzahl ändern
                    copies_action = QAction("Kopien für Export ändern…", menu)
                    menu.addAction(copies_action)
                    copies_action.triggered.connect(lambda: self._edit_count_sticker_copies(current_row))
                    menu.addSeparator()
            
            # "Zur Sammlung hinzufügen" Aktion (duplizieren)
            add_action = QAction("Zur Sammlung hinzufügen (Duplizieren)", menu)
            menu.addAction(add_action)
            add_action.triggered.connect(lambda: self._duplicate_collection_item(current_row))

            # "Zum Equipment hinzufügen" Aktion
            equip_action = QAction("Zum Equipment-Manager hinzufügen…", menu)
            menu.addAction(equip_action)
            equip_action.triggered.connect(lambda: self._add_collection_item_to_equipment_manager(current_row))
            
            # Trennlinie
            menu.addSeparator()
            
            # "Aus Sammlung entfernen" Aktion
            remove_action = QAction("Aus Sammlung entfernen", menu)
            menu.addAction(remove_action)
            remove_action.triggered.connect(lambda: self._remove_collection_item(current_row))
        else:
            # Mehrfachauswahl: Nur Löschen anbieten
            remove_action = QAction(f"{len(selected_rows)} Sticker aus Sammlung entfernen", menu)
            remove_action.setIcon(qta.icon('ph.trash', color='#ef4444'))
            menu.addAction(remove_action)
            remove_action.triggered.connect(lambda: self._remove_multiple_collection_items(selected_rows))
        
        # Zeige Menü
        global_pos = self.collection_list.mapToGlobal(pos)
        menu.exec(global_pos)

    def _add_collection_item_to_equipment_manager(self, row: int) -> None:
        """Übernimmt den ausgewählten Sticker als Equipment-Eintrag in die Equipment-Hierarchie."""
        try:
            if row < 0 or row >= len(self.collection):
                return

            item = self.collection[row]
            if not item or len(item) < 4:
                return

            symbol_type = item[1] if len(item) > 1 else ""
            energy_id = (item[2] if len(item) > 2 else "") or ""
            equipment_name = (item[3] if len(item) > 3 else "") or ""
            
            # QR-Path aus full_info extrahieren (Index 5)
            qr_path = ""
            logger.info(f"DEBUG: Item length={len(item)}, full item structure: {[type(x).__name__ for x in item]}")
            if len(item) > 5:
                full_info = item[5]
                logger.info(f"full_info type={type(full_info)}, value={full_info}")
                if isinstance(full_info, dict):
                    qr_path = full_info.get("qr_path", "")
                    logger.info(f"Extracted qr_path from dict={qr_path}")
                else:
                    logger.warning(f"full_info is not a dict, it's {type(full_info)}, value={full_info}")
            else:
                logger.warning(f"Item too short, len={len(item)}, expected at least 6")

            # COUNT-Sticker nicht übernehmen
            is_count_single = (len(item) >= 6 and item[5] == "count_single") or (str(symbol_type) == "COUNT_SINGLE")
            is_count_multi = (len(item) >= 6 and item[5] == "count_multi") or (str(symbol_type) == "COUNT_MULTI")
            if is_count_single or is_count_multi:
                msg = self._create_styled_msgbox("Info", "COUNT-Sticker können nicht in den Equipment-Manager übernommen werden.")
                msg.exec()
                return

            equipment_name = str(equipment_name).strip()
            energy_id = str(energy_id).strip()
            symbol_type_str = str(getattr(symbol_type, 'name', symbol_type)).strip().upper()

            if not equipment_name:
                equipment_name, ok = QInputDialog.getText(self, "Equipment", "Name für das neue Betriebsmittel:")
                if not ok or not equipment_name.strip():
                    return
                equipment_name = equipment_name.strip()

            # Ziel-System auswählen
            dialog = EquipmentSelectionDialog(self, self.equipment_manager, getattr(self, 'theme', Theme.LIGHT))
            dialog.setWindowTitle("Ziel-System auswählen")
            if dialog.exec() != QDialog.DialogCode.Accepted or not dialog.selected_data:
                return

            sel = dialog.selected_data
            sel_type = sel.get('type')
            if sel_type == 'system':
                location = sel.get('location', '')
                system_name = sel.get('system_name', '')
            elif sel_type == 'equipment':
                location = sel.get('location', '')
                system_name = sel.get('system_name', '')
            else:
                msg = self._create_styled_msgbox("Fehler", "Bitte ein System (oder ein Equipment innerhalb eines Systems) auswählen.", QMessageBox.Icon.Warning)
                msg.exec()
                return

            if not location or not system_name:
                msg = self._create_styled_msgbox("Fehler", "Konnte Standort/System aus der Auswahl nicht ermitteln.", QMessageBox.Icon.Warning)
                msg.exec()
                return

            # Existiert Equipment bereits? -> update, sonst add
            exists = False
            try:
                for eq in self.equipment_manager.get_equipment(location, system_name):
                    if eq.get('name', '') == equipment_name:
                        exists = True
                        break
            except Exception:
                exists = False

            if exists:
                ok = self.equipment_manager.update_equipment_properties(
                    location, system_name, equipment_name,
                    energy_id=energy_id if energy_id else None,
                    symbol_type=symbol_type_str if symbol_type_str else None,
                    qr_path=qr_path if qr_path else None
                )
                if not ok:
                    msg = self._create_styled_msgbox("Fehler", "Equipment konnte nicht aktualisiert werden.", QMessageBox.Icon.Warning)
                    msg.exec()
                    return
                success_msg = "Equipment aktualisiert (zum Speichern bitte im Equipment-Tab auf 'Speichern' klicken)."
            else:
                ok = self.equipment_manager.add_equipment(
                    location, system_name, equipment_name,
                    energy_id=energy_id,
                    symbol_type=symbol_type_str,
                    qr_path=qr_path
                )
                if not ok:
                    msg = self._create_styled_msgbox("Fehler", "Equipment konnte nicht hinzugefügt werden.", QMessageBox.Icon.Warning)
                    msg.exec()
                    return
                success_msg = "Equipment hinzugefügt (zum Speichern bitte im Equipment-Tab auf 'Speichern' klicken)."

            if hasattr(self, 'equipment_controller') and self.equipment_controller:
                self.equipment_controller.refresh_tree()

            msgbox = self._create_styled_msgbox("Erfolg", success_msg)
            msgbox.exec()

        except Exception as e:
            logger.exception("Fehler beim Übernehmen in Equipment")
            msg = self._create_styled_msgbox("Fehler", f"Fehler beim Übernehmen: {e}", QMessageBox.Icon.Warning)
            msg.exec()
    
    def _duplicate_collection_item(self, row):
        """Dupliziere ein Collection Item"""
        if row < 0 or row >= len(self.collection):
            return
        
        item = self.collection[row]
        if not item or len(item) < 5:
            return
        
        # Extrahiere Daten aus dem Item
        # Collection-Struktur: [img_thumbnail, symbol_type, energy_id, equipment_name, description, full_info, img_fullsize]
        symbol_type = item[1] if len(item) > 1 else "ELECTRICAL"
        energy_id = item[2] if len(item) > 2 else ""
        equipment_name = item[3] if len(item) > 3 else ""
        description = item[4] if len(item) > 4 else ""
        full_info = item[5] if len(item) > 5 else ""
        
        # Generiere neue Bilder
        try:
            img = self.sticker_service.generate_sticker(
                energy_id=energy_id,
                equipment=equipment_name,
                symbol_name=symbol_type,
                description=description
            )
            
            if img is None:
                msg = self._create_styled_msgbox("Fehler", "Sticker konnte nicht generiert werden", QMessageBox.Icon.Warning)
                msg.exec()
                return
            
            # Thumbnail erstellen
            img_thumbnail = img.copy()
            img_thumbnail.thumbnail((400, 300), Image.Resampling.LANCZOS)
            
            # Item zur Collection hinzufügen
            self.collection_service.add_item(
                energy_id=energy_id,
                equipment=equipment_name,
                symbol_type=symbol_type,
                description=description,
                image=img,
                thumbnail=img_thumbnail
            )
            
            # Legacy: Auch in alte self.collection schreiben
            self.collection.append([img_thumbnail, symbol_type, energy_id, equipment_name, description, full_info, img])
            
            # UI aktualisieren
            self.update_collection_list()
            msg = self._create_styled_msgbox("Erfolg", "Sticker zur Sammlung hinzugefügt")
            msg.exec()
            
        except Exception as e:
            logger.error(f"Fehler beim Duplizieren: {e}")
            msg = self._create_styled_msgbox("Fehler", f"Fehler beim Duplizieren: {e}", QMessageBox.Icon.Warning)
            msg.exec()
    
    def _remove_collection_item(self, row):
        """Entferne ein Collection Item"""
        if row < 0 or row >= len(self.collection):
            return
        
        item = self.collection[row]
        if not item or len(item) < 3:
            return
        
        energy_id = item[2] if len(item) > 2 else "Unknown"
        equipment_name = item[3] if len(item) > 3 else "Unknown"
        
        # Bestätigung
        reply = QMessageBox.question(
            self, "Bestätigung",
            f"Sticker '{energy_id} / {equipment_name}' wirklich löschen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Entferne aus Collection Service
        self.collection_service.remove_item(row)
        
        # Entferne aus Legacy Collection
        if row < len(self.collection):
            del self.collection[row]
        
        logger.info(f"Sticker gelöscht. Collection hat jetzt {len(self.collection)} Items")
        
        # UI aktualisieren
        self.update_collection_list()
        
        # Count-Sticker aktualisieren
        logger.info("Aktualisiere Count-Sticker nach Löschung...")
        self._regenerate_multi_count_sticker()

    def _remove_multiple_collection_items(self, rows: list):
        """Entferne mehrere Collection Items (Strg+Mehrfachauswahl)"""
        if not rows:
            return
        
        # Bestätigung
        reply = QMessageBox.question(
            self, "Bestätigung",
            f"{len(rows)} Sticker wirklich löschen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Sortiere absteigend um Index-Verschiebung zu vermeiden
        rows_sorted = sorted(rows, reverse=True)
        
        for row in rows_sorted:
            if row < 0 or row >= len(self.collection):
                continue
            
            # Entferne aus Collection Service
            try:
                self.collection_service.remove_item(row)
            except Exception:
                pass
            
            # Entferne aus Legacy Collection
            if row < len(self.collection):
                del self.collection[row]
        
        logger.info(f"{len(rows)} Sticker gelöscht. Collection hat jetzt {len(self.collection)} Items")
        
        # UI aktualisieren
        self.update_collection_list()
        
        # Count-Sticker aktualisieren
        logger.info("Aktualisiere Count-Sticker nach Mehrfach-Löschung...")
        self._regenerate_multi_count_sticker()
        logger.info("Count-Sticker aktualisiert")
        
        msg = self._create_styled_msgbox("Erfolg", "Sticker entfernt")
        msg.exec()

    def regenerate_all_stickers(self):
        """Alle Sticker in der Sammlung mit aktuellen Einstellungen neu generieren"""
        if not self.collection:
            msg = self._create_styled_msgbox("Info", "Keine Sticker zum Regenerieren.")
            msg.exec()
            return
        
        # Bestätigung
        msg = self._create_styled_msgbox(
            "Bestätigung",
            f"Alle {len(self.collection)} Sticker mit aktuellen Einstellungen (inkl. QR-Code) neu generieren?",
            QMessageBox.Icon.Question,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if msg.exec() != QMessageBox.StandardButton.Yes:
            return
        
        # Progress bar
        progress_bar = None
        if hasattr(self, 'magic_menu'):
            progress_bar = self.magic_menu.progress_bar
            progress_bar.setRange(0, len(self.collection))
            progress_bar.setValue(0)
            progress_bar.setVisible(True)
        
        regenerated_count = 0
        errors = []
        
        try:
            for i, item in enumerate(self.collection):
                try:
                    # Extract data from collection item
                    # Format: [img_thumbnail, symbol_type, energy_id, equipment, description, full_info, img]
                    if len(item) < 5:
                        continue
                    
                    symbol_type = item[1] if len(item) > 1 else "ELECTRICAL"
                    energy_id = item[2] if len(item) > 2 else ""
                    equipment = item[3] if len(item) > 3 else ""
                    description = item[4] if len(item) > 4 else ""
                    
                    # Skip count stickers
                    if len(item) >= 6 and (item[5] == 'count_single' or item[5] == 'count_multi'):
                        if progress_bar:
                            progress_bar.setValue(i + 1)
                        continue
                    
                    # Regenerate sticker with current config
                    new_img = self.sticker_service.generate_sticker(
                        energy_id=energy_id,
                        equipment=equipment,
                        symbol_name=symbol_type,
                        description=description
                    )
                    
                    if new_img:
                        # Create new thumbnail
                        new_thumbnail = new_img.copy()
                        new_thumbnail.thumbnail((400, 300), Image.Resampling.LANCZOS)
                        
                        # Update collection item
                        item[0] = new_thumbnail  # thumbnail
                        if len(item) > 6:
                            item[6] = new_img  # full image
                        
                        # Update in collection service
                        self.collection_service.update_item_image(i, new_img, new_thumbnail)
                        
                        regenerated_count += 1
                    
                except Exception as e:
                    errors.append(f"Sticker {i+1}: {str(e)}")
                    logger.error(f"Error regenerating sticker {i}: {e}")
                
                if progress_bar:
                    progress_bar.setValue(i + 1)
                QApplication.processEvents()
            
            # Update UI
            self.update_collection_list()
            
        finally:
            if progress_bar:
                progress_bar.setVisible(False)
        
        # Show result
        if errors:
            error_msg = f"{regenerated_count} Sticker regeneriert.\n\nFehler:\n" + "\n".join(errors[:5])
            if len(errors) > 5:
                error_msg += f"\n... und {len(errors) - 5} weitere Fehler"
            msg = self._create_styled_msgbox("Abgeschlossen", error_msg, QMessageBox.Icon.Warning)
        else:
            msg = self._create_styled_msgbox("Erfolg", f"{regenerated_count} Sticker erfolgreich regeneriert!")
        msg.exec()

    def clear_collection(self):
        """Sammlung leeren - nutzt CollectionService"""
        if self.collection_service.is_empty():
            msg = self._create_styled_msgbox("Info", "Sammlung ist bereits leer", QMessageBox.Icon.Information)
            msg.exec()
            return

        count = self.collection_service.get_count()
        msg_box = self._create_styled_msgbox(
            "Bestätigung",
            f"Alle {count} Sticker löschen?",
            QMessageBox.Icon.Question,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        reply = msg_box.exec()

        if reply == QMessageBox.StandardButton.Yes:
            self.collection_service.clear()
            # Legacy: Auch alte Liste leeren
            self.collection.clear()
            self.collection_export_sources.clear()
            # UI aktualisieren
            self.update_collection_list()
            if self.status_bar:
                self.status_bar.showMessage("Sammlung geleert", 2000)

    def register_collection_source(self, source: str):
        if source:
            self.collection_export_sources.add(str(source).strip())

    @staticmethod
    def _extract_group_key(energy_id, equipment='', description=''):
        """Extrahiert den Gruppenschlüssel aus Energy-ID + Equipment + Description.
        
        Prüft nacheinander: SC_XX.XX → KSV{N}→SC_02.0{N} → NSHV → UV-H/WALLBOX
        Bezieht alle Felder ein (für Split-IDs über mehrere Zeilen im PDF).
        """
        import re
        combined = (energy_id + '.' + equipment + '.' + description).upper()
        
        # 1. SC-Pattern direkt vorhanden
        sc_match = re.search(r'SC_(\d+)\.(\d+)', combined)
        if sc_match:
            return f"SC_{sc_match.group(1)}.{sc_match.group(2).zfill(2)}"
        
        # 2. KSV{N} → abgeleitetes SC-Pattern
        ksv_match = re.search(r'KSV(\d+)', combined)
        if ksv_match:
            n = int(ksv_match.group(1))
            return f"SC_02.{str(n).zfill(2)}"
        
        # 3. NSHV-Sticker
        if 'NSHV' in combined:
            return "NSHV"
        
        # 4. UV-H / WALLBOX
        if 'UV-H' in combined or 'WALLBOX' in combined:
            return "UV-H"
        
        return None

    def _detect_missing_stickers(self, extracted_data, count_sticker_groups):
        """Erkennt fehlende Sticker durch Vergleich von Count-Sticker-Einträgen mit extrahierten Stickern.
        
        Verwendet Multi-Pass-Matching:
        1. Full-ID Match (exakt und Prefix)
        2. SC-Key + Energy-Prefix Match
        3. Energy-Prefix-Only Match (Last Resort)
        
        Returns:
            list: Liste der fehlenden Count-Sticker-Einträge (Strings)
        """
        import re
        
        if not count_sticker_groups:
            return []
        
        # Alle Count-Sticker-Einträge flach sammeln
        all_count_entries = []
        for group in count_sticker_groups:
            for entry in group:
                normalized = entry.strip().strip(".").upper()
                if normalized:
                    all_count_entries.append(normalized)
        
        if not all_count_entries:
            return []
        
        # Sticker-Informationen aufbauen
        sticker_infos = []
        for i, sticker in enumerate(extracted_data):
            eid = sticker.get("energy_id", "").strip().strip(".")
            eq = sticker.get("equipment", "").strip().strip(".")
            desc = sticker.get("description", "").strip().strip(".")
            parts = [p for p in [eid, eq, desc] if p]
            full_id = ".".join(parts).upper()
            
            key = self._extract_group_key(eid, eq, desc)
            
            sticker_infos.append({
                "index": i,
                "energy_id": eid.upper(),
                "full_id": full_id,
                "key": key,
                "claimed": False,
            })
        
        matched_entries = set()
        
        # Pass 1: Full-ID-Matching (exakt und Prefix)
        for entry in all_count_entries:
            for info in sticker_infos:
                if info["claimed"]:
                    continue
                if info["full_id"] == entry:
                    info["claimed"] = True
                    matched_entries.add(entry)
                    break
                if entry.startswith(info["full_id"]) or info["full_id"].startswith(entry):
                    info["claimed"] = True
                    matched_entries.add(entry)
                    break
        
        # Pass 2: SC-Key + Energy-Prefix
        for entry in all_count_entries:
            if entry in matched_entries:
                continue
            m = re.match(r'^([EPMC]\d+)', entry)
            entry_prefix = m.group(1).upper() if m else ""
            entry_key = self._extract_group_key(entry)
            
            if entry_key and entry_prefix:
                for info in sticker_infos:
                    if info["claimed"]:
                        continue
                    if info["energy_id"] == entry_prefix and info["key"] == entry_key:
                        info["claimed"] = True
                        matched_entries.add(entry)
                        break
        
        # Pass 3: Energy-Prefix Only (Last Resort)
        for entry in all_count_entries:
            if entry in matched_entries:
                continue
            m = re.match(r'^([EPMC]\d+)', entry)
            entry_prefix = m.group(1).upper() if m else ""
            
            if entry_prefix:
                for info in sticker_infos:
                    if info["claimed"]:
                        continue
                    if info["energy_id"] == entry_prefix:
                        info["claimed"] = True
                        matched_entries.add(entry)
                        break
        
        # Nicht gematchte Einträge sind fehlend
        missing = [entry for entry in all_count_entries if entry not in matched_entries]
        
        if missing:
            logger.info(f"Fehlende Sticker erkannt: {missing}")
        
        return missing

    def _detect_missing_from_group_gaps(self, extracted_data, count_sticker_groups=None):
        """Erkennt fehlende Sticker durch Lücken in E-Nummern-Sequenzen innerhalb von Gruppen.
        
        Analysiert Gruppen, die NICHT durch Count-Sticker-Daten abgedeckt sind,
        und sucht nach fehlenden sequentiellen E-Nummern (z.B. E2 vorhanden aber E1 fehlt).
        
        Returns:
            list: Liste der wahrscheinlich fehlenden Sticker-IDs (Strings)
        """
        import re
        
        # Bestimme welche Gruppen durch Count-Sticker abgedeckt sind
        covered_keys = set()
        if count_sticker_groups:
            for group_entries in count_sticker_groups:
                for entry in group_entries:
                    key = self._extract_group_key(entry)
                    if key:
                        covered_keys.add(key)
        
        # Sticker nach Gruppe gruppieren
        groups = {}  # key -> list of (num, prefix_char, rest_equipment)
        for sticker in extracted_data:
            eid = sticker.get('energy_id', '').strip().strip('.')
            eq = sticker.get('equipment', '').strip().strip('.')
            desc = sticker.get('description', '').strip().strip('.')
            
            key = self._extract_group_key(eid, eq, desc)
            if not key or key in covered_keys:
                continue
            
            # E-Nummer aus dem Anfang parsen
            full_combined = '.'.join(p for p in [eid, eq, desc] if p).upper()
            m = re.match(r'^([EPMC])(\d+)', full_combined)
            if not m:
                continue
            
            prefix_char = m.group(1)
            num = int(m.group(2))
            rest = full_combined[len(m.group(0)):].lstrip('.')
            
            if key not in groups:
                groups[key] = []
            groups[key].append((num, prefix_char, rest))
        
        missing = []
        
        for key, members in groups.items():
            if not members:
                continue
            
            nums = set(m[0] for m in members)
            prefix_char = members[0][1]
            max_num = max(nums)
            
            # Nur Lücken erkennen wenn max > 1
            if max_num <= 1:
                continue
            
            missing_nums = sorted(set(range(1, max_num + 1)) - nums)
            if not missing_nums:
                continue
            
            # Equipment-Basis ableiten: Schlüssel im Equipment suchen
            eq_base = None
            for _, _, rest in members:
                rest_upper = rest.upper()
                idx = rest_upper.find(key)
                if idx >= 0:
                    after_key = rest_upper[idx + len(key):]
                    extra = re.match(r'[\d.]+', after_key)
                    if extra:
                        end_pos = idx + len(key) + extra.end()
                    else:
                        end_pos = idx + len(key)
                    base = rest[:end_pos].rstrip('.')
                    if eq_base is None or len(base) < len(eq_base):
                        eq_base = base
            
            if not eq_base:
                shortest = min(members, key=lambda m: len(m[2]))
                eq_base = shortest[2].rstrip('.')
            
            for num in missing_nums:
                entry = f"{prefix_char}{num}.{eq_base}"
                missing.append(entry)
        
        if missing:
            logger.info(f"Fehlende Sticker aus Lückenanalyse: {missing}")
        
        return missing

    def _show_missing_stickers_dialog(self, missing_entries):
        """Zeigt Dialog mit fehlenden Stickern und bietet deren Erstellung an.
        
        Args:
            missing_entries: Liste der fehlenden Energy-ID-Strings
            
        Returns:
            list: Ausgewählte Einträge die erstellt werden sollen (oder leere Liste)
        """
        from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                                      QCheckBox, QScrollArea, QWidget)
        from ui.glass_button import GlassGlowButton
        from ui.theme import Theme, get_theme_colors, create_dialog_stylesheet
        import qtawesome as qta
        
        theme = getattr(self, 'theme', Theme.LIGHT)
        colors = get_theme_colors(theme)
        text_color = colors["fg"]
        accent = colors["accent"]
        card_bg = "rgba(0,0,0,0.03)"
        border_color = "rgba(0,0,0,0.08)"
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Fehlende Sticker erkannt")
        dialog.setModal(True)
        dialog.setMinimumWidth(520)
        dialog.setStyleSheet(create_dialog_stylesheet(theme))
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 20, 24, 20)
        
        # Header mit Icon
        header_layout = QHBoxLayout()
        header_icon = QLabel()
        header_icon.setPixmap(qta.icon('ph.warning', color=accent).pixmap(QSize(22, 22)))
        header_layout.addWidget(header_icon)
        
        header = QLabel("Fehlende Sticker erkannt")
        header.setStyleSheet(f"color: {text_color}; font-size: 15px; font-weight: 600; border: none;")
        header_layout.addWidget(header)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        info = QLabel(
            f"Die folgenden {len(missing_entries)} Sticker sind in den Count-Stickern aufgeführt, "
            f"wurden aber nicht als eigene Sticker im PDF gefunden.\n"
            f"Möglicherweise wurden sie vom Ersteller vergessen.\n\n"
            f"Wähle die Sticker aus, die erstellt werden sollen:"
        )
        info.setWordWrap(True)
        info.setStyleSheet(f"color: {text_color}; font-size: 12px; border: none; padding-bottom: 4px;")
        layout.addWidget(info)
        
        # Scroll-Bereich mit Checkboxen
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(300)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: 1px solid {border_color};
                border-radius: 8px;
            }}
        """)
        
        scroll_widget = QWidget()
        scroll_widget.setStyleSheet("background: transparent;")
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(4)
        scroll_layout.setContentsMargins(8, 8, 8, 8)
        
        checkboxes = []
        for entry in missing_entries:
            cb = QCheckBox(entry)
            cb.setChecked(True)
            cb.setStyleSheet(f"""
                QCheckBox {{
                    color: {text_color};
                    font-size: 13px;
                    font-family: 'Consolas', 'Courier New', monospace;
                    padding: 6px 8px;
                    background: {card_bg};
                    border-radius: 6px;
                    border: none;
                }}
                QCheckBox::indicator {{
                    width: 16px;
                    height: 16px;
                    border-radius: 4px;
                    border: 1.5px solid rgba(128,128,128,0.3);
                }}
                QCheckBox::indicator:checked {{
                    background: {accent};
                    border: 1.5px solid {accent};
                }}
                QCheckBox::indicator:hover {{
                    border: 1.5px solid {accent};
                }}
            """)
            scroll_layout.addWidget(cb)
            checkboxes.append((cb, entry))
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        button_layout.addStretch()
        
        skip_btn = GlassGlowButton("Überspringen")
        skip_btn.setMinimumHeight(40)
        skip_btn.setMinimumWidth(130)
        skip_btn.setIcon(qta.icon('ph.skip-forward', color=text_color))
        skip_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(skip_btn)
        
        create_btn = GlassGlowButton("Ausgewählte erstellen")
        create_btn.setMinimumHeight(40)
        create_btn.setMinimumWidth(180)
        create_btn.setIcon(qta.icon('ph.plus-circle', color=text_color))
        create_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(create_btn)
        
        layout.addLayout(button_layout)
        
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return []
        
        return [entry for cb, entry in checkboxes if cb.isChecked()]

    def _create_stickers_from_entries(self, extracted_data, entries):
        """Erstellt Sticker-Dicts aus Count-Sticker-Einträgen und fügt sie zu extracted_data hinzu.
        
        Args:
            extracted_data: Liste der extrahierten Sticker (wird in-place erweitert)
            entries: Liste der zu erstellenden Energy-ID-Strings
            
        Returns:
            int: Anzahl der erstellten Sticker
        """
        import re
        
        created = 0
        for entry in entries:
            # Split: "E1.ELEC.DP.UV-H0.1" → energy_id="E1", rest="ELEC.DP.UV-H0.1"
            match = re.match(r'^([EPMC]\d+)\.(.+)$', entry, re.IGNORECASE)
            if match:
                energy_id = match.group(1).upper()
                equipment = match.group(2)
            else:
                energy_id = entry.upper()
                equipment = ""
            
            # Symbol-Typ basierend auf Präfix
            prefix = energy_id[0] if energy_id else 'E'
            symbol_map = {'P': "PNEUMATIC", 'M': "MECHANICAL", 'C': "CHEMICAL"}
            symbol_type = symbol_map.get(prefix, "ELECTRICAL")
            
            new_sticker = {
                "energy_id": energy_id,
                "equipment": equipment,
                "symbol_type": symbol_type,
                "description": "",
                "_created_from_count": True,  # Markierung für nachträglich erstellte Sticker
            }
            
            extracted_data.append(new_sticker)
            created += 1
            logger.info(f"Fehlender Sticker erstellt: {energy_id} / {equipment}")
        
        return created

    def _show_loto_grouping_dialog(self, extracted_data, count_sticker_groups=None):
        """Zeigt einen Dialog zur manuellen Gruppierung von Stickern für Multi-LOTO.
        
        Args:
            extracted_data: Liste der extrahierten Sticker-Daten
            count_sticker_groups: Liste von Listen mit Energy-IDs aus erkannten Count-Stickern
        
        Returns:
            dict: {sticker_index: group_name} oder None bei Abbruch
        """
        from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                                      QTableWidget, QTableWidgetItem, QHeaderView,
                                      QComboBox, QSpinBox, QWidget, QPushButton,
                                      QAbstractItemView,
                                      QLineEdit, QCheckBox, QScrollArea)
        from ui.glass_button import GlassGlowButton
        from ui.theme import Theme, get_theme_colors, create_dialog_stylesheet
        
        theme = getattr(self, 'theme', Theme.LIGHT)
        colors = get_theme_colors(theme)
        
        dialog = QDialog(self)
        dialog.setWindowTitle("LOTO Gruppen zuweisen")
        dialog.setModal(True)
        dialog.setMinimumSize(750, 500)
        dialog.setStyleSheet(create_dialog_stylesheet(theme))
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QLabel("Multi-LOTO Gruppierung")
        header.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {colors['fg']};")
        layout.addWidget(header)
        
        info = QLabel("Weisen Sie jedem Sticker eine Gruppe zu. Sticker mit der gleichen Gruppe erhalten einen gemeinsamen Count-Sticker.\nGruppe 0 = Single LOTO (eigener Count-Sticker pro Sticker).")
        info.setWordWrap(True)
        info.setStyleSheet(f"font-size: 11px; color: {colors['fg']}; opacity: 0.8;")
        layout.addWidget(info)
        
        # Gruppen-Anzahl Steuerung
        group_ctrl_layout = QHBoxLayout()
        group_ctrl_label = QLabel("Anzahl Gruppen:")
        group_ctrl_label.setStyleSheet(f"font-size: 12px; color: {colors['fg']};")
        group_ctrl_layout.addWidget(group_ctrl_label)
        
        group_spin = StyledSpinBox()
        group_spin.setRange(1, 20)
        group_spin.setValue(2)
        group_spin.setFixedWidth(80)
        group_spin.setFixedHeight(36)
        group_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Light theme Farben für die SpinBox
        spin_bg = "#ffffff"
        spin_fg = "#1f2937"
        spin_border = "#d1d5db"
        group_spin.setStyleSheet(f"""
            QSpinBox {{
                padding: 2px 2px 2px 2px;
                border: 2px solid {spin_border};
                border-radius: 8px;
                background: {spin_bg};
                color: {spin_fg};
                font-size: 16px;
                font-weight: 700;
                min-height: 0px;
            }}
            QSpinBox:hover {{
                border-color: #FFC000;
                background: {spin_bg};
            }}
            QSpinBox:focus {{
                border-color: #3498db;
                background: {spin_bg};
            }}
            QSpinBox::up-button {{
                width: 0px; border: none; background: none;
            }}
            QSpinBox::down-button {{
                width: 0px; border: none; background: none;
            }}
        """)
        group_ctrl_layout.addWidget(group_spin)
        
        auto_btn = GlassGlowButton("Auto-Zuweisen")
        auto_btn.setFixedHeight(32)
        auto_btn.setMinimumWidth(160)
        group_ctrl_layout.addWidget(auto_btn)
        
        add_missing_btn = GlassGlowButton("  Fehlenden Sticker +")
        add_missing_btn.setFixedHeight(32)
        add_missing_btn.setMinimumWidth(170)
        add_missing_btn.setIcon(qta.icon('ph.plus-circle', color='#374151'))
        add_missing_btn.setIconSize(QSize(16, 16))
        group_ctrl_layout.addWidget(add_missing_btn)
        
        group_ctrl_layout.addStretch()
        layout.addLayout(group_ctrl_layout)
        
        class RowDragTableWidget(QTableWidget):
            """QTableWidget mit stabilem Zeilen-Drag&Drop inkl. Cell-Widgets."""

            def __init__(self, parent=None):
                super().__init__(parent)
                self._rows_changed_callback = None
                self._group_widget_factory = None
                self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                self.customContextMenuRequested.connect(self._show_context_menu)

            def _show_context_menu(self, pos):
                row = self.rowAt(pos.y())
                if row < 0:
                    return
                menu = QMenu(self)
                delete_action = menu.addAction("Zeile löschen")
                action = menu.exec(self.viewport().mapToGlobal(pos))
                if action == delete_action:
                    self._delete_selected_rows()

            def _delete_selected_rows(self):
                rows = sorted(set(idx.row() for idx in self.selectedIndexes()), reverse=True)
                for row in rows:
                    self.removeRow(row)
                if callable(self._rows_changed_callback):
                    self._rows_changed_callback()

            def keyPressEvent(self, event):
                if event.key() == Qt.Key.Key_Delete:
                    self._delete_selected_rows()
                else:
                    super().keyPressEvent(event)

            def set_rows_changed_callback(self, callback):
                self._rows_changed_callback = callback

            def set_group_widget_factory(self, factory):
                self._group_widget_factory = factory

            def _move_row(self, source_row, target_row):
                if source_row < 0 or source_row >= self.rowCount():
                    return

                if target_row < 0:
                    target_row = self.rowCount()

                if target_row > self.rowCount():
                    target_row = self.rowCount()

                if target_row == source_row or target_row == source_row + 1:
                    return

                source_items = []
                for col in range(3):
                    src = self.item(source_row, col)
                    source_items.append(src.clone() if src is not None else None)

                source_group_idx = 0
                source_combo = self.cellWidget(source_row, 3)
                if isinstance(source_combo, QComboBox):
                    source_group_idx = source_combo.currentIndex()

                self.removeRow(source_row)

                if target_row > source_row:
                    target_row -= 1

                self.insertRow(target_row)

                for col, item in enumerate(source_items):
                    if item is not None:
                        self.setItem(target_row, col, item)

                if callable(self._group_widget_factory):
                    group_combo = self._group_widget_factory(source_group_idx)
                    self.setCellWidget(target_row, 3, group_combo)

                self.setCurrentCell(target_row, 0)

                if callable(self._rows_changed_callback):
                    self._rows_changed_callback()

            def dropEvent(self, event):
                if event.source() is self:
                    source_row = self.currentRow()
                    target_row = self.rowAt(int(event.position().y()))
                    self._move_row(source_row, target_row)
                    event.setDropAction(Qt.DropAction.CopyAction)
                    event.accept()
                    return

                super().dropEvent(event)

        # Tabelle
        # Filtere Separator-Items heraus
        sticker_items = [(i, d) for i, d in enumerate(extracted_data) if not d.get("is_separator")]
        
        table = RowDragTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Energy ID", "Equipment", "Beschreibung", "Gruppe"])
        table.setRowCount(len(sticker_items))
        role_orig_idx = Qt.ItemDataRole.UserRole
        role_sticker_pos = Qt.ItemDataRole.UserRole + 1
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        table.horizontalHeader().resizeSection(3, 100)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked |
            QTableWidget.EditTrigger.EditKeyPressed |
            QTableWidget.EditTrigger.AnyKeyPressed
        )
        table.setDragEnabled(True)
        table.viewport().setAcceptDrops(True)
        table.setDropIndicatorShown(True)
        table.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        table.setDefaultDropAction(Qt.DropAction.CopyAction)
        table.setDragDropOverwriteMode(False)
        table.setAlternatingRowColors(False)
        
        table_bg = "#ffffff"
        table_alt = "#f7f8fa"
        table_header_bg = "#f0f0f0"
        table_border = "#e0e0e0"
        table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {table_bg};
                color: {colors['fg']};
                border: 1px solid {table_border};
                border-radius: 6px;
                gridline-color: {table_border};
                font-size: 11px;
            }}
            QTableWidget::item {{
                padding: 4px 8px;
                color: {colors['fg']};
            }}
            QHeaderView::section {{
                background-color: {table_header_bg};
                color: {colors['fg']};
                padding: 6px;
                border: none;
                border-bottom: 1px solid {table_border};
                font-weight: 600;
                font-size: 11px;
            }}
        """)
        
        # Gruppen-Farben für visuelle Unterscheidung (kräftig & eindeutig)
        group_colors_light = ["#ffffff",   # 0 = Single (weiß/neutral)
                              "#bbdefb",   # Gruppe 1 - Blau
                              "#c8e6c9",   # Gruppe 2 - Grün
                              "#ffe0b2",   # Gruppe 3 - Orange
                              "#f8bbd0",   # Gruppe 4 - Rosa
                              "#d1c4e9",   # Gruppe 5 - Lila
                              "#b2ebf2",   # Gruppe 6 - Cyan
                              "#fff9c4",   # Gruppe 7 - Gelb
                              "#d7ccc8",   # Gruppe 8 - Braun
                              "#c5cae9",   # Gruppe 9 - Indigo
                              "#dcedc8"]   # Gruppe 10 - Limette
        
        def get_group_color(group_idx):
            """Liefert Hintergrundfarbe für eine Gruppe"""
            return group_colors_light[group_idx % len(group_colors_light)]
        
        combo_style_base = f"""
            QComboBox {{
                background-color: {spin_bg};
                color: {spin_fg};
                border: 1px solid {spin_border};
                border-radius: 3px;
                padding: 2px 6px;
                font-size: 11px;
                font-weight: 600;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {spin_bg};
                color: {spin_fg};
                border: 1px solid {spin_border};
                selection-background-color: {colors['accent']};
                selection-color: white;
            }}
        """

        def build_group_combo(current_index=0):
            combo = QComboBox()
            combo.setStyleSheet(combo_style_base)
            n = group_spin.value()
            for g in range(n + 1):
                combo.addItem(f"Gruppe {g}" if g > 0 else "0 (Single)")
            combo.setCurrentIndex(max(0, min(current_index, combo.count() - 1)))
            combo.currentIndexChanged.connect(update_row_colors)
            return combo
        
        def update_row_colors():
            """Aktualisiert die Zeilenfarben basierend auf der Gruppenzuordnung"""
            for row_idx in range(table.rowCount()):
                combo = table.cellWidget(row_idx, 3)
                if combo is None:
                    continue
                grp = combo.currentIndex()
                bg_color = get_group_color(grp)
                for col in range(3):
                    cell = table.item(row_idx, col)
                    if cell:
                        cell.setBackground(QColor(bg_color))
        
        for row, (orig_idx, data) in enumerate(sticker_items):
            energy_id = data.get("energy_id", "")
            equipment = data.get("equipment", "")
            description = data.get("description", "")
            
            e_item = QTableWidgetItem(energy_id)
            e_item.setData(role_orig_idx, orig_idx)
            e_item.setData(role_sticker_pos, row)
            table.setItem(row, 0, e_item)
            
            eq_item = QTableWidgetItem(equipment)
            eq_item.setData(role_orig_idx, orig_idx)
            eq_item.setData(role_sticker_pos, row)
            table.setItem(row, 1, eq_item)
            
            d_item = QTableWidgetItem(description)
            d_item.setData(role_orig_idx, orig_idx)
            d_item.setData(role_sticker_pos, row)
            table.setItem(row, 2, d_item)
            
            combo = build_group_combo(1 if group_spin.value() > 1 else 0)
            table.setCellWidget(row, 3, combo)

        # Interne Qt-Sortierung deaktivieren, damit Drag&Drop-Reihenfolge stabil bleibt.
        # Sortierung erfolgt stattdessen manuell per Header-Klick.
        table.setSortingEnabled(False)
        header = table.horizontalHeader()
        header.setSortIndicatorShown(True)
        header.setSectionsClickable(True)
        sort_state = {"column": 0, "order": Qt.SortOrder.AscendingOrder}

        def sort_by_column(column):
            if sort_state["column"] == column:
                sort_state["order"] = (
                    Qt.SortOrder.DescendingOrder
                    if sort_state["order"] == Qt.SortOrder.AscendingOrder
                    else Qt.SortOrder.AscendingOrder
                )
            else:
                sort_state["column"] = column
                sort_state["order"] = Qt.SortOrder.AscendingOrder

            table.sortItems(sort_state["column"], sort_state["order"])
            header.setSortIndicator(sort_state["column"], sort_state["order"])
            update_row_colors()

        header.sectionClicked.connect(sort_by_column)
        table.set_rows_changed_callback(update_row_colors)
        table.set_group_widget_factory(build_group_combo)

        # Initial nach Energy ID sortieren.
        table.sortItems(0, Qt.SortOrder.AscendingOrder)
        header.setSortIndicator(0, Qt.SortOrder.AscendingOrder)
        
        layout.addWidget(table, 1)
        
        def update_group_count():
            """Aktualisiert die Gruppen-Auswahl in allen ComboBoxes"""
            n = group_spin.value()
            for row_idx in range(table.rowCount()):
                combo = table.cellWidget(row_idx, 3)
                if combo is None:
                    continue
                current = combo.currentIndex()
                combo.blockSignals(True)
                combo.clear()
                for g in range(n + 1):  # 0 = Single, 1..n = Gruppen
                    combo.addItem(f"Gruppe {g}" if g > 0 else "0 (Single)")
                combo.setCurrentIndex(min(current, n))
                combo.blockSignals(False)
            update_row_colors()
        
        # Verwende die statische Methode als lokale Funktion
        extract_group_key = self._extract_group_key
        
        def auto_assign_groups():
            """Verteilt Sticker auf Gruppen basierend auf:
            1. Count-Sticker aus PDF (SC-Key je Gruppe)
            2. Fallback: SC-Key aus Energy-ID + Equipment der einzelnen Sticker
            Gruppen werden aufsteigend nach SC-Nummer sortiert."""
            
            import re
            
            # === Schritt 1: Alle verfügbaren Gruppen-Keys sammeln ===
            
            # Count-Sticker-Gruppen → SC-Key extrahieren
            cs_group_keys = {}  # SC-Key → group entries list
            if count_sticker_groups:
                for group_entries in count_sticker_groups:
                    # Bestimme den SC-Key dieser Gruppe (häufigster Key)
                    key_counts = {}
                    for entry in group_entries:
                        key = extract_group_key(entry)
                        if key:
                            key_counts[key] = key_counts.get(key, 0) + 1
                    if key_counts:
                        group_key = max(key_counts, key=key_counts.get)
                        cs_group_keys[group_key] = group_entries
            
            # === Schritt 2: Sticker ihren Gruppen zuordnen ===
            sticker_key_map = {}  # row → SC-Key
            all_keys = set()
            
            for row, (orig_idx, data) in enumerate(sticker_items):
                energy_id = data.get("energy_id", "").strip()
                equipment = data.get("equipment", "").strip()
                description = data.get("description", "").strip()
                key = extract_group_key(energy_id, equipment, description)
                if key:
                    sticker_key_map[row] = key
                    all_keys.add(key)
                else:
                    sticker_key_map[row] = None
            
            # === Schritt 3: Alle Gruppen-Keys sortieren (aufsteigend) ===
            def key_sort(k):
                sc_match = re.match(r'SC_(\d+)\.(\d+)', k)
                if sc_match:
                    return (0, int(sc_match.group(1)), int(sc_match.group(2)))
                # NSHV, UV-H etc. nach SC-Gruppen
                return (1, 0, hash(k) % 1000)
            
            sorted_keys = sorted(all_keys, key=key_sort)
            
            # Key → Gruppen-Index (1-basiert)
            key_to_group = {key: idx + 1 for idx, key in enumerate(sorted_keys)}
            num_groups = len(sorted_keys)
            
            if num_groups < 1:
                return
            
            # === Schritt 4: Gruppenanzahl setzen und zuweisen ===
            group_spin.setValue(num_groups)
            update_group_count()
            
            for row, (orig_idx, data) in enumerate(sticker_items):
                key = sticker_key_map.get(row)
                group_idx = key_to_group.get(key, 0) if key else 0
                target_row = None
                for r in range(table.rowCount()):
                    energy_item = table.item(r, 0)
                    if energy_item and energy_item.data(role_sticker_pos) == row:
                        target_row = r
                        break
                if target_row is not None:
                    combo = table.cellWidget(target_row, 3)
                    if combo is not None:
                        combo.setCurrentIndex(min(group_idx, combo.count() - 1))
            
            # Logging
            cs_keys_found = set(cs_group_keys.keys()) & all_keys
            fallback_keys = all_keys - set(cs_group_keys.keys())
            logger.info(f"Auto-Zuweisen: {num_groups} Gruppen gesamt "
                       f"({len(cs_keys_found)} aus Count-Stickern, {len(fallback_keys)} aus Sticker-Analyse)")
            logger.info(f"  Gruppen: {sorted_keys}")
            
            update_row_colors()
        
        def add_missing_sticker():
            """Öffnet Dialog mit erkannten fehlenden Stickern + manueller Eingabe."""
            
            # Fehlende Sticker berechnen (Count-Sticker-Einträge ohne passenden Sticker)
            missing_entries = []
            if count_sticker_groups:
                missing_entries = self._detect_missing_stickers(extracted_data, count_sticker_groups)
            # Auch Lücken in E-Nummern-Sequenzen erkennen (für Gruppen ohne Count-Sticker-Daten)
            gap_missing = self._detect_missing_from_group_gaps(extracted_data, count_sticker_groups)
            for entry in gap_missing:
                if entry not in missing_entries:
                    missing_entries.append(entry)
            
            # Gestylter Dialog
            input_dlg = QDialog(dialog)
            input_dlg.setWindowTitle("Fehlende Sticker hinzufügen")
            input_dlg.setModal(True)
            input_dlg.setFixedWidth(520)
            input_dlg.setStyleSheet(create_dialog_stylesheet(theme))
            
            dlg_layout = QVBoxLayout(input_dlg)
            dlg_layout.setSpacing(10)
            dlg_layout.setContentsMargins(24, 20, 24, 20)
            
            input_bg = "#ffffff"
            input_fg = "#111111"
            input_border = "#b0b0b0"
            card_bg = "rgba(0,0,0,0.02)"
            card_border = "rgba(0,0,0,0.08)"
            
            # --- Abschnitt: Erkannte fehlende Sticker ---
            checkboxes = []
            if missing_entries:
                sec_label = QLabel(f"Erkannte fehlende Sticker ({len(missing_entries)}):")
                sec_label.setStyleSheet(f"color: {colors['fg']}; font-size: 13px; font-weight: 600; border: none;")
                dlg_layout.addWidget(sec_label)
                
                scroll = QScrollArea()
                scroll.setWidgetResizable(True)
                scroll.setMaximumHeight(min(len(missing_entries) * 36 + 16, 200))
                scroll.setStyleSheet(f"""
                    QScrollArea {{
                        background: transparent;
                        border: 1px solid {card_border};
                        border-radius: 6px;
                    }}
                """)
                scroll_w = QWidget()
                scroll_w.setStyleSheet("background: transparent;")
                scroll_lay = QVBoxLayout(scroll_w)
                scroll_lay.setSpacing(2)
                scroll_lay.setContentsMargins(6, 6, 6, 6)
                
                for entry in missing_entries:
                    cb = QCheckBox(entry)
                    cb.setChecked(True)
                    cb.setStyleSheet(f"""
                        QCheckBox {{
                            color: {colors['fg']};
                            font-size: 12px;
                            font-family: 'Consolas', 'Courier New', monospace;
                            padding: 4px 6px;
                            background: {card_bg};
                            border-radius: 4px;
                            border: none;
                        }}
                        QCheckBox::indicator {{
                            width: 14px; height: 14px;
                            border-radius: 3px;
                            border: 1.5px solid rgba(128,128,128,0.3);
                        }}
                        QCheckBox::indicator:checked {{
                            background: {colors['accent']};
                            border: 1.5px solid {colors['accent']};
                        }}
                        QCheckBox::indicator:hover {{
                            border: 1.5px solid {colors['accent']};
                        }}
                    """)
                    scroll_lay.addWidget(cb)
                    checkboxes.append((cb, entry))
                
                scroll_lay.addStretch()
                scroll.setWidget(scroll_w)
                dlg_layout.addWidget(scroll)
                
                # Trenner
                sep = QLabel("")
                sep.setFixedHeight(1)
                sep.setStyleSheet(f"background: {card_border}; border: none;")
                dlg_layout.addWidget(sep)
            
            # --- Abschnitt: Manuelle Eingabe ---
            man_label = QLabel("Manuell hinzufügen:")
            man_label.setStyleSheet(f"color: {colors['fg']}; font-size: 13px; font-weight: 600; border: none;")
            dlg_layout.addWidget(man_label)
            
            input_field = QLineEdit()
            input_field.setPlaceholderText("z.B. E1.ELEC.DP.XYZ")
            input_field.setReadOnly(False)
            input_field.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {input_bg};
                    color: {input_fg};
                    border: 1.5px solid {input_border};
                    border-radius: 6px;
                    padding: 8px 12px;
                    font-size: 13px;
                    font-family: 'Consolas', 'Courier New', monospace;
                    selection-background-color: {colors['accent']};
                    selection-color: white;
                }}
                QLineEdit:focus {{
                    border-color: {colors['accent']};
                }}
            """)
            dlg_layout.addWidget(input_field)
            
            # --- Buttons ---
            dlg_btns = QHBoxLayout()
            dlg_btns.addStretch()
            cancel_b = GlassGlowButton("Abbrechen")
            cancel_b.setFixedHeight(34)
            cancel_b.clicked.connect(input_dlg.reject)
            dlg_btns.addWidget(cancel_b)
            add_b = GlassGlowButton("  Hinzufügen")
            add_b.setFixedHeight(34)
            add_b.setIcon(qta.icon('ph.plus-circle', color='#374151'))
            add_b.setIconSize(QSize(15, 15))
            add_b.clicked.connect(input_dlg.accept)
            dlg_btns.addWidget(add_b)
            dlg_layout.addLayout(dlg_btns)
            
            input_field.returnPressed.connect(input_dlg.accept)
            if not missing_entries:
                input_field.setFocus()
            
            if input_dlg.exec() != QDialog.DialogCode.Accepted:
                return
            
            # Alle zu erstellenden Einträge sammeln
            entries_to_add = []
            
            # Aus Checkboxen
            for cb, entry in checkboxes:
                if cb.isChecked():
                    entries_to_add.append(entry)
            
            # Aus manuellem Feld
            manual_text = input_field.text().strip().upper()
            if manual_text:
                entries_to_add.append(manual_text)
            
            if not entries_to_add:
                return
            
            # Sticker erstellen und zur Tabelle hinzufügen
            import re as _re
            for entry_text in entries_to_add:
                match = _re.match(r'^([EPMC]\d+)\.(.+)$', entry_text, _re.IGNORECASE)
                if match:
                    energy_id = match.group(1).upper()
                    equipment = match.group(2)
                else:
                    energy_id = entry_text
                    equipment = ""
                
                prefix = energy_id[0] if energy_id else 'E'
                sym_map = {'P': 'PNEUMATIC', 'M': 'MECHANICAL', 'C': 'CHEMICAL'}
                symbol_type = sym_map.get(prefix, 'ELECTRICAL')
                
                new_sticker = {
                    'energy_id': energy_id,
                    'equipment': equipment,
                    'symbol_type': symbol_type,
                    'description': '',
                    '_created_from_count': True,
                }
                
                # Zur extracted_data hinzufügen
                extracted_data.append(new_sticker)
                orig_idx = len(extracted_data) - 1
                sticker_items.append((orig_idx, new_sticker))
                
                # Neue Zeile in Tabelle
                new_row = table.rowCount()
                table.setRowCount(new_row + 1)
                
                e_item = QTableWidgetItem(energy_id)
                sticker_pos = len(sticker_items) - 1
                e_item.setData(role_orig_idx, orig_idx)
                e_item.setData(role_sticker_pos, sticker_pos)
                table.setItem(new_row, 0, e_item)
                
                eq_item = QTableWidgetItem(equipment)
                eq_item.setData(role_orig_idx, orig_idx)
                eq_item.setData(role_sticker_pos, sticker_pos)
                table.setItem(new_row, 1, eq_item)
                
                d_item = QTableWidgetItem('')
                d_item.setData(role_orig_idx, orig_idx)
                d_item.setData(role_sticker_pos, sticker_pos)
                table.setItem(new_row, 2, d_item)
                
                combo = build_group_combo(0)
                table.setCellWidget(new_row, 3, combo)
                
                logger.info(f'Fehlender Sticker hinzugefuegt: {energy_id} / {equipment}')
            
            # Auto-Zuweisen neu ausführen, um die Sticker richtig einzuordnen
            auto_assign_groups()
        
        group_spin.valueChanged.connect(update_group_count)
        auto_btn.clicked.connect(auto_assign_groups)
        add_missing_btn.clicked.connect(add_missing_sticker)
        
        # Initial: Gruppierung initialisieren
        update_group_count()
        update_row_colors()
        
        # Automatisch zuweisen wenn Count-Sticker-Gruppen vorhanden
        if count_sticker_groups:
            auto_assign_groups()
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        button_layout.addStretch()
        
        cancel_btn = GlassGlowButton("Abbrechen")
        cancel_btn.setMinimumHeight(44)
        cancel_btn.setMinimumWidth(140)
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)
        
        ok_btn = GlassGlowButton("Übernehmen")
        ok_btn.setMinimumHeight(44)
        ok_btn.setMinimumWidth(160)
        ok_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(ok_btn)
        
        layout.addLayout(button_layout)
        
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None

        # Geaenderte Tabellenwerte ins Datenmodell uebernehmen.
        for row in range(table.rowCount()):
            energy_item = table.item(row, 0)
            if energy_item is None:
                continue

            orig_idx = energy_item.data(role_orig_idx)
            if not isinstance(orig_idx, int) or not (0 <= orig_idx < len(extracted_data)):
                continue

            equipment_item = table.item(row, 1)
            description_item = table.item(row, 2)

            energy_id = (energy_item.text() if energy_item else "").strip()
            equipment = (equipment_item.text() if equipment_item else "").strip()
            description = (description_item.text() if description_item else "").strip()

            extracted_data[orig_idx]["energy_id"] = energy_id
            extracted_data[orig_idx]["equipment"] = equipment
            extracted_data[orig_idx]["description"] = description

            # Symboltyp konsistent zur ggf. geaenderten Energy-ID halten.
            prefix = energy_id[:1].upper()
            symbol_map = {
                'P': 'PNEUMATIC',
                'M': 'MECHANICAL',
                'C': 'CHEMICAL',
                'E': 'ELECTRICAL',
            }
            if prefix in symbol_map:
                extracted_data[orig_idx]["symbol_type"] = symbol_map[prefix]
        
        # Ergebnis zusammenbauen: sticker_index -> group_name
        result = {}
        single_members = []  # (sticker_idx, equipment)

        # Erst Gruppen-Zuordnung sammeln (group_idx -> list of (sticker_idx, equipment))
        group_members = {}
        for row in range(table.rowCount()):
            energy_item = table.item(row, 0)
            combo = table.cellWidget(row, 3)
            if energy_item is None or combo is None:
                continue

            sticker_idx = energy_item.data(role_sticker_pos)
            if not isinstance(sticker_idx, int):
                continue

            eq_item = table.item(row, 1)
            eq_text = (eq_item.text() if eq_item else "").strip()

            group_idx = combo.currentIndex()
            if group_idx == 0:
                single_members.append((sticker_idx, eq_text))
            else:
                group_members.setdefault(group_idx, []).append((sticker_idx, eq_text))

        # Gruppenname aus gemeinsamem Equipment-Prefix ableiten
        def _common_prefix(strings):
            if not strings:
                return ""
            prefix = strings[0]
            for s in strings[1:]:
                while not s.startswith(prefix) and prefix:
                    # Am letzten Punkt oder Ende abschneiden
                    dot_pos = prefix.rfind(".")
                    if dot_pos > 0:
                        prefix = prefix[:dot_pos]
                    else:
                        prefix = ""
            return prefix.rstrip(".")

        # Gruppenname pro Gruppe bestimmen (erste Runde)
        group_name_map = {}
        for group_idx, members in group_members.items():
            equips = [eq for _, eq in members if eq]
            common = _common_prefix(equips)
            group_name_map[group_idx] = common if common else f"Gruppe {group_idx}"
        
        # Duplikate erkennen: wenn mehrere Gruppen denselben Namen hätten, Fallback auf "Gruppe N"
        name_counts = {}
        for name in group_name_map.values():
            name_counts[name] = name_counts.get(name, 0) + 1
        for group_idx in group_name_map:
            if name_counts[group_name_map[group_idx]] > 1:
                group_name_map[group_idx] = f"Gruppe {group_idx}"
        
        for group_idx, members in group_members.items():
            group_name = group_name_map[group_idx]
            for sticker_idx, _ in members:
                result[sticker_idx] = group_name
        
        # Single-Items: alle in eine gemeinsame Gruppe "Single LOTO Count"
        for sticker_idx, eq_text in single_members:
            result[sticker_idx] = "SINGLE_Single LOTO Count"
        
        return result

    def import_stickers_from_pdf(self):
        """Importiert Sticker aus einer PDF-Datei."""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QRadioButton, QButtonGroup
        from ui.glass_button import GlassGlowButton
        
        dialog = PDFImportDialog(self, sticker_config=self.sticker_service.generator.cfg)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Data is already extracted in the dialog
            extracted_data = dialog.extracted_data
            import_qr_path = getattr(dialog, "import_qr_path", None)
            count_sticker_groups = getattr(dialog, "count_sticker_groups", [])
            
            if count_sticker_groups:
                logger.info(f"PDF Import: {len(count_sticker_groups)} Count-Sticker-Gruppen erkannt: {count_sticker_groups}")
            
            # Fehlende Sticker erkennen und optional erstellen
            if count_sticker_groups and extracted_data:
                missing = self._detect_missing_stickers(extracted_data, count_sticker_groups)
                if missing:
                    selected = self._show_missing_stickers_dialog(missing)
                    if selected:
                        created = self._create_stickers_from_entries(extracted_data, selected)
                        logger.info(f"PDF Import: {created} fehlende Sticker erstellt")
            
            if not extracted_data:
                msg = self._create_styled_msgbox("Info", "Keine Daten zum Importieren gefunden.", QMessageBox.Icon.Warning)
                msg.exec()
                return

            # Frage nach Single/Multi LOTO Modus mit gestyltem Dialog
            
            mode_dialog = QDialog(self)
            mode_dialog.setWindowTitle("LOTO Modus wählen")
            mode_dialog.setModal(True)
            mode_dialog.setFixedWidth(450)
            
            # Theme-basiertes Styling
            theme = getattr(self, 'theme', Theme.LIGHT)
            colors = get_theme_colors(theme)
            text_color = colors["fg"]
            radio_accent = colors["accent"]
            mode_dialog.setStyleSheet(create_dialog_stylesheet(theme))
            
            layout = QVBoxLayout(mode_dialog)
            layout.setSpacing(15)
            layout.setContentsMargins(25, 20, 25, 20)
            
            # Titel
            title = QLabel("Welchen LOTO Modus möchten Sie verwenden?")
            title.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {text_color}; padding-bottom: 5px;")
            layout.addWidget(title)
            
            # Radio Buttons mit Phosphor Icons
            radio_layout = QVBoxLayout()
            radio_layout.setSpacing(10)
            
            button_group = QButtonGroup(mode_dialog)
            
            single_radio = QRadioButton("  Single LOTO")
            single_radio.setToolTip("Ein Count-Sticker pro LOTO-Point")
            single_radio.setIcon(qta.icon('ph.lock', color=text_color))
            single_radio.setIconSize(QSize(18, 18))
            
            multi_radio = QRadioButton("  Multi LOTO")
            multi_radio.setToolTip("Ein Count-Sticker für alle LOTO-Points")
            multi_radio.setIcon(qta.icon('ph.lock-open', color=text_color))
            multi_radio.setIconSize(QSize(18, 18))
            
            custom_radio = QRadioButton("  Selbstauswahl")
            custom_radio.setToolTip("Sticker manuell in Multi-LOTO Gruppen einteilen")
            custom_radio.setIcon(qta.icon('ph.wrench', color=text_color))
            custom_radio.setIconSize(QSize(18, 18))
            
            button_group.addButton(single_radio)
            button_group.addButton(multi_radio)
            button_group.addButton(custom_radio)
            
            # Setze Standard basierend auf aktueller Auswahl
            current_is_single = getattr(self, 'single_loto_radio', None) and self.single_loto_radio.isChecked()
            if current_is_single:
                single_radio.setChecked(True)
            else:
                multi_radio.setChecked(True)
            
            radio_style = f"""
                QRadioButton {{
                    color: {text_color};
                    font-size: 13px;
                    font-weight: 400;
                    spacing: 10px;
                    padding: 6px 12px;
                }}
                QRadioButton::indicator {{
                    width: 16px;
                    height: 16px;
                    border-radius: 8px;
                    border: 1.5px solid rgba(128, 128, 128, 0.3);
                    background: transparent;
                }}
                QRadioButton::indicator:hover {{
                    border: 1.5px solid {radio_accent};
                }}
                QRadioButton::indicator:checked {{
                    border: 1.5px solid {radio_accent};
                    background: qradialgradient(cx:0.5, cy:0.5, radius:0.5,
                        fx:0.5, fy:0.5,
                        stop:0 {radio_accent},
                        stop:0.4 {radio_accent},
                        stop:0.5 transparent,
                        stop:1 transparent);
                }}
            """
            single_radio.setStyleSheet(radio_style)
            multi_radio.setStyleSheet(radio_style)
            custom_radio.setStyleSheet(radio_style)

            radio_layout.addWidget(single_radio)
            radio_layout.addWidget(multi_radio)
            radio_layout.addWidget(custom_radio)
            layout.addLayout(radio_layout)
            
            layout.addSpacing(10)
            
            # Buttons
            button_layout = QHBoxLayout()
            button_layout.setSpacing(10)
            button_layout.addStretch()
            
            cancel_btn = GlassGlowButton("Abbrechen")
            cancel_btn.setMinimumHeight(44)
            cancel_btn.setMinimumWidth(140)
            cancel_btn.clicked.connect(mode_dialog.reject)
            button_layout.addWidget(cancel_btn)
            
            ok_btn = GlassGlowButton("Importieren")
            ok_btn.setMinimumHeight(44)
            ok_btn.setMinimumWidth(160)
            ok_btn.clicked.connect(mode_dialog.accept)
            button_layout.addWidget(ok_btn)
            
            layout.addLayout(button_layout)
            
            # Dialog ausführen
            if mode_dialog.exec() != QDialog.DialogCode.Accepted:
                return  # Abgebrochen
            
            # Modus bestimmen
            is_single_mode = single_radio.isChecked()
            is_multi_mode = multi_radio.isChecked()
            is_custom_mode = custom_radio.isChecked()
            
            # Bei Selbstauswahl: Gruppierungs-Dialog anzeigen
            custom_groups = None
            if is_custom_mode:
                custom_groups = self._show_loto_grouping_dialog(extracted_data, count_sticker_groups)
                if custom_groups is None:
                    return  # Abgebrochen

            # Mapping fuer spaetere Uebergabe an Equipment-Import: extracted_data-index -> Gruppenname
            custom_group_by_extracted_index = {}
            if is_custom_mode and custom_groups:
                filtered_indices = [idx for idx, d in enumerate(extracted_data) if not d.get("is_separator")]
                for sticker_pos, group_name in custom_groups.items():
                    if isinstance(sticker_pos, int) and 0 <= sticker_pos < len(filtered_indices):
                        custom_group_by_extracted_index[filtered_indices[sticker_pos]] = group_name
                logger.info(f"custom_group_by_extracted_index: {len(custom_group_by_extracted_index)} Eintraege, "
                           f"custom_groups: {len(custom_groups)} Eintraege, "
                           f"filtered_indices: {len(filtered_indices)} Eintraege")

            imported_count = 0
            
            # Use embedded progress bar from Magic Menu
            progress_bar = None
            if hasattr(self, 'magic_menu'):
                progress_bar = self.magic_menu.progress_bar
                progress_bar.setRange(0, len(extracted_data))
                progress_bar.setValue(0)
                progress_bar.setVisible(True)
            
            # PDF-Import: Neuen Generator mit QR aus PDF (falls gefunden)
            from generators.sticker_generator import StickerGenerator
            from core.models import StickerConfig
            
            # Komplett neue Config ohne QR erstellen (nicht replace, sondern neue Instanz)
            orig_cfg = self.sticker_service.generator.cfg
            import_cfg = StickerConfig(
                width_mm=orig_cfg.width_mm,
                height_mm=orig_cfg.height_mm,
                dpi=orig_cfg.dpi,
                corner_radius=orig_cfg.corner_radius,
                outline_width=orig_cfg.outline_width,
                font_path=orig_cfg.font_path,
                auto_adjust=orig_cfg.auto_adjust,
                sticker_color=orig_cfg.sticker_color,
                font_size_mm=orig_cfg.font_size_mm,
                line_height_mm=orig_cfg.line_height_mm,
                symbols_dir=orig_cfg.symbols_dir,
                symbol_corner_radius=orig_cfg.symbol_corner_radius,
                symbol_size_mm=orig_cfg.symbol_size_mm,
                symbol_offset_x_mm=orig_cfg.symbol_offset_x_mm,
                symbol_offset_y_mm=orig_cfg.symbol_offset_y_mm,
                text_offset_x=orig_cfg.text_offset_x,
                text_offset_y=orig_cfg.text_offset_y,
                qr_mode_enabled=bool(import_qr_path),
                qr_placeholder_text="QR",
                qr_placeholder_bg="#FFFFFF",
                qr_image_path=import_qr_path,
                preview_scale=orig_cfg.preview_scale,
                export_exact_three_rows=orig_cfg.export_exact_three_rows,
                export_margin_mm=orig_cfg.export_margin_mm,
                export_gap_mm=orig_cfg.export_gap_mm,
                export_min_scale=orig_cfg.export_min_scale
            )
            
            # Neuen Generator für Import erstellen
            import_generator = StickerGenerator(import_cfg)
            import_generator._qr_cache.clear()  # Cache leeren
            logger.info(f"PDF Import: qr_mode_enabled={import_cfg.qr_mode_enabled}, qr_image_path={import_cfg.qr_image_path}")
            
            # WICHTIG: Setze QR auch für den Haupt-Generator, damit Vorschau funktioniert
            if import_qr_path:
                logger.info(f"Setze QR auch für Haupt-Generator: {import_qr_path}")
                self.sticker_service.generator.cfg.qr_mode_enabled = True
                self.sticker_service.generator.cfg.qr_image_path = import_qr_path
                # Cache leeren, damit der neue QR geladen wird
                self.sticker_service.generator._qr_cache.clear()
            
            try:
                for i, data in enumerate(extracted_data):
                    if data.get("is_separator"):
                        if progress_bar: progress_bar.setValue(i + 1)
                        continue

                    # Bei Selbstauswahl: gelöschte Zeilen überspringen
                    if is_custom_mode and custom_group_by_extracted_index and i not in custom_group_by_extracted_index:
                        if progress_bar: progress_bar.setValue(i + 1)
                        continue
                        
                    energy_id = data.get("energy_id", "UNKNOWN")
                    equipment = data.get("equipment", "Imported")
                    description = data.get("description", "")
                    symbol_type = data.get("symbol_type", "ELECTRICAL")
                    sticker_qr_path = data.get("qr_path", "") or import_qr_path or ""  # Individueller QR pro Sticker
                    
                    # Generate sticker image mit Import-Generator
                    try:
                        # Individuellen QR-Pfad für diesen Sticker setzen
                        if sticker_qr_path:
                            import_cfg.qr_mode_enabled = True
                            import_cfg.qr_image_path = sticker_qr_path
                        else:
                            import_cfg.qr_mode_enabled = False
                            import_cfg.qr_image_path = None
                        import_generator._qr_cache.clear()
                        import_generator._img_cache.clear()

                        # Symbol-Typ ermitteln
                        from core.models import SymbolType
                        sym_type = SymbolType.ELECTRICAL
                        try:
                            sym_type = SymbolType[symbol_type.upper()]
                        except (KeyError, AttributeError):
                            sym_type = SymbolType.ELECTRICAL
                        
                        lines = [energy_id, equipment]
                        if description:
                            lines.append(description)
                        
                        # Direkt mit Import-Generator generieren
                        image = import_generator.generate(sym_type, lines)
                        logger.info(f"Sticker generiert für {energy_id}: QR-Mode={import_cfg.qr_mode_enabled}, QR-Path={import_cfg.qr_image_path}")
                        
                        # Add to collection service
                        self.collection_service.add_item(
                            energy_id=energy_id,
                            equipment=equipment,
                            symbol_type=symbol_type,
                            description=description,
                            image=image
                        )
                        
                        # Add to legacy collection list (required for UI update)
                        custom_group = custom_group_by_extracted_index.get(i, "")
                        # SINGLE_-Prefix nur intern für Count-Sticker-Logik, nicht für Equipment-Manager
                        equipment_group = custom_group.replace("SINGLE_", "") if custom_group.startswith("SINGLE_") else custom_group
                        full_info = {
                            "text": f"{energy_id} {equipment} {description}".strip(),
                            "qr_path": sticker_qr_path,  # Individueller QR-Pfad pro Sticker!
                            "group": equipment_group,
                        }
                        self._add_to_collection_with_thumbnail(
                            image,
                            symbol_type,
                            energy_id,
                            equipment,
                            description,
                            full_info
                        )

                        # Bei Single LOTO: Count Sticker pro Item hinzufügen
                        if is_single_mode:
                            try:
                                count_detail = full_info.get("text", f"{energy_id} {equipment} {description}".strip())
                                count_img = self.count_generator.generate(count_detail, 1)
                                self.collection.append([count_img, "COUNT_SINGLE", f"C_{energy_id}", "", count_detail, "count_single", count_img])
                            except Exception as e:
                                logger.warning(f"Count Sticker konnte nicht generiert werden (PDF Import): {e}")
                        
                        imported_count += 1
                    except Exception as e:
                        logger.error(f"Error generating sticker for {energy_id}: {e}")
                    
                    if progress_bar:
                        progress_bar.setValue(i + 1)
                    QApplication.processEvents()
                
                if progress_bar:
                    progress_bar.setVisible(False)
                
                if imported_count > 0:
                    # Bei Multi-LOTO Modus: Count-Sticker per Gruppe hinzufügen
                    if is_multi_mode:
                        try:
                            self._regenerate_multi_count_sticker()
                        except Exception as e:
                            logger.warning(f"Multi Count Sticker konnte nicht erstellt werden: {e}")
                    
                    # Bei Selbstauswahl: Count-Sticker pro Gruppe
                    if is_custom_mode and custom_groups:
                        try:
                            # Entferne alte Count Sticker
                            i = len(self.collection) - 1
                            while i >= 0:
                                item = self.collection[i]
                                if self._is_count_multi(item) or self._is_count_single(item):
                                    self.collection.pop(i)
                                i -= 1
                            
                            # Baue Gruppen-Zuordnung: group_name -> [sticker indices]
                            # custom_groups ist dict: row_index (in sticker_items) -> group_name
                            groups = {}
                            for idx, group_name in custom_groups.items():
                                if group_name not in groups:
                                    groups[group_name] = []
                                groups[group_name].append(idx)
                            
                            # Filtere sticker_items (ohne Separatoren) für den Zugriff
                            filtered_sticker_items = [(i, d) for i, d in enumerate(extracted_data) if not d.get("is_separator")]
                            
                            # Für jede Gruppe einen Count-Sticker generieren
                            for group_name, sticker_indices in sorted(groups.items()):
                                group_details = []
                                for idx in sticker_indices:
                                    if idx < len(filtered_sticker_items):
                                        _, data_item = filtered_sticker_items[idx]
                                        item_energy = data_item.get("energy_id", "")
                                        item_equipment = data_item.get("equipment", "")
                                        item_description = data_item.get("description", "")
                                        detail = f"{item_energy} {item_equipment} {item_description}".strip()
                                        if detail:
                                            group_details.append(detail)
                                
                                if group_details:
                                    import re as _re_sort
                                    group_details.sort(key=lambda s: [int(t) if t.isdigit() else t.lower() for t in _re_sort.split(r'(\d+)', s)])
                                    group_count = len(group_details)
                                    detail_str = ', '.join(group_details)
                                    
                                    if group_name.startswith("SINGLE_"):
                                        # Single LOTO: Ein Count-Sticker PRO Item
                                        for detail in group_details:
                                            first_energy = detail.split()[0] if detail else "UNKNOWN"
                                            logger.info(f"Custom Single Count für '{first_energy}': {detail[:80]}")
                                            count_img = self.count_generator.generate(detail, 1)
                                            self.collection.append([
                                                count_img, "COUNT_SINGLE", f"C_{first_energy}", "", detail,
                                                {"type": "count_single", "copies": 1}, count_img
                                            ])
                                    else:
                                        # Multi-LOTO Gruppe
                                        logger.info(f"Custom Group '{group_name}': {group_count} Items, Details: {detail_str[:100]}...")
                                        count_img = self.count_generator.generate(detail_str, group_count)
                                        self.collection.append([
                                            count_img, "COUNT_MULTI", f"TOTAL_{group_name}", "", "",
                                            {"type": "count_multi", "details": detail_str, "group": group_name},
                                            count_img
                                        ])
                        except Exception as e:
                            logger.warning(f"Custom Group Count Sticker konnte nicht erstellt werden: {e}")

                    self.update_collection_list() # Ensure UI is updated

            except Exception as e:
                logger.error(f"PDF Import fehlgeschlagen: {e}")
                msg = self._create_styled_msgbox("Fehler", f"PDF-Import fehlgeschlagen:\n{e}", QMessageBox.Icon.Critical)
                msg.exec()
            finally:
                if hasattr(dialog, "cleanup_temp_files"):
                    dialog.cleanup_temp_files()
                if progress_bar:
                    progress_bar.setVisible(False)


    def _serialize_current_sticker_config(self) -> dict:
        """Serialisiert die aktuelle Sticker-Konfiguration zu einem Dict."""
        cfg = self.sticker_service.generator.cfg
        count_cfg = self.count_config
        
        return {
            # LOTO Sticker Config
            "width_mm": cfg.width_mm,
            "height_mm": cfg.height_mm,
            "dpi": cfg.dpi,
            "corner_radius": cfg.corner_radius,
            "outline_width": cfg.outline_width,
            "font_path": cfg.font_path,
            "auto_adjust": cfg.auto_adjust,
            "sticker_color": cfg.sticker_color,
            "font_size_mm": cfg.font_size_mm,
            "line_height_mm": cfg.line_height_mm,
            "symbol_corner_radius": cfg.symbol_corner_radius,
            "symbol_size_mm": cfg.symbol_size_mm,
            "symbol_offset_x_mm": cfg.symbol_offset_x_mm,
            "symbol_offset_y_mm": cfg.symbol_offset_y_mm,
            "text_offset_x": cfg.text_offset_x,
            "text_offset_y": cfg.text_offset_y,
            "qr_mode_enabled": cfg.qr_mode_enabled,
            "qr_placeholder_text": cfg.qr_placeholder_text,
            "qr_placeholder_bg": cfg.qr_placeholder_bg,
            "qr_image_path": cfg.qr_image_path,
            "preview_scale": cfg.preview_scale,
            "export_exact_three_rows": cfg.export_exact_three_rows,
            "export_margin_mm": cfg.export_margin_mm,
            "export_gap_mm": cfg.export_gap_mm,
            "export_min_scale": cfg.export_min_scale,
            "loto_mode_single": getattr(self, 'single_loto_radio', None) and self.single_loto_radio.isChecked(),
            
            # Count Sticker Config
            "count_width_mm": count_cfg.width_mm,
            "count_height_mm": count_cfg.height_mm,
            "count_dpi": count_cfg.dpi,
            "count_corner_radius": count_cfg.corner_radius,
            "count_outline_width": count_cfg.outline_width,
            "count_font_path": count_cfg.font_path,
            "count_auto_adjust": count_cfg.auto_adjust,
            "count_font_size_mm": count_cfg.font_size_mm,
            "count_line_height_mm": count_cfg.line_height_mm,
            "count_header_text": count_cfg.header_text,
            "count_bg_color": count_cfg.bg_color,
            "count_stripe_color": count_cfg.stripe_color,
            "count_show_stripes": count_cfg.show_stripes,
            "count_header_margin_mm": count_cfg.header_margin_mm,
            "count_text_spacing_mm": count_cfg.text_spacing_mm
        }

    def _sync_settings_to_equipment_manager(self):
        """Schreibt die aktuelle Sticker-/Count-Config zurück in den Equipment-Manager
        für alle Items, die aus dem Equipment-Manager in der Collection geladen wurden."""
        try:
            if not hasattr(self, 'equipment_service'):
                return
            equipment_manager = self.equipment_service.get_manager()
            if not equipment_manager:
                return

            sticker_config = self._serialize_current_sticker_config()
            updated_count = 0

            for item in getattr(self, 'collection', []):
                if self._is_count_single(item) or self._is_count_multi(item):
                    continue
                if len(item) < 6:
                    continue

                full_info = item[5] if isinstance(item[5], dict) else {}
                location = full_info.get("location", "")
                system = full_info.get("system", "")
                if not location or not system:
                    continue

                energy_id = item[2] if len(item) > 2 else ""
                equipment_name = item[3] if len(item) > 3 else ""
                if not equipment_name:
                    continue

                updated = equipment_manager.update_equipment_properties(
                    location, system, equipment_name,
                    sticker_config=sticker_config,
                    match_energy_id=energy_id if energy_id else None
                )
                if updated:
                    updated_count += 1

            if updated_count > 0:
                equipment_manager.save_equipment()
                if hasattr(self, 'equipment_controller'):
                    self.equipment_controller.refresh_tree()
                logger.info(f"Sticker-Config für {updated_count} Equipment(s) im Equipment-Manager aktualisiert")
                if self.status_bar:
                    self.status_bar.showMessage(
                        f"Einstellungen für {updated_count} Equipment(s) übernommen", 3000
                    )
        except Exception as e:
            logger.error(f"Fehler beim Sync der Einstellungen zum Equipment-Manager: {e}")

    def import_collection_to_equipment_manager(self):
        """Übernimmt Sticker aus der Ablage in den Equipment-Manager (mit Abfrage)."""
        if not hasattr(self, 'equipment_service'):
            return

        # Sammle nur LOTO-Sticker (keine Count-Sticker)
        items = []
        for item in getattr(self, 'collection', []):
            if self._is_count_single(item) or self._is_count_multi(item):
                continue
            if len(item) >= 5:
                # full_info kann String oder Dict sein
                full_info = item[5] if len(item) > 5 else {}
                qr_path = ""
                group_name = ""
                if isinstance(full_info, dict):
                    qr_path = full_info.get("qr_path", "")
                    group_name = full_info.get("group", "")
                logger.info(f"DEBUG import_collection: full_info={full_info}, qr_path={qr_path}")
                
                # Aktuelle Sticker-Config serialisieren
                sticker_config = self._serialize_current_sticker_config()
                
                items.append({
                    "energy_id": item[2],
                    "equipment": item[3],
                    "description": item[4],
                    "symbol_type": item[1],
                    "qr_path": qr_path,
                    "sticker_config": sticker_config,
                    "group": group_name,
                })

        if not items:
            msg = self._create_styled_msgbox("Info", "Keine LOTO-Sticker in der Ablage gefunden.", QMessageBox.Icon.Information)
            msg.exec()
            return

        dialog = EquipmentImportDialog(self, items, self.equipment_service.get_manager())
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        selected_items = dialog.selected_items
        if not selected_items:
            return

        equipment_manager = self.equipment_service.get_manager()
        imported = 0
        import re

        def _normalize_equipment_name(name: str) -> str:
            """Entfernt alle Energy-ID Suffixe [Exx] aus dem Namen.
            Die Energy-ID wird separat im energy_id Feld gespeichert."""
            base = name.strip()
            # Entferne alle energy-id tokens [Exx] aus dem Namen
            base = re.sub(r"\s*\[E\d+\]\s*", " ", base, flags=re.IGNORECASE).strip()
            return base

        for it in selected_items:
            try:
                location = it["location"]
                system = it["system"]
                equipment_name = it.get("equipment", "").strip()
                energy_id = it.get("energy_id", "").strip()
                symbol_type = it.get("symbol_type", "").strip()
                description = it.get("description", "").strip()
                # Normalize name: entferne Energy-ID aus dem Namen (wird separat gespeichert)
                if equipment_name:
                    equipment_name = _normalize_equipment_name(equipment_name)
                    # Description zum Namen hinzufügen wenn vorhanden
                    if description:
                        equipment_name = f"{equipment_name} - {description}"
                if not equipment_name:
                    equipment_name = energy_id
                if not equipment_name:
                    continue

                qr_path = it.get("qr_path", "")
                sticker_config = it.get("sticker_config", {})
                logger.debug(f"Füge Equipment hinzu: name={equipment_name}, qr_path={qr_path}")
                added = equipment_manager.add_equipment(
                    location, system, equipment_name,
                    energy_id=energy_id,
                    symbol_type=symbol_type,
                    description="",  # Description ist bereits im Namen
                    qr_path=qr_path,
                    sticker_config=sticker_config
                )

                if added:
                    imported += 1
                else:
                    # Equipment mit Name+Energy-ID existiert bereits, aktualisiere Eigenschaften
                    updated = equipment_manager.update_equipment_properties(
                        location, system, equipment_name,
                        symbol_type=symbol_type,
                        description="",  # Description ist bereits im Namen
                        qr_path=qr_path,
                        sticker_config=sticker_config,
                        match_energy_id=energy_id
                    )
                    if updated:
                        imported += 1
            except Exception:
                continue

        if imported > 0:
            self.equipment_service.save()
            if hasattr(self, 'equipment_controller'):
                self.equipment_controller.refresh_tree()
            if self.status_bar:
                self.status_bar.showMessage(f"{imported} Einträge in Equipment übernommen", 3000)
            msg = self._create_styled_msgbox(
                "Gespeichert",
                f"{imported} Einträge wurden in den Equipment‑Manager übernommen.",
                QMessageBox.Icon.Information
            )
            msg.exec()
        else:
            msg = self._create_styled_msgbox(
                "Hinweis",
                "Keine Einträge übernommen.",
                QMessageBox.Icon.Warning
            )
            msg.exec()

    def sort_collection_by_energy_id(self):
        """Sortiert die Sammlung nach Energie-ID (E1, E2, E3, ...)"""
        import re
        from PyQt6.QtWidgets import QMessageBox

        if not hasattr(self, "collection") or not self.collection:
            msg = self._create_styled_msgbox("Hinweis", "Keine Sticker in der Sammlung!", QMessageBox.Icon.Warning)
            msg.exec()
            return

        # Trenne reguläre Items und Count-Items
        regular = []
        counts = []
        for item in self.collection:
            if self._is_count_single(item) or self._is_count_multi(item):
                counts.append(item)
            else:
                regular.append(item)

        # Sortiere reguläre Items numerisch nach Energie-ID
        def get_energy_key(item):
            if len(item) < 3:
                return (float("inf"), "")
            eid = str(item[2]).upper()
            m = re.search(r"E(\d+)", eid)
            return (int(m.group(1)), eid) if m else (float("inf"), eid)

        regular.sort(key=get_energy_key)

        # Zusammenführen
        self.collection = regular + counts
        self._manual_sort_mode = "energy_id"

        # UI aktualisieren - Count-Sticker regenerieren wenn vorhanden
        has_count_sticker = any(self._is_count_multi(it) for it in counts)
        if has_count_sticker:
            self._regenerate_multi_count_sticker()
        else:
            self.update_collection_list(skip_sort=True)

        if self.status_bar:
            self.status_bar.showMessage(f"Nach Energie-ID sortiert ({len(regular)} Sticker)", 3000)

    def _regenerate_multi_count_sticker(self):
        """Regeneriert Multi-LOTO Count-Sticker nach Änderungen — ein Count-Sticker pro Gruppe"""
        try:
            # Merke ob Count-Sticker aktuell ausgewählt ist
            current_row = self.collection_list.currentRow()
            was_count_selected = False
            if current_row >= 0 and current_row < len(self.collection):
                item = self.collection[current_row]
                was_count_selected = self._is_count_multi(item)
            
            # 1. Merke pro-Gruppe Kopienanzahl, bevor alte Count-Multi Sticker entfernt werden
            old_copies_per_group = {}
            for item in self.collection:
                if self._is_count_multi(item) and len(item) > 5 and isinstance(item[5], dict):
                    grp = item[5].get("group", "")
                    old_copies_per_group[grp] = item[5].get("copies", 1)
            
            # 2. Entferne ALLE alten Count-Multi Sticker
            i = len(self.collection) - 1
            while i >= 0:
                item = self.collection[i]
                if self._is_count_multi(item):
                    self.collection.pop(i)
                    logger.info(f"_regenerate: Entferne alten Count-Multi Sticker an Index {i}")
                i -= 1
            
            # 2. Sammle reguläre Items und gruppiere nach full_info["group"]
            from collections import OrderedDict
            groups = OrderedDict()  # group_name -> [items]
            for item in self.collection:
                if self._is_count_single(item) or self._is_count_multi(item):
                    continue
                if len(item) < 5:
                    continue
                full_info = item[5] if len(item) > 5 else {}
                group_name = ""
                if isinstance(full_info, dict):
                    group_name = full_info.get("group", "")
                if group_name not in groups:
                    groups[group_name] = []
                groups[group_name].append(item)
            
            logger.info(f"_regenerate: {len(groups)} Gruppe(n) gefunden: {list(groups.keys())}")
            
            # 3. Für jede Gruppe einen Count-Sticker generieren
            for group_name, group_items in groups.items():
                count = len(group_items)
                if count == 0:
                    continue
                
                details = []
                for item in group_items:
                    item_energy = item[2]
                    item_equipment = item[3]
                    item_description = item[4]
                    
                    if isinstance(item_description, dict):
                        item_description = item_description.get("text", "")
                    
                    if not item_description and len(item) > 5:
                        fi = item[5]
                        if isinstance(fi, dict) and "text" in fi:
                            full_text = fi.get("text", "")
                            parts = full_text.split()
                            if len(parts) > 2:
                                item_description = " ".join(parts[2:])
                    
                    if item_energy.startswith("C_"):
                        item_energy = item_energy[2:]
                    detail = f"{item_energy} {item_equipment} {item_description}".strip()
                    if detail:
                        details.append(detail)
                
                import re as _re_sort
                details.sort(key=lambda s: [int(t) if t.isdigit() else t.lower() for t in _re_sort.split(r'(\d+)', s)])
                detail_str = ', '.join(details) if details else "LOTO Points"
                
                logger.info(f"Regenerate Count-Sticker für Gruppe '{group_name}': {count} Items")
                
                count_copies_default = max(1, int(getattr(getattr(self, 'count_config', None), 'count_print_copies', 1)))
                # Nutze benutzerdefinierte Kopienanzahl falls vorhanden, sonst Einstellung
                copies = old_copies_per_group.get(group_name, count_copies_default)
                count_img = self.count_generator.generate(detail_str, count)
                self.collection.append([
                    count_img, "COUNT_MULTI", "TOTAL", "", "",
                    {"type": "count_multi", "group": group_name, "details": detail_str, "copies": copies},
                    count_img
                ])
            
            # 4. UI aktualisieren
            self.update_collection_list()
            
            # 5. Wenn Count-Sticker vorher ausgewählt war, Vorschau aktualisieren
            if was_count_selected:
                new_count_row = len(self.collection) - 1
                self.collection_list.setCurrentRow(new_count_row)
        except Exception as e:
            logger.warning(f"Count-Sticker konnte nicht aktualisiert werden: {e}")

    def move_item_up(self):
        """Gewähltes Element in der Sammlung nach oben verschieben"""
        current_row = self.collection_list.currentRow()
        if current_row <= 0:
            msg = self._create_styled_msgbox("Info", "Element ist bereits an der ersten Position oder nichts gewählt", QMessageBox.Icon.Information)
            msg.exec()
            return
        
        # Tausche in der collection Liste
        self.collection[current_row], self.collection[current_row - 1] = \
            self.collection[current_row - 1], self.collection[current_row]
        
        # Aktualisiere UI
        self.update_collection_list()
        self.collection_list.setCurrentRow(current_row - 1)
        if self.status_bar:
            self.status_bar.showMessage("Element nach oben verschoben", 2000)

    def move_item_down(self):
        """Gewähltes Element in der Sammlung nach unten verschieben"""
        current_row = self.collection_list.currentRow()
        if current_row < 0 or current_row >= len(self.collection) - 1:
            msg = self._create_styled_msgbox("Info", "Element ist bereits an der letzten Position oder nichts gewählt", QMessageBox.Icon.Information)
            msg.exec()
            return
        
        # Tausche in der collection Liste
        self.collection[current_row], self.collection[current_row + 1] = \
            self.collection[current_row + 1], self.collection[current_row]
        
        # Aktualisiere UI
        self.update_collection_list()
        self.collection_list.setCurrentRow(current_row + 1)
        if self.status_bar:
            self.status_bar.showMessage("Element nach unten verschoben", 2000)

    def delete_selected_items(self):
        """Gewählte Elemente aus der Sammlung löschen"""
        selected_items = self.collection_list.selectedItems()
        if not selected_items:
            msg = self._create_styled_msgbox("Info", "Keine Elemente gewählt", QMessageBox.Icon.Information)
            msg.exec()
            return
        
        # Hole die Indizes der gewählten Elemente
        selected_rows = []
        for item in selected_items:
            row = self.collection_list.row(item)
            if row >= 0:
                selected_rows.append(row)
        
        if not selected_rows:
            return
            
        msg = self._create_styled_msgbox(
            "Bestätigung",
            f"{len(selected_rows)} Element(e) löschen?",
            QMessageBox.Icon.Question,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        reply = msg.exec()
        
        if reply == QMessageBox.StandardButton.Yes:
            # Lösche von hinten nach vorne, damit Indizes stimmen
            for row in sorted(selected_rows, reverse=True):
                if 0 <= row < len(self.collection):
                    del self.collection[row]
            
            self.update_collection_list()
            if self.status_bar:
                self.status_bar.showMessage(f"{len(selected_rows)} Element(e) gelöscht", 2000)

    def _apply_theme_styles(self):
        """Wendet Theme-Styles auf das Hauptfenster an."""
        custom_colors = getattr(self.theme_config, 'custom_colors', {}) if hasattr(self, 'theme_config') else {}
        colors = get_theme_colors(Theme.LIGHT, custom_colors)
        tooltip_bg = "#1f2937"  # Dunkelgrau für besseren Kontrast
        tooltip_fg = "#ffffff"  # Weißer Text
        text_color = "#1a1a1a"
        border_color = "#e0e0e0"
        
        # Check if custom background color is set
        bg_style = f"background-color: {colors['bg']};"

        # Tab colors für Light Mode
        tab_bg = "rgba(255, 255, 255, 150)"
        tab_selected_bg = "rgba(255, 255, 255, 240)"
        tab_hover_bg = "rgba(255, 255, 255, 200)"

        self.setStyleSheet(f"""
            QMainWindow {{
                {bg_style}
                color: {colors['fg']};
            }}
            QWidget {{
                color: {colors['fg']};
                background-color: transparent;
            }}
            QLabel {{
                color: {colors['fg']};
            }}
            QMenuBar {{
                background-color: {colors['bg']};
                color: {colors['fg']};
                border-bottom: 1px solid {colors['border']};
                padding: 2px 4px;
                min-height: 40px;
            }}
            QMenuBar::item {{
                background-color: transparent;
                padding: 4px 10px;
                border-radius: 4px;
            }}
            QMenuBar::item:selected {{
                background-color: {colors['hover']};
            }}
            QMenuBar::item:pressed {{
                background-color: {colors['accent']};
                color: #ffffff;
            }}
            QMenu {{
                background-color: {colors['input_bg']};
                color: {colors['fg']};
                border: 1px solid {colors['border']};
                padding: 5px;
            }}
            QMenu::item {{
                padding: 5px 20px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {colors['accent']};
                color: #ffffff;
            }}
            QStatusBar {{
                background-color: {colors['bg']};
                color: {colors['fg']};
                border-top: 1px solid {colors['border']};
            }}
            QTabWidget {{
                background-color: transparent;
            }}
            QTabWidget::pane {{
                border: none;
                background-color: transparent;
            }}
            QTabBar::tab {{
                background-color: {tab_bg};
                color: {colors['fg']};
                padding: 10px 20px;
                border: 1px solid {colors['border']};
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 4px;
            }}
            QTabBar::tab:selected {{
                background-color: {tab_selected_bg};
                border-bottom: 1px solid transparent;
                font-weight: bold;
            }}
            QTabBar::tab:hover {{
                background-color: {tab_hover_bg};
            }}
            QToolTip {{
                color: {tooltip_fg};
                background-color: {tooltip_bg};
                border: 1px solid {colors['border']};
                padding: 6px 10px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 600;
            }}
        """)


    
    def _select_equipment(self):
        """Equipment-Auswahl-Dialog öffnen"""
        dialog = EquipmentSelectionDialog(self, self.equipment_manager, Theme.LIGHT)
        dialog.setWindowTitle("Ziel-System auswählen")
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_data:
            data = dialog.selected_data
            
            # Equipment Name
            if hasattr(self, 'equipment_entry') and self.equipment_entry:
                self.equipment_entry.setText(data.get('equipment_name', ''))
            
            # Energy ID
            if hasattr(self, 'energy_entry') and self.energy_entry and data.get('energy_id'):
                self.energy_entry.setText(data.get('energy_id'))
            
            # Description -> MAIN SWITCH
            if hasattr(self, 'description_entry') and self.description_entry:
                self.description_entry.setText("MAIN SWITCH")
            
            # Symbol Type
            symbol_type = data.get('symbol_type', '')
            if hasattr(self, 'symbol_combo') and self.symbol_combo and symbol_type:
                symbol_name = symbol_type.capitalize()
                index = self.symbol_combo.findText(symbol_name)
                if index >= 0:
                    self.symbol_combo.setCurrentIndex(index)


if __name__ == '__main__':
    import sys
    import time
    import random
    import math
    app = QApplication(sys.argv)
    
    # Setze globale Light Palette - deaktiviere Windows Dark Mode für diese App
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
    app.setStyle("Fusion")  # Verwende Fusion Style für konsistente mit Palette
    
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
                
                # Canvas Größe
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
                
                # Partikel extrahieren (weniger für Performance)
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
                
                # Weniger Partikel für bessere Performance
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
                            
                            # Startposition außerhalb
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
