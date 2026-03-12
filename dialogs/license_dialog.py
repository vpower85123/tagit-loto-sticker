from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QLineEdit, 
                             QPushButton, QMessageBox, QHBoxLayout, QFrame)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QFont, QIcon
from ui.glass_button import GlassGlowButton

class LoginDialog(QDialog):
    def __init__(self, license_manager, parent=None):
        super().__init__(parent)
        self.license_manager = license_manager
        self.setWindowTitle("TAG!T - Login")
        self.setFixedSize(400, 500)
        # Entferne Schließen-Button, um Umgehung zu erschweren
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint)
        
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # Icon oder Logo Platzhalter
        icon_label = QLabel("👤")
        icon_label.setFont(QFont("Segoe UI Emoji", 48))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)
        
        # Header
        title = QLabel("Anmelden")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #2c3e50;")
        layout.addWidget(title)
        
        info = QLabel("Bitte melden Sie sich mit Ihrem Account an, um die Software zu nutzen.")
        info.setWordWrap(True)
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setStyleSheet("color: #7f8c8d; font-size: 13px;")
        layout.addWidget(info)
        
        # Inputs
        input_style = """
            QLineEdit {
                padding: 12px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                background: #f8f9fa;
                color: #2c3e50;
                font-size: 14px;
                text-align: center;
            }
            QLineEdit:focus {
                border-color: #146B8A;
                background: white;
            }
        """
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("E-Mail Adresse")
        self.email_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.email_input.setStyleSheet(input_style)
        layout.addWidget(self.email_input)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Passwort")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.password_input.setStyleSheet(input_style)
        layout.addWidget(self.password_input)
        
        # Buttons
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(12)
        
        self.login_btn = GlassGlowButton("Anmelden")
        self.login_btn.setFixedHeight(38)
        self.login_btn.clicked.connect(self._on_login)
        btn_layout.addWidget(self.login_btn)
        
        self.register_btn = GlassGlowButton("Account erstellen / Lizenz kaufen")
        self.register_btn.setFixedHeight(38)
        self.register_btn.clicked.connect(self._on_register)
        btn_layout.addWidget(self.register_btn)
        
        layout.addLayout(btn_layout)
        layout.addStretch()
        
    def _on_login(self):
        email = self.email_input.text()
        password = self.password_input.text()
        
        if not email or not password:
            QMessageBox.warning(self, "Fehler", "Bitte füllen Sie alle Felder aus.")
            return
        
        # Backdoor login for testing
        if email == "admin" and password == "admin85":
            QMessageBox.information(self, "Erfolg", "Admin Login erfolgreich")
            self.accept()
            return
            
        success, message = self.license_manager.login(email, password)
        
        if success:
            QMessageBox.information(self, "Erfolg", message)
            self.accept()
        else:
            QMessageBox.critical(self, "Anmeldung fehlgeschlagen", message)
            
    def _on_register(self):
        dialog = RegistrationDialog(self.license_manager, self)
        dialog.exec()

class RegistrationDialog(QDialog):
    def __init__(self, license_manager, parent=None):
        super().__init__(parent)
        self.license_manager = license_manager
        self.setWindowTitle("TAG!T - Registrierung")
        self.setFixedSize(400, 550)
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(15)
        
        title = QLabel("Neuen Account erstellen")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        input_style = """
            QLineEdit {
                padding: 10px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                background: #f8f9fa;
                color: #2c3e50;
            }
            QLineEdit:focus {
                border-color: #146B8A;
                background: white;
            }
        """
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("E-Mail Adresse")
        self.email_input.setStyleSheet(input_style)
        self.email_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.email_input)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Passwort")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setStyleSheet(input_style)
        self.password_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.password_input)
        
        self.license_input = QLineEdit()
        self.license_input.setPlaceholderText("Lizenzschlüssel (XXXX-XXXX-XXXX-XXXX)")
        self.license_input.setStyleSheet(input_style)
        self.license_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.license_input)
        
        reg_btn = GlassGlowButton("Registrieren")
        reg_btn.setFixedHeight(38)
        reg_btn.clicked.connect(self._on_register)
        layout.addWidget(reg_btn)
        
        cancel_btn = GlassGlowButton("Abbrechen")
        cancel_btn.setFixedHeight(38)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)
        
        layout.addStretch()

    def _on_register(self):
        email = self.email_input.text()
        password = self.password_input.text()
        key = self.license_input.text()
        
        if not email or not password or not key:
            QMessageBox.warning(self, "Fehler", "Bitte füllen Sie alle Felder aus.")
            return
            
        success, message = self.license_manager.register_user(email, password, key)
        
        if success:
            QMessageBox.information(self, "Erfolg", message)
            self.accept()
        else:
            QMessageBox.critical(self, "Fehler", message)
