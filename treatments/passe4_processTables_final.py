import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import shutil

# --- Structure de Données ---
@dataclass
class TableCell:
    """Structure de données pour une cellule de tableau."""
    box: List[float]
    texts: List[str] = field(default_factory=list)
    texts_bboxes: List[List[float]] = field(default_factory=list)

    @property
    def x1(self): return self.box[0]
    @property
    def y1(self): return self.box[1]

# --- Fonctions Utilitaires ---
def get_intersection(box1: List[float], box2: List[float]) -> Optional[List[float]]:
    """Calcule la boîte d'intersection entre deux boîtes."""
    x1, y1, x2, y2 = max(box1[0], box2[0]), max(box1[1], box2[1]), min(box1[2], box2[2]), min(box1[3], box2[3])
    if x1 < x2 and y1 < y2:
        return [x1, y1, x2, y2]
    return None

def get_area(box: List[float]) -> float:
    """Calcule l'aire d'une boîte."""
    return (box[2] - box[0]) * (box[3] - box[1])

def is_contained(inner_box: List[float], outer_box: List[float]) -> bool:
    """Vérifie si le centre d'une boîte est contenu dans une autre."""
    center_x, center_y = (inner_box[0] + inner_box[2]) / 2, (inner_box[1] + inner_box[3]) / 2
    return (outer_box[0] <= center_x <= outer_box[2] and outer_box[1] <= center_y <= outer_box[3])

class TableProcessor:
    """Contient la logique de traitement des tableaux."""

    def process_table_layout(self, text_layout: Dict[str, Any], table_structure: Dict[str, Any]) -> Dict[str, Any]:
        """
        Traite un layout de tableau en appliquant la passe des tableaux.
        
        Args:
            text_layout: Layout avec label "Table" depuis result_json
            table_structure: Structure du tableau depuis result_json_tables
            
        Returns:
            Layout modifié avec structured_table_data
        """
        # ÉTAPE 1: Générer toutes les cellules possibles du tableau
        rows = [d['bbox'] for d in table_structure['table_data'] if d['label'] in ('table row', 'table row header')]
        cols = [d['bbox'] for d in table_structure['table_data'] if d['label'] in ('table column', 'table column header')]
        
        print(f"    Trouvé {len(rows)} lignes et {len(cols)} colonnes")
        
        cellulesArray = []
        for r_box in rows:
            for c_box in cols:
                cell_box = get_intersection(r_box, c_box)
                if cell_box and get_area(cell_box) > 0:
                    cellulesArray.append(TableCell(box=cell_box))
        
        print(f"    Généré {len(cellulesArray)} cellules unitaires")
        
        # ÉTAPE 2: Minimisation des cellules (gestion des 'merged cells')
        spanning_cells_data = [d['bbox'] for d in table_structure['table_data'] if d['label'] == 'table spanning cell']
        print(f"    Trouvé {len(spanning_cells_data)} cellules fusionnées")
        
        unit_cells_to_keep = [
            unit_cell for unit_cell in cellulesArray 
            if not any(is_contained(unit_cell.box, sp_box) for sp_box in spanning_cells_data)
        ]
        
        spanning_cells = [TableCell(box=sp_box) for sp_box in spanning_cells_data]
        cellulesArray = unit_cells_to_keep + spanning_cells
        
        print(f"    Après minimisation: {len(cellulesArray)} cellules finales")
        
        if not cellulesArray:
            print("    Avertissement : Aucune cellule n'a pu être générée.")
            return text_layout

        # ÉTAPE 3: Affectation du texte
        text_boxes = text_layout.get('bbox_text', [])
        texts = text_layout.get('text', [])
        
        if len(text_boxes) != len(texts):
            print(f"    Avertissement: Nombre de bbox_text ({len(text_boxes)}) != nombre de text ({len(texts)})")
            min_len = min(len(text_boxes), len(texts))
            text_boxes = text_boxes[:min_len]
            texts = texts[:min_len]
        
        print(f"    Traitement de {len(text_boxes)} éléments de texte")
        
        for text_bbox, text_content in zip(text_boxes, texts):
            best_cell = max(cellulesArray, key=lambda cell: get_area(get_intersection(text_bbox, cell.box) or [0,0,0,0]))
            intersection_area = get_area(get_intersection(text_bbox, best_cell.box) or [0,0,0,0])
            
            if intersection_area > 0:
                best_cell.texts_bboxes.append(text_bbox)
                best_cell.texts.append(text_content)
                
        # ÉTAPE 4: Ordonner le texte à l'intérieur de chaque cellule
        for cell in cellulesArray:
            if len(cell.texts) > 1:
                sorted_items = sorted(zip(cell.texts_bboxes, cell.texts), key=lambda item: (item[0][1], item[0][0]))
                if sorted_items:
                    cell.texts_bboxes, cell.texts = list(zip(*sorted_items))
                else:
                    cell.texts_bboxes, cell.texts = [], []

        # ÉTAPE 5: Extraction des lignes structurées
        structured_rows = []
        sorted_rows = sorted(rows, key=lambda b: b[1])  # Trier par Y
        
        for r_box in sorted_rows:
            row_center_y = (r_box[1] + r_box[3]) / 2
            
            # Trouver toutes les cellules qui appartiennent à cette ligne
            cells_in_row = []
            for cell in cellulesArray:
                cell_center_y = (cell.box[1] + cell.box[3]) / 2
                if abs(cell_center_y - row_center_y) < 10:  # Tolérance de 10 pixels
                    cells_in_row.append(cell)
            
            # Trier les cellules par X (gauche vers droite)
            sorted_cells = sorted(cells_in_row, key=lambda c: c.x1)
            
            # Extraire le texte de chaque cellule
            row_texts = []
            for cell in sorted_cells:
                cell_text = " ".join(cell.texts) if cell.texts else ""
                row_texts.append(cell_text)
            
            structured_rows.append(row_texts)
            
        print(f"    Généré {len(structured_rows)} lignes structurées")
        
        # ÉTAPE 6: Sauvegarde dans une nouvelle clé
        processed_layout = text_layout.copy()
        processed_layout['structured_table_data'] = structured_rows
        
        return processed_layout

class BatchTableProcessor:
    """Traite tous les tableaux en lot."""
    
    def __init__(self, base_dir: str = "states"):
        self.base_dir = Path(base_dir)
        self.result_json_dir = self.base_dir / "result_json"
        self.result_json_tables_dir = self.base_dir / "result_json_tables"
        self.output_dir = self.base_dir / "result_json_processed"
        
        self.table_processor = TableProcessor()
        
        # Statistiques
        self.stats = {
            'files_processed': 0,
            'pages_processed': 0,
            'tables_processed': 0,
            'errors': 0
        }
    
    def process_all_documents(self):
        """Traite tous les documents avec tableaux."""
        print("=== Début du traitement en lot des tableaux ===")
        
        # Créer le dossier de sortie
        self.output_dir.mkdir(exist_ok=True)
        
        # Parcourir tous les fichiers de tables
        for table_file in self.result_json_tables_dir.rglob("*.json"):
            try:
                self.process_document(table_file)
            except Exception as e:
                print(f"Erreur lors du traitement de {table_file}: {e}")
                self.stats['errors'] += 1
        
        self.print_statistics()
    
    def process_document(self, table_file_path: Path):
        """Traite un document spécifique."""
        # Construire le chemin du fichier original correspondant
        relative_path = table_file_path.relative_to(self.result_json_tables_dir)
        
        # Enlever le suffixe "_table" du nom de fichier
        original_filename = table_file_path.stem
        if original_filename.endswith("_table"):
            original_filename = original_filename[:-6]  # Enlever "_table"
        original_filename += ".json"
        
        original_file_path = self.result_json_dir / relative_path.parent / original_filename
        
        if not original_file_path.exists():
            print(f"Fichier original non trouvé: {original_file_path}")
            return
        
        print(f"\nTraitement de {table_file_path.name} avec {original_file_path.name}")
        
        # Charger les fichiers
        with open(table_file_path, "r", encoding="utf-8") as f:
            tables_doc = json.load(f)
        
        with open(original_file_path, "r", encoding="utf-8") as f:
            original_doc = json.load(f)
        
        # Créer une copie du document original pour modification
        processed_doc = json.loads(json.dumps(original_doc))  # Deep copy
        
        # Traiter chaque page avec tableaux
        tables_by_page = {table_info['index']: table_info for table_info in tables_doc}
        
        for page in processed_doc:
            page_index = page['index']
            
            if page_index in tables_by_page:
                table_page_info = tables_by_page[page_index]
                self.process_page_tables(page, table_page_info)
                self.stats['pages_processed'] += 1
        
        # Sauvegarder le document traité
        output_file_path = self.output_dir / relative_path.parent / original_filename
        output_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file_path, "w", encoding="utf-8") as f:
            json.dump(processed_doc, f, indent=2, ensure_ascii=False)
        
        print(f"Document traité sauvegardé: {output_file_path}")
        self.stats['files_processed'] += 1
    
    def process_page_tables(self, page: Dict[str, Any], table_page_info: Dict[str, Any]):
        """Traite tous les tableaux d'une page."""
        page_layouts = page.get('page', [])
        table_structures = table_page_info.get('page_data', [])
        
        # Trouver tous les layouts avec label "Table"
        table_layouts = [layout for layout in page_layouts if layout.get('label') == 'Table']
        
        print(f"  Page {page['index']}: {len(table_layouts)} layout(s) Table, {len(table_structures)} structure(s)")
        
        if not table_layouts or not table_structures:
            return
        
        # Associer chaque layout de table avec sa structure
        # Pour simplifier, on associe dans l'ordre (peut être amélioré avec une logique de correspondance spatiale)
        for i, table_layout in enumerate(table_layouts):
            if i < len(table_structures):
                table_structure = table_structures[i]
                print(f"    Traitement du tableau {i+1}")
                
                try:
                    processed_layout = self.table_processor.process_table_layout(table_layout, table_structure)
                    
                    # Remplacer le layout original par le layout traité
                    layout_index = page_layouts.index(table_layout)
                    page_layouts[layout_index] = processed_layout
                    
                    self.stats['tables_processed'] += 1
                    print(f"    Tableau {i+1} traité avec succès")
                    
                except Exception as e:
                    print(f"    Erreur lors du traitement du tableau {i+1}: {e}")
                    self.stats['errors'] += 1
            else:
                print(f"    Pas de structure disponible pour le tableau {i+1}")
    
    def print_statistics(self):
        """Affiche les statistiques de traitement."""
        print("\n=== Statistiques de traitement ===")
        print(f"Fichiers traités: {self.stats['files_processed']}")
        print(f"Pages traitées: {self.stats['pages_processed']}")
        print(f"Tableaux traités: {self.stats['tables_processed']}")
        print(f"Erreurs rencontrées: {self.stats['errors']}")
        print("=" * 40)

def main():
    """Fonction principale."""
    # Changer vers le répertoire parent pour accéder au dossier states
    current_dir = Path(__file__).resolve().parent
    base_dir = current_dir.parent / "states"
    
    if not base_dir.exists():
        print(f"Erreur: Le dossier {base_dir} n'existe pas.")
        print(f"Structure attendue: {base_dir}/result_json et {base_dir}/result_json_tables")
        return
    
    processor = BatchTableProcessor(str(base_dir))
    processor.process_all_documents()

if __name__ == "__main__":
    main()