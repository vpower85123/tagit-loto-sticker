@echo off
echo ========================================
echo    TAG!T Sticker - Build & Installer
echo ========================================
echo.

cd /d "%~dp0.."

echo [1/3] Python-Abhängigkeiten prüfen...
pip install pyinstaller --quiet

echo [2/3] EXE mit PyInstaller erstellen...
pyinstaller --noconfirm sticker_app.spec

if errorlevel 1 (
    echo FEHLER: PyInstaller fehlgeschlagen!
    pause
    exit /b 1
)

echo [3/3] Installer erstellen...
echo.
echo HINWEIS: Inno Setup muss installiert sein!
echo Download: https://jrsoftware.org/isdl.php
echo.

if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\tagit_setup.iss
) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    "C:\Program Files\Inno Setup 6\ISCC.exe" installer\tagit_setup.iss
) else (
    echo Inno Setup nicht gefunden!
    echo Bitte manuell installieren und installer\tagit_setup.iss öffnen.
)

echo.
echo ========================================
echo    Fertig! Installer in dist\
echo ========================================
pause
