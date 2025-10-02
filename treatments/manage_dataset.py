# manage_dataset.py (Corrigé)

import json
from pathlib import Path
from typing import Dict, List, Any

class LayoutManager:
    def execute(self, layout_data: Dict[str, Any]) -> Dict[str, Any]:
        return layout_data

class PageManager:
    def __init__(self, layout_manager: LayoutManager):
        self.layout_manager = layout_manager

    # --- MODIFICATION 1 : La signature de la méthode est mise à jour ---
    # Elle accepte maintenant file_path, même si la classe de base ne l'utilise pas.
    def execute(self, page_data: Dict[str, Any], file_path: Path) -> Dict[str, Any]:
        processed_layouts = [self.layout_manager.execute(layout) for layout in page_data.get('page', [])]
        new_page_data = page_data.copy()
        new_page_data['page'] = processed_layouts
        return new_page_data

class DocumentManager:
    def __init__(self, page_manager: PageManager):
        self.page_manager = page_manager

    def execute(self, document_data: List[Dict[str, Any]], file_path: Path) -> List[Dict[str, Any]]:
        # --- MODIFICATION 2 : On passe maintenant file_path à chaque appel de page_manager.execute ---
        return [self.page_manager.execute(page, file_path) for page in document_data]

class DataSetManager:
    def __init__(self, source_dir: str, output_dir: str):
        self.source_path = Path(source_dir)
        self.output_path = Path(output_dir)
        
        self.layout_manager = LayoutManager()
        self.page_manager = PageManager(self.layout_manager)
        self.document_manager = DocumentManager(self.page_manager)
        
        print(f"DataSetManager initialisé pour la source '{source_dir}' et la sortie '{output_dir}'")

    def process_dataset(self):
        if not self.source_path.exists():
            print(f"Erreur : Le dossier source '{self.source_path}' n'existe pas.")
            return

        self.output_path.mkdir(exist_ok=True)
        print(f"Traitement en cours... Sortie dans '{self.output_path}'")

        for year_dir in sorted(self.source_path.iterdir()):
            if not year_dir.is_dir():
                continue
            
            output_year_dir = self.output_path / year_dir.name
            output_year_dir.mkdir(exist_ok=True)
            
            print(f"  Traitement de l'année : {year_dir.name}")
            for json_file in sorted(year_dir.glob("*.json")):
                with open(json_file, "r", encoding="utf-8") as f:
                    original_document = json.load(f)
                
                processed_document = self.document_manager.execute(original_document, json_file)
                
                output_file_path = output_year_dir / json_file.name
                with open(output_file_path, "w", encoding="utf-8") as f:
                    json.dump(processed_document, f, indent=2, ensure_ascii=False)
        
        print("Traitement du dataset terminé.")