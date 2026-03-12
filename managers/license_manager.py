import json
import hashlib
import datetime
import os
import uuid
from pathlib import Path

class LicenseManager:
    def __init__(self, storage_path="license.dat", db_path="users_db.json"):
        base_dir = os.path.dirname(os.path.dirname(__file__))
        self.storage_path = os.path.join(base_dir, storage_path)
        self.db_path = os.path.join(base_dir, db_path)
        self.secret_salt = "TAGIT_LOTO_SECRET_2025_SECURE"
        self.license_secret = "TAGIT_LICENSE_MASTER_KEY_2026_SECURE"  # Muss mit Generator übereinstimmen! 

    def get_machine_id(self):
        """Generiert eine eindeutige ID für diesen Computer."""
        return str(uuid.getnode())

    def validate_key_format(self, key):
        """Prüft das Format des Lizenzschlüssels (XXXX-XXXX-XXXX-XXXX)."""
        key = key.strip().upper()
        parts = key.split('-')
        if len(parts) != 4:
            return False
        for part in parts:
            if len(part) != 4:
                return False
        return True

    def register_user(self, email, password, license_key):
        """Registriert einen neuen Benutzer mit Lizenzschlüssel."""
        if not self.validate_key_format(license_key):
            return False, "Ungültiges Lizenzformat (XXXX-XXXX-XXXX-XXXX)."
            
        users = self._load_users_db()
        
        if email in users:
            return False, "Diese E-Mail-Adresse ist bereits registriert."
        
        # Validiere und dekodiere signierten Schlüssel
        is_valid, duration_days, error_msg = self._validate_signed_license_key(license_key)
        if not is_valid:
            return False, error_msg or "Ungültiger Lizenzschlüssel."
        
        # Prüfe ob Schlüssel bereits verwendet wurde (in users_db)
        for user_email, user_data in users.items():
            if user_data.get("license_key") == license_key:
                return False, "Dieser Lizenzschlüssel wurde bereits verwendet."
        
        activation_date = datetime.datetime.now()
        expiry_date = activation_date + datetime.timedelta(days=duration_days)
        
        # Passwort hashen
        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        
        users[email] = {
            "password_hash": pw_hash,
            "license_key": license_key,
            "activation_date": activation_date.isoformat(),
            "expiry_date": expiry_date.isoformat(),
            "duration_days": duration_days
        }
        
        if self._save_users_db(users):
            days_left = duration_days
            return True, f"Registrierung erfolgreich! Lizenz gültig für {days_left} Tage."
        else:
            return False, "Fehler beim Speichern der Benutzerdaten."

    def login(self, email, password):
        """Login mit Prüfung gegen lokale Benutzer-DB."""
        users = self._load_users_db()
        
        if email not in users:
            return False, "Benutzer nicht gefunden. Bitte registrieren Sie sich zuerst."
            
        user_data = users[email]
        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        
        if user_data["password_hash"] != pw_hash:
            return False, "Falsches Passwort."
            
        # Lizenz prüfen
        try:
            expiry = datetime.datetime.fromisoformat(user_data["expiry_date"])
            if datetime.datetime.now() > expiry:
                return False, f"Ihre Lizenz ist am {expiry.strftime('%d.%m.%Y')} abgelaufen."
        except:
            return False, "Fehler in den Lizenzdaten."
            
        # Login erfolgreich -> Lokale Session erstellen
        machine_id = self.get_machine_id()
        license_key = user_data["license_key"]
        activation_date = user_data["activation_date"]
        expiry_str = user_data["expiry_date"]
        
        data = {
            "email": email,
            "key": license_key,
            "activation_date": activation_date,
            "expiry_date": expiry_str,
            "machine_id": machine_id,
            "signature": self._sign_data(email, license_key, activation_date, expiry_str, machine_id)
        }
        
        try:
            self._save_license(data)
            return True, f"Willkommen zurück, {email}!"
        except Exception as e:
            return False, f"Fehler beim Speichern der Session: {str(e)}"

    def logout(self):
        """Meldet den Benutzer ab (löscht die Session-Datei)."""
        if os.path.exists(self.storage_path):
            try:
                os.remove(self.storage_path)
                return True
            except:
                return False
        return True

    def check_license(self):
        """
        Prüft, ob eine gültige Lizenz vorhanden ist.
        Rückgabe: (is_valid, message, expiry_date_obj)
        """
        data = self._load_license()
        if not data:
            return False, "Bitte melden Sie sich an.", None
            
        # 1. Signatur prüfen
        expected_sig = self._sign_data(
            data.get("email", ""), # Backwards compatibility handled by empty string default? No, need to be careful.
            data.get("key"), 
            data.get("activation_date"), 
            data.get("expiry_date"),
            data.get("machine_id")
        )
        
        # Handle old license format (without email) if necessary, but we are replacing it.
        # Let's just assume new format for now or reset if invalid.
        
        if data.get("signature") != expected_sig:
            return False, "Sitzung ungültig. Bitte neu anmelden.", None
            
        # 2. Maschinen-ID prüfen
        if data.get("machine_id") != self.get_machine_id():
            return False, "Bitte melden Sie sich auf diesem Gerät neu an.", None
            
        # 3. Ablaufdatum prüfen
        try:
            expiry = datetime.datetime.fromisoformat(data["expiry_date"])
            if datetime.datetime.now() > expiry:
                return False, f"Lizenz abgelaufen am {expiry.strftime('%d.%m.%Y')}.", expiry
            
            days_left = (expiry - datetime.datetime.now()).days
            return True, f"Angemeldet als {data.get('email')}", expiry
        except ValueError:
            return False, "Fehler in den Lizenzdaten.", None

    def _sign_data(self, email, key, date_str, expiry_str, machine_id):
        """Erstellt eine Signatur für die Lizenzdaten."""
        raw = f"{email}|{key}|{date_str}|{expiry_str}|{machine_id}|{self.secret_salt}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def _save_license(self, data):
        with open(self.storage_path, 'w') as f:
            json.dump(data, f, indent=4)

    def _load_license(self):
        if not os.path.exists(self.storage_path):
            return None
        try:
            with open(self.storage_path, 'r') as f:
                return json.load(f)
        except:
            return None

    def _save_users_db(self, users):
        try:
            with open(self.db_path, 'w') as f:
                json.dump(users, f, indent=4)
            return True
        except:
            return False

    def _load_users_db(self):
        if not os.path.exists(self.db_path):
            return {}
        try:
            with open(self.db_path, 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def _validate_signed_license_key(self, license_key):
        """Validiert einen signierten Lizenzschlüssel und extrahiert die Gültigkeitsdauer"""
        try:
            parts = license_key.split('-')
            if len(parts) != 4:
                return False, 0, "Ungültiges Format"
            
            days_hex, random1, random2, signature = parts
            
            # Rekonstruiere Daten für Signatur-Prüfung
            data_to_sign = f"{days_hex}-{random1}-{random2}"
            
            # Berechne erwartete Signatur
            expected_sig = hashlib.sha256(f"{data_to_sign}|{self.license_secret}".encode()).hexdigest()[:4].upper()
            
            # Prüfe Signatur
            if signature.upper() != expected_sig:
                return False, 0, "Ungültige Signatur - Schlüssel gefälscht"
            
            # Dekodiere Gültigkeitsdauer
            try:
                duration_days = int(days_hex, 16)  # Hexadezimal zu Dezimal
            except ValueError:
                return False, 0, "Fehlerhafte Schlüsseldaten"
            
            # Validiere Plausibilität (1-3650 Tage)
            if duration_days < 1 or duration_days > 3650:
                return False, 0, "Ungültige Gültigkeitsdauer"
            
            return True, duration_days, None
            
        except Exception as e:
            return False, 0, f"Validierungsfehler: {str(e)}"
