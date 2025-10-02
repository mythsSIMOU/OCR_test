# passe2_removeTags.py

import re
import json
from pathlib import Path
from typing import Dict, List, Any

# Importer les classes de base de notre framework
from manage_dataset import DataSetManager, LayoutManager
ROOT_DIR = Path(__file__).resolve().parents[1] # Cette ligne reste utile pour trouver le dossier 'states'


class TagRemovingLayoutManager(LayoutManager):
    """
    Un LayoutManager personnalisé qui nettoie les balises HTML du texte d'un layout.
    """
    def __init__(self):
        # Expression régulière pour trouver et supprimer les balises HTML (ex: <b>, </i>, <...>)
        self.html_tag_regex = re.compile('</?[^>]+(>|$)')
        print("TagRemovingLayoutManager initialisé.")

    def execute(self, layout_data: Dict[str, Any]) -> Dict[str, Any]:
        # On travaille sur une copie pour ne pas altérer les données originales en mémoire
        processed_layout = layout_data.copy()
        
        original_text_list = processed_layout.get('text')
        
        # Vérifier si le champ 'text' existe et n'est pas vide
        if not original_text_list:
            return processed_layout # Retourner le layout tel quel s'il n'y a pas de texte

        cleaned_text_list = []
        for text_entry in original_text_list:
            # Appliquer le regex pour substituer les balises par une chaîne vide
            cleaned_text = self.html_tag_regex.sub('', text_entry)
            cleaned_text_list.append(cleaned_text)
        
        # Remplacer la liste de textes originale par la nouvelle liste nettoyée
        processed_layout['text'] = cleaned_text_list
        
        return processed_layout

if __name__ == "__main__":
    STATES_DIR = ROOT_DIR / "states"
    SOURCE_DIR = STATES_DIR / "result_json_merged"
    OUTPUT_DIR = STATES_DIR / "result_json_no_tags"

    print(f"--- Lancement de la Passe 2 : Suppression des balises HTML de '{SOURCE_DIR}' ---")

    # 1. Initialiser le DataSetManager
    data_manager = DataSetManager(source_dir=str(SOURCE_DIR), output_dir=str(OUTPUT_DIR))

    # 2. Créer notre LayoutManager personnalisé pour la suppression des balises
    tag_remover_manager = TagRemovingLayoutManager()

    # 3. Injecter notre manager personnalisé dans le système.
    # La logique s'applique au niveau du layout, on remplace donc le layout_manager du page_manager.
    data_manager.page_manager.layout_manager = tag_remover_manager
    print("Injection du TagRemovingLayoutManager dans le système.")

    # 4. Lancer le processus
    data_manager.process_dataset()