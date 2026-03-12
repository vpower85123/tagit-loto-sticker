"""
Konvertiert PNG zu ICO für Windows Installer
"""
from PIL import Image
import os

# Pfade
script_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(script_dir)
parent_dir = os.path.dirname(base_dir)

png_path = os.path.join(parent_dir, "TAG!T Icon.png")
ico_path = os.path.join(base_dir, "assets", "icons", "app_icon.ico")

# Ordner erstellen falls nicht vorhanden
os.makedirs(os.path.dirname(ico_path), exist_ok=True)

# PNG laden und in verschiedenen Größen als ICO speichern
img = Image.open(png_path)

# ICO mit mehreren Größen (für beste Darstellung)
sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
icons = []

for size in sizes:
    resized = img.resize(size, Image.Resampling.LANCZOS)
    # In RGBA konvertieren falls nötig
    if resized.mode != 'RGBA':
        resized = resized.convert('RGBA')
    icons.append(resized)

# Als ICO speichern
icons[0].save(ico_path, format='ICO', sizes=[(s[0], s[1]) for s in sizes], append_images=icons[1:])

print(f"✅ ICO erstellt: {ico_path}")
