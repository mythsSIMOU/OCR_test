
import json
from pathlib import Path
from typing import List, Dict, Any

from manage_dataset import DataSetManager, DocumentManager, PageManager

ROOT_DIR = Path(__file__).resolve().parents[1] # Cette ligne reste utile pour trouver le dossier 'states'

class MergingDocumentManager(DocumentManager):
    """
    Un DocumentManager personnalisé qui fusionne les données de v1 et v2 au niveau de la page.
    """
    def __init__(self, page_manager: PageManager, v2_dir: str, source_dir: str):
        super().__init__(page_manager)
        self.v2_path = Path(v2_dir)
        self.source_path = Path(source_dir)
        print(f"MergingDocumentManager (Page-Level) initialisé. Cherchera les pages V2 dans '{self.v2_path}'")

    def execute(self, document_data_v1: List[Dict[str, Any]], file_path_v1: Path) -> List[Dict[str, Any]]:
        # Construire le chemin potentiel vers le fichier dans le dossier v2
        relative_path = file_path_v1.relative_to(self.source_path)
        file_path_v2 = self.v2_path / relative_path

        # Si pas de version V2, on retourne simplement la V1
        if not file_path_v2.exists():
            return document_data_v1

        # --- LOGIQUE DE FUSION PAR PAGE ---
        print(f"    -> Fusion par page pour {file_path_v1.name}...")
        
        # Charger les pages recalculées de la V2
        with open(file_path_v2, "r", encoding="utf-8") as f:
            document_data_v2 = json.load(f)
        
        # Créer un dictionnaire des pages V2 pour un accès rapide (clé = index de la page)
        v2_pages_map = {page['index']: page for page in document_data_v2}
        
        merged_document = []
        # Parcourir les pages du document original V1
        for page_v1 in document_data_v1:
            page_index = page_v1.get('index')
            
            # Si une version de cette page existe dans notre map V2, on l'utilise
            if page_index in v2_pages_map:
                merged_document.append(v2_pages_map[page_index])
            else:
                # Sinon, on garde la page originale V1
                merged_document.append(page_v1)
                
        return merged_document


if __name__ == "__main__":
    STATES_DIR = ROOT_DIR / "states"
    SOURCE_V1_DIR = STATES_DIR / "result_json"
    SOURCE_V2_DIR = STATES_DIR / "result_json_v2"
    OUTPUT_DIR = STATES_DIR / "result_json_merged"

    print(f"--- Lancement de la Passe 1 : Fusion de '{SOURCE_V1_DIR.name}' et '{SOURCE_V2_DIR.name}' ---")

    data_manager = DataSetManager(source_dir=str(SOURCE_V1_DIR), output_dir=str(OUTPUT_DIR))

    merging_manager = MergingDocumentManager(
        page_manager=data_manager.page_manager,
        v2_dir=str(SOURCE_V2_DIR),
        source_dir=str(SOURCE_V1_DIR)
    )

    data_manager.document_manager = merging_manager
    print("Injection du MergingDocumentManager (Page-Level) dans le système.")
    data_manager.process_dataset()