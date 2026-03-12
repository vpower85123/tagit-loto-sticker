"""
Utilities und Helper für UI-Komponenten.
"""

from PyQt6.QtWidgets import QMessageBox


def show_info(parent, title: str, message: str):
    """Zeige Info-Dialog."""
    if parent is not None and hasattr(parent, "_create_styled_msgbox"):
        msg = parent._create_styled_msgbox(title, message, QMessageBox.Icon.Information)
        msg.exec()
    else:
        QMessageBox.information(parent, title, message)


def show_warning(parent, title: str, message: str):
    """Zeige Warn-Dialog."""
    if parent is not None and hasattr(parent, "_create_styled_msgbox"):
        msg = parent._create_styled_msgbox(title, message, QMessageBox.Icon.Warning)
        msg.exec()
    else:
        QMessageBox.warning(parent, title, message)


def show_error(parent, title: str, message: str):
    """Zeige Fehler-Dialog."""
    if parent is not None and hasattr(parent, "_create_styled_msgbox"):
        msg = parent._create_styled_msgbox(title, message, QMessageBox.Icon.Critical)
        msg.exec()
    else:
        QMessageBox.critical(parent, title, message)


def show_question(parent, title: str, message: str) -> bool:
    """Zeige Ja/Nein-Dialog. Gibt True zurück wenn Ja angeklickt."""
    reply = QMessageBox.question(parent, title, message)
    return reply == QMessageBox.StandardButton.Yes
