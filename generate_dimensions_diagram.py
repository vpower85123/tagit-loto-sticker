"""
Generiert ein Beispielbild der Export-Einstellungen mit Maßangaben
"""
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Rectangle

def generate_dimensions_diagram(width_mm=210, height_mm=297, margin_mm=8, spacing_mm=4, output_file="dimensions_example.png"):
    """
    Generiert ein visuelles Diagramm der Export-Einstellungen
    
    Args:
        width_mm: Breite in mm
        height_mm: Höhe in mm
        margin_mm: Rand in mm
        spacing_mm: Abstand zwischen Elementen in mm
        output_file: Ausgabedatei
    """
    # Erstelle Figure und Axes
    fig, ax = plt.subplots(1, 1, figsize=(12, 16))
    
    # Skalierung für bessere Darstellung (1mm = 1 unit)
    scale = 1
    width = width_mm * scale
    height = height_mm * scale
    margin = margin_mm * scale
    spacing = spacing_mm * scale
    
    # A4 Seite (äußerer Rahmen)
    page = Rectangle((0, 0), width, height, 
                     linewidth=3, edgecolor='black', 
                     facecolor='white', label='A4 Seite')
    ax.add_patch(page)
    
    # Rand-Bereich (gestrichelt)
    margin_rect = Rectangle((margin, margin), 
                            width - 2*margin, 
                            height - 2*margin,
                            linewidth=2, edgecolor='red', 
                            linestyle='--',
                            facecolor='lightblue', alpha=0.2,
                            label='Druckbarer Bereich')
    ax.add_patch(margin_rect)
    
    # Beispiel-Sticker (3x3 Grid)
    sticker_width = (width - 2*margin - 2*spacing) / 3
    sticker_height = (height - 2*margin - 2*spacing) / 3
    
    for row in range(3):
        for col in range(3):
            x = margin + col * (sticker_width + spacing)
            y = margin + row * (sticker_height + spacing)
            sticker = Rectangle((x, y), sticker_width, sticker_height,
                               linewidth=1.5, edgecolor='green',
                               facecolor='lightgreen', alpha=0.3)
            ax.add_patch(sticker)
    
    # Maßlinien und Beschriftungen
    
    # Breite (oben)
    ax.annotate('', xy=(width, height + 15), xytext=(0, height + 15),
                arrowprops=dict(arrowstyle='<->', color='blue', lw=2))
    ax.text(width/2, height + 20, f'Breite: {width_mm} mm', 
            ha='center', va='bottom', fontsize=12, color='blue', fontweight='bold')
    
    # Höhe (rechts)
    ax.annotate('', xy=(width + 15, height), xytext=(width + 15, 0),
                arrowprops=dict(arrowstyle='<->', color='blue', lw=2))
    ax.text(width + 20, height/2, f'Höhe: {height_mm} mm', 
            ha='left', va='center', fontsize=12, color='blue', 
            fontweight='bold', rotation=-90)
    
    # Rand links
    ax.annotate('', xy=(margin, height/2 + 30), xytext=(0, height/2 + 30),
                arrowprops=dict(arrowstyle='<->', color='red', lw=1.5))
    ax.text(margin/2, height/2 + 35, f'Rand: {margin_mm} mm', 
            ha='center', va='bottom', fontsize=10, color='red', fontweight='bold')
    
    # Rand oben
    ax.annotate('', xy=(width/2 + 30, height), xytext=(width/2 + 30, height - margin),
                arrowprops=dict(arrowstyle='<->', color='red', lw=1.5))
    ax.text(width/2 + 35, height - margin/2, f'{margin_mm} mm', 
            ha='left', va='center', fontsize=10, color='red', fontweight='bold')
    
    # Abstand horizontal (zwischen ersten beiden Stickern)
    x_space = margin + sticker_width
    y_space = margin + sticker_height/2
    ax.annotate('', xy=(x_space + spacing, y_space), xytext=(x_space, y_space),
                arrowprops=dict(arrowstyle='<->', color='orange', lw=1.5))
    ax.text(x_space + spacing/2, y_space - 8, f'Abstand: {spacing_mm} mm', 
            ha='center', va='top', fontsize=9, color='orange', 
            fontweight='bold', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    # Abstand vertikal (zwischen ersten beiden Reihen)
    x_vspace = margin + sticker_width/2
    y_vspace = margin + sticker_height
    ax.annotate('', xy=(x_vspace, y_vspace + spacing), xytext=(x_vspace, y_vspace),
                arrowprops=dict(arrowstyle='<->', color='orange', lw=1.5))
    ax.text(x_vspace + 8, y_vspace + spacing/2, f'{spacing_mm} mm', 
            ha='left', va='center', fontsize=9, color='orange', 
            fontweight='bold', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    # Titel und Legende
    ax.set_title('Export-Einstellungen - Maße Übersicht\nDIN A4 Format', 
                fontsize=16, fontweight='bold', pad=20)
    
    # Legende mit Erklärungen
    legend_elements = [
        patches.Patch(facecolor='white', edgecolor='black', linewidth=2, label='A4 Seite (210 × 297 mm)'),
        patches.Patch(facecolor='lightblue', edgecolor='red', linestyle='--', alpha=0.3, 
                     label=f'Rand: {margin_mm} mm (gestrichelt)'),
        patches.Patch(facecolor='lightgreen', edgecolor='green', alpha=0.3, 
                     label='Beispiel-Sticker'),
        patches.Patch(facecolor='white', edgecolor='orange', linewidth=2, 
                     label=f'Abstand zwischen Stickern: {spacing_mm} mm')
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=10, 
             bbox_to_anchor=(1.0, -0.02))
    
    # Achsen-Einstellungen
    ax.set_xlim(-30, width + 40)
    ax.set_ylim(-30, height + 40)
    ax.set_aspect('equal')
    ax.axis('off')
    
    # Speichern
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight', facecolor='white')
    print(f"✓ Diagramm wurde gespeichert: {output_file}")
    plt.show()

if __name__ == "__main__":
    # Standardwerte aus dem Screenshot
    generate_dimensions_diagram(
        width_mm=210,
        height_mm=297,
        margin_mm=8,
        spacing_mm=4,
        output_file="export_dimensions_example.png"
    )
