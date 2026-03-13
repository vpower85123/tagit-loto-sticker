"""Theme-Helper fuer das Hauptfenster."""

from ui.theme import Theme, get_theme_colors


def apply_main_window_theme(window) -> None:
    """Wendet Theme-Styles auf das Hauptfenster an."""
    custom_colors = getattr(window.theme_config, 'custom_colors', {}) if hasattr(window, 'theme_config') else {}
    colors = get_theme_colors(Theme.LIGHT, custom_colors)
    tooltip_bg = "#1f2937"  # Dunkelgrau fuer besseren Kontrast
    tooltip_fg = "#ffffff"  # Weisser Text

    # Check if custom background color is set
    bg_style = f"background-color: {colors['bg']};"

    # Tab colors fuer Light Mode
    tab_bg = "rgba(255, 255, 255, 150)"
    tab_selected_bg = "rgba(255, 255, 255, 240)"
    tab_hover_bg = "rgba(255, 255, 255, 200)"

    window.setStyleSheet(f"""
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
