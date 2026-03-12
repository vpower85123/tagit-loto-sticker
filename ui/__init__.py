"""UI-Helpers und utilities für alle Tabs."""


def create_glass_button(text, parent=None, dark_mode=False):
    """Factory-Funktion für GlassGlowButton."""
    from ui.glass_button import GlassGlowButton
    return GlassGlowButton(text, parent, dark_mode)
