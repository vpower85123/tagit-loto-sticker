import json
import logging
from dataclasses import asdict
from core.paths import PathManager
from core.models import StickerConfig, CountConfig, ExportConfig, ThemeConfig

logger = logging.getLogger(__name__)

class ConfigManager:
    @staticmethod
    def _read_config_file() -> dict:
        if PathManager.CONFIG_PATH.exists():
            try:
                return json.loads(PathManager.CONFIG_PATH.read_text("utf-8"))
            except Exception:
                return {}
        return {}
    @staticmethod
    def load() -> tuple['StickerConfig','CountConfig', 'ThemeConfig']:
        DEFAULT_STICKER = {
            'width_mm': 45.0,
            'height_mm': 30.0,
            'dpi': 300,
            'corner_radius': 4,
            'outline_width': 2,
            'font_path': 'Arial',
            'auto_adjust': True,
            'sticker_color': '#FFFFFF',
            'font_size_mm': 6.0,
            'line_height_mm': 7.0,
            'symbols_dir': str(getattr(PathManager, 'SYMBOLS_DIR', PathManager.BASE_DIR / 'symbols')),
            'symbol_corner_radius': 2,
            'symbol_size_mm': 0.0,
            'symbol_offset_x_mm': 0.0,
            'symbol_offset_y_mm': 0.0,
            'text_offset_x': 0,
            'text_offset_y': 0,
            'qr_mode_enabled': False,
            'qr_placeholder_text': 'QR',
            'qr_placeholder_bg': '#FFFFFF',
            'qr_image_path': None,
            'preview_scale': 0.7,
            'export_exact_three_rows': False,
            'export_margin_mm': 8.0,
            'export_gap_mm': 5.0,
            'export_min_scale': 0.8,
        }
        DEFAULT_COUNT = {
            'width_mm': 210.0,
            'height_mm': 50.0,
            'dpi': 300,
            'corner_radius': 0,
            'outline_width': 0,
            'font_path': 'Arial',
            'auto_adjust': False,
            'font_size_mm': 8.0,
            'line_height_mm': 9.0,
            'count_print_copies': 1,
            'header_text': 'TOTAL COUNT OF LOTO POINTS –',
            'bg_color': '#FFFFFF',
            'stripe_color': '#FF0000',
            'show_stripes': True,
            'header_margin_mm': 3.0,
            'text_spacing_mm': 5.0,
        }
        DEFAULT_THEME = {
            'mode': 'light',
            'custom_colors': {}
        }

        def _norm_numeric(d: dict, keys: list):
            for k in keys:
                if k in d:
                    v = d[k]
                    if isinstance(v, str):
                        raw = v.strip().replace(',', '.')
                        try:
                            d[k] = float(raw)
                        except ValueError:
                            pass
                    elif isinstance(v, list) and len(v) == 1:
                        d[k] = v[0]
                        if isinstance(d[k], str):
                            raw = d[k].strip().replace(',', '.')
                            try:
                                d[k] = float(raw)
                            except ValueError:
                                pass

        def _filter_keys(data: dict, cls):
            allowed = set(getattr(cls, '__dataclass_fields__', {}).keys())
            return {k: v for k, v in data.items() if k in allowed}

        try:
            if PathManager.CONFIG_PATH.exists():
                data = json.loads(PathManager.CONFIG_PATH.read_text('utf-8'))
                st_data = data.get('sticker', {}) or {}
                ct_data = data.get('count', {}) or {}
                th_data = data.get('theme', {}) or {}
                
                _norm_numeric(st_data, ['symbol_offset_x_mm','symbol_offset_y_mm','symbol_size_mm','width_mm','height_mm','font_size_mm','line_height_mm'])
                _norm_numeric(ct_data, ['width_mm','height_mm','font_size_mm','line_height_mm','count_print_copies'])
                
                # Konvertiere corner_radius und outline_width zu Integer
                if 'corner_radius' in st_data:
                    st_data['corner_radius'] = int(st_data['corner_radius'])
                if 'outline_width' in st_data:
                    st_data['outline_width'] = int(st_data['outline_width'])
                if 'symbol_corner_radius' in st_data:
                    st_data['symbol_corner_radius'] = int(st_data['symbol_corner_radius'])
                if 'corner_radius' in ct_data:
                    ct_data['corner_radius'] = int(ct_data['corner_radius'])
                if 'outline_width' in ct_data:
                    ct_data['outline_width'] = int(ct_data['outline_width'])
                if 'count_print_copies' in ct_data:
                    ct_data['count_print_copies'] = max(1, int(ct_data['count_print_copies']))
                
                st_base = DEFAULT_STICKER.copy(); st_base.update(st_data)
                ct_base = DEFAULT_COUNT.copy(); ct_base.update(ct_data)
                th_base = DEFAULT_THEME.copy(); th_base.update(th_data)
                
                # Defensive: falls laufende StickerConfig-Version (zur Laufzeit) kein outline_width akzeptiert
                try:
                    return StickerConfig(**st_base), CountConfig(**ct_base), ThemeConfig(**th_base)
                except TypeError as te:
                    if 'outline_width' in st_base:
                        ow = st_base.pop('outline_width')
                        logger.warning(f"StickerConfig akzeptiert 'outline_width' nicht (TypeError: {te}); entferne Feld (Wert war {ow}).")
                        return StickerConfig(**st_base), CountConfig(**ct_base), ThemeConfig(**th_base)
                    raise
        except Exception as e:
            logger.warning(f"Config laden fehlgeschlagen, verwende Defaults: {e}")
        return StickerConfig(**DEFAULT_STICKER), CountConfig(**DEFAULT_COUNT), ThemeConfig(**DEFAULT_THEME)
    @staticmethod
    def load_export() -> 'ExportConfig':
        try:
            # Versuche zuerst, export_config.json zu laden (separate Datei)
            if PathManager.EXPORT_CONFIG_PATH.exists():
                data = json.loads(PathManager.EXPORT_CONFIG_PATH.read_text('utf-8'))
                return ExportConfig(**data)
            
            # Fallback: Versuche aus config.json zu laden (export section)
            if PathManager.CONFIG_PATH.exists():
                data = json.loads(PathManager.CONFIG_PATH.read_text('utf-8'))
                exp_data = data.get('export', {})
                if exp_data:
                    return ExportConfig(**exp_data)
        except Exception as e:
            logger.warning(f"ExportConfig laden fehlgeschlagen, verwende Defaults: {e}")
        return ExportConfig()
    @staticmethod
    def save_sticker(st_cfg: 'StickerConfig') -> None:
        try:
            base = ConfigManager._read_config_file()
            base['sticker'] = asdict(st_cfg)
            base.setdefault('count', {})
            base.setdefault('export', base.get('export', {}))
            PathManager.CONFIG_PATH.write_text(json.dumps(base, indent=2, ensure_ascii=False), encoding='utf-8')
        except Exception as e:
            logger.error(f"StickerConfig speichern fehlgeschlagen: {e}")
    @staticmethod
    def save_count(ct_cfg: 'CountConfig') -> None:
        try:
            base = ConfigManager._read_config_file()
            base.setdefault('sticker', {})
            base['count'] = asdict(ct_cfg)
            base.setdefault('export', base.get('export', {}))
            PathManager.CONFIG_PATH.write_text(json.dumps(base, indent=2, ensure_ascii=False), encoding='utf-8')
        except Exception as e:
            logger.error(f"CountConfig speichern fehlgeschlagen: {e}")
    @staticmethod
    def save(st_cfg: 'StickerConfig', ct_cfg: 'CountConfig', th_cfg: 'ThemeConfig | None' = None) -> None:
        try:
            base = {}
            if PathManager.CONFIG_PATH.exists():
                try:
                    base = json.loads(PathManager.CONFIG_PATH.read_text("utf-8"))
                except Exception:
                    base = {}
            base["sticker"] = asdict(st_cfg)
            base["count"] = asdict(ct_cfg)
            if th_cfg:
                base["theme"] = asdict(th_cfg)
            PathManager.CONFIG_PATH.write_text(json.dumps(base, indent=2, ensure_ascii=False), encoding='utf-8')
        except Exception as e:
            logger.error(f"Config speichern fehlgeschlagen: {e}")
    @staticmethod
    def save_export(exp_cfg: 'ExportConfig') -> None:
        try:
            # Baue export_data dict (wird in beide Dateien geschrieben)
            export_data = {
                'sheet_width_mm': exp_cfg.sheet_width_mm,
                'sheet_height_mm': exp_cfg.sheet_height_mm,
                'orientation_mode': exp_cfg.orientation_mode,
                'margin_mm': exp_cfg.margin_mm,
                'gap_mm': exp_cfg.gap_mm,
                'min_scale': exp_cfg.min_scale,
                'exact_three_rows': exp_cfg.exact_three_rows,
                'include_count_header': exp_cfg.include_count_header,
                'export_mode': getattr(exp_cfg, 'export_mode', 'multi'),
                'roll_mode': getattr(exp_cfg, 'roll_mode', False),
                'roll_width_mm': getattr(exp_cfg, 'roll_width_mm', 500.0),
                'max_columns': exp_cfg.max_columns,
                'max_rows': exp_cfg.max_rows,
                'force_rows': exp_cfg.force_rows,
                'force_cols': exp_cfg.force_cols,
                'sticker_rotate_mode': exp_cfg.sticker_rotate_mode,
                'sticker_rotation_locked': getattr(exp_cfg, 'sticker_rotation_locked', None),
                'auto_height': getattr(exp_cfg, 'auto_height', False),
            }
            
            # Speichere in export_config.json (primäre Datei)
            PathManager.EXPORT_CONFIG_PATH.write_text(json.dumps(export_data, indent=2, ensure_ascii=False), encoding='utf-8')
            
            # Speichere auch in config.json (Fallback/Kompatibilität)
            base = {}
            if PathManager.CONFIG_PATH.exists():
                try:
                    base = json.loads(PathManager.CONFIG_PATH.read_text("utf-8"))
                except Exception:
                    base = {}
            base.setdefault("sticker", {})
            base.setdefault("count", {})
            base["export"] = export_data
            PathManager.CONFIG_PATH.write_text(json.dumps(base, indent=2, ensure_ascii=False), encoding='utf-8')
        except Exception as e:
            logger.error(f"ExportConfig speichern fehlgeschlagen: {e}")
