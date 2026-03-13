"""Helper zum Erstellen der Hauptmenueleiste."""

import datetime
import logging

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QSizePolicy
from PyQt6.QtGui import QAction

from ui.glass_button import GlassGlowButton

logger = logging.getLogger(__name__)


def build_main_menu(app) -> None:
    """Erstellt die Menueleiste fuer das Hauptfenster."""
    try:
        menubar = app.menuBar()
        if menubar is None:
            return

        # Menue leeren, falls es bereits existiert (verhindert Dopplungen)
        menubar.clear()

        # Datei-Menue
        file_menu = menubar.addMenu("&Datei")
        if file_menu:
            new_action = QAction("&Neu", app)
            new_action.triggered.connect(app._new_project)
            new_action.setShortcut("Ctrl+N")
            file_menu.addAction(new_action)

            file_menu.addSeparator()

            logout_action = QAction("&Abmelden", app)
            logout_action.triggered.connect(app.logout)
            file_menu.addAction(logout_action)

            file_menu.addSeparator()

            exit_action = QAction("&Beenden", app)
            exit_action.triggered.connect(app.close)
            exit_action.setShortcut("Ctrl+Q")
            file_menu.addAction(exit_action)

        # Bearbeiten-Menue
        edit_menu = menubar.addMenu("&Bearbeiten")
        if edit_menu:
            settings_action = QAction("&Sticker-Einstellungen", app)
            settings_action.triggered.connect(app.open_sticker_settings)
            settings_action.setShortcut("Ctrl+S")
            edit_menu.addAction(settings_action)

            count_settings_action = QAction("&Count-Einstellungen", app)
            count_settings_action.triggered.connect(app.open_count_settings)
            edit_menu.addAction(count_settings_action)

        # Lizenz-Info im Menue (rechts)
        if hasattr(app, 'license_manager'):
            is_valid, _msg, expiry = app.license_manager.check_license()
            if is_valid and expiry:
                license_widget = QWidget()
                license_widget.setFixedHeight(36)
                license_widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
                l_layout = QHBoxLayout(license_widget)
                l_layout.setContentsMargins(0, 0, 12, 0)
                l_layout.setSpacing(6)

                icon = QLabel("🔐")
                icon.setStyleSheet("font-size: 14px;")
                l_layout.addWidget(icon)

                days_left = (expiry - datetime.datetime.now()).days
                info_text = f"Lizenz aktiv: {days_left} Tage"
                color = "#27ae60" if days_left > 30 else "#e74c3c"

                lbl = QLabel(info_text)
                lbl.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 12px;")
                l_layout.addWidget(lbl)

                logout_btn = GlassGlowButton("Abmelden")
                logout_btn.setFixedHeight(34)
                logout_btn.clicked.connect(app.logout)
                l_layout.addWidget(logout_btn)

                license_widget.adjustSize()
                license_widget.setToolTip(f"Gueltig bis: {expiry.strftime('%d.%m.%Y')}")
                menubar.setCornerWidget(license_widget, Qt.Corner.TopRightCorner)

    except Exception as e:
        logger.error(f"Menue-Erstellung fehlgeschlagen: {e}")
