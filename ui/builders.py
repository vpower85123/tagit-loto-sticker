"""Tab UI Builders fuer die Sticker App (Facade).

Re-exportiert alle Builder-Funktionen aus den aufgeteilten Modulen:
- builder_utils: Utility-Funktionen und Icon-Factory
- builder_sticker: Sticker-Tab, Start-Tab, PDF-Import-Tab
- builder_equipment: Equipment-Tab
- builder_export: Export-Tab
"""

# Utilities & Icon Factory
from ui.builder_utils import (
    add_depth_shadow,
    _get_card_style,
    _create_glass_button,
    create_symbol_icon,
)

# Tab Builders
from ui.builder_sticker import build_start_tab, build_sticker_tab, build_pdf_import_tab
from ui.builder_equipment import build_equipment_tab
from ui.builder_export import build_export_tab

__all__ = [
    'add_depth_shadow',
    '_get_card_style',
    '_create_glass_button',
    'create_symbol_icon',
    'build_start_tab',
    'build_sticker_tab',
    'build_pdf_import_tab',
    'build_equipment_tab',
    'build_export_tab',
]
