# treatments/passe3_solveSameLine.py

import json
from pathlib import Path
from collections import defaultdict

# L'import fonctionne directement car manage_dataset.py est dans le même dossier
from manage_dataset import DataSetManager, PageManager, LayoutManager

class SameLineReorderingPageManager(PageManager):
    """
    Un PageManager personnalisé qui réorganise les layouts sur une page.
    Il regroupe les layouts qui sont sur la même ligne horizontale (avec une tolérance)
    puis les trie de gauche à droite.
    """
    def __init__(self, layout_manager: LayoutManager, y_snap_grid_size: int = 5):
        super().__init__(layout_manager)
        self.snap_grid_size = y_snap_grid_size
        print(f"SameLineReorderingPageManager initialisé avec une grille de 'snap' de {y_snap_grid_size}px.")

    def execute(self, page_data: dict, file_path: Path) -> dict: # Ajout de file_path pour la cohérence
        original_layouts = page_data.get('page', [])
        if not original_layouts:
            return page_data

        # 1. Regrouper les layouts par "rangée" en utilisant la formule de magnétisme
        row_groups = defaultdict(list)
        for layout in original_layouts:
            # On utilise la coordonnée y_start pour déterminer la ligne
            y_start = layout['bbox_layout'][1]
            snapped_y = int(y_start / self.snap_grid_size) * self.snap_grid_size
            row_groups[snapped_y].append(layout)

        # 2. Reconstruire la liste des layouts, triée par rangée puis par position X
        new_layout_list = []
        # On trie les clés (les y "snappés") pour traiter les rangées de haut en bas
        for snapped_y in sorted(row_groups.keys()):
            layouts_in_row = row_groups[snapped_y]
            
            # On trie les layouts dans la rangée par leur coordonnée x_start (de gauche à droite)
            sorted_row = sorted(layouts_in_row, key=lambda l: l['bbox_layout'][0])
            
            # On ajoute la rangée triée à notre liste finale
            new_layout_list.extend(sorted_row)

        # 3. Mettre à jour la page avec la nouvelle liste de layouts ordonnée
        processed_page = page_data.copy()
        processed_page['page'] = new_layout_list
        
        # Mettre à jour le champ 'position' pour refléter le nouvel ordre
        for i, layout in enumerate(processed_page['page']):
            layout['position'] = i
            
        return processed_page

if __name__ == "__main__":
    # --- MODIFIÉ : Définition des chemins pour la nouvelle structure ---
    # Obtenir le chemin du dossier racine du projet (qui contient 'treatments' et 'states')
    ROOT_DIR = Path(__file__).resolve().parents[1]
    # Définir le dossier où se trouvent toutes les données
    STATES_DIR = ROOT_DIR / "states"
    
    # Définir les chemins d'entrée et de sortie spécifiques à cette passe
    SOURCE_DIR = STATES_DIR / "result_json_no_tags"
    OUTPUT_DIR = STATES_DIR / "result_json_reordered2"
    # --- FIN DE LA MODIFICATION ---

    print(f"--- Lancement de la Passe 3 : Réorganisation des layouts de '{SOURCE_DIR.name}' ---")

    # 1. Initialiser le DataSetManager
    data_manager = DataSetManager(source_dir=str(SOURCE_DIR), output_dir=str(OUTPUT_DIR))

    # 2. Créer notre PageManager personnalisé pour la réorganisation
    reordering_page_manager = SameLineReorderingPageManager(
        layout_manager=data_manager.layout_manager # On garde le LayoutManager par défaut
    )

    # 3. Injecter notre manager personnalisé dans le système.
    data_manager.document_manager.page_manager = reordering_page_manager
    print("Injection du SameLineReorderingPageManager dans le système.")

    # 4. Lancer le processus
    data_manager.process_dataset()