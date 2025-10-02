import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path

def visualize_table_structure_v2(json_path: Path, page_index_to_find: int):
    """
    Version améliorée qui dessine la structure du tableau de manière plus claire,
    en différenciant la grille des cellules logiques.
    """
    if not json_path.exists():
        print(f"Erreur : Le fichier '{json_path}' est introuvable.")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    page_data = None
    for item in data:
        if item.get("index") == page_index_to_find:
            page_data = item['page_data'][0]
            break

    if not page_data:
        print(f"Erreur : Page {page_index_to_find} non trouvée.")
        return

    table_components = page_data.get("table_data", [])
    overall_table_bbox = page_data.get("table")

    fig, ax = plt.subplots(figsize=(15, 20))
    ax.set_title(f"Structure de Tableau Améliorée - {json_path.name} - Page {page_index_to_find}", fontsize=16)

    color_map = {
        "table row": "gray",
        "table column": "gray",
        "table spanning cell": "orange",
        "table column header": "red",
        "table row header": "purple"
    }

    # --- NOUVELLE LOGIQUE DE DESSIN ---
    # 1. Séparer les composants en deux groupes : grille et cellules logiques
    grid_components = [c for c in table_components if c['label'] in ('table row', 'table column')]
    logical_components = [c for c in table_components if c['label'] not in ('table row', 'table column')]

    # 2. Dessiner la grille de base en pointillé
    for component in grid_components:
        bbox = component.get("bbox")
        if not bbox: continue
        width, height = bbox[2] - bbox[0], bbox[3] - bbox[1]
        rect = patches.Rectangle(
            (bbox[0], bbox[1]), width, height,
            linewidth=1,
            edgecolor='gray',
            facecolor='none',
            linestyle='--' # Style en pointillé
        )
        ax.add_patch(rect)

    # 3. Dessiner les cellules logiques par-dessus avec des lignes pleines et colorées
    for component in logical_components:
        label = component.get("label", "unknown")
        bbox = component.get("bbox")
        if not bbox: continue
        color = color_map.get(label, "black")
        width, height = bbox[2] - bbox[0], bbox[3] - bbox[1]
        rect = patches.Rectangle(
            (bbox[0], bbox[1]), width, height,
            linewidth=2.5, # Plus épais
            edgecolor=color,
            facecolor='none' # Pas de remplissage pour mieux voir
        )
        ax.add_patch(rect)
        ax.text(bbox[0], bbox[1] - 5, label, fontsize=9, color=color, weight='bold')
    # --- FIN DE LA NOUVELLE LOGIQUE ---

    if overall_table_bbox:
        padding = 50
        ax.set_xlim(overall_table_bbox[0] - padding, overall_table_bbox[2] + padding)
        ax.set_ylim(overall_table_bbox[3] + padding, overall_table_bbox[1] - padding)

    legend_elements = [
        patches.Patch(edgecolor='gray', facecolor='none', linestyle='--', label='Grille (Lignes/Colonnes)'),
        patches.Patch(edgecolor='orange', facecolor='none', linewidth=2.5, label='Cellule Fusionnée'),
        patches.Patch(edgecolor='red', facecolor='none', linewidth=2.5, label='En-tête de Colonne'),
        patches.Patch(edgecolor='purple', facecolor='none', linewidth=2.5, label='En-tête de Ligne')
    ]
    ax.legend(handles=legend_elements, loc='upper right')
    ax.grid(False) # La grille de matplotlib n'est plus utile

    output_filename = f"{json_path.stem}_page_{page_index_to_find}_structure_v2.png"
    plt.savefig(output_filename, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"Visualisation améliorée sauvegardée sous : '{output_filename}'")

if __name__ == "__main__":
    # Assurez-vous d'avoir le fichier JSON dans le même dossier que le script
    file_to_visualize = Path("treatments/page.json")
    page_index = 6
    
    visualize_table_structure_v2(file_to_visualize, page_index)