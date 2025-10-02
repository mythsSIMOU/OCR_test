import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

# --- Étape 0 : Structure de Données ---
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
        
        # ÉTAPE 1: Générer toutes les cellules possibles du tableau
        rows = [d['bbox'] for d in table_structure['table_data'] if d['label'] in ('table row', 'table row header')]
        cols = [d['bbox'] for d in table_structure['table_data'] if d['label'] in ('table column', 'table column header')]
        
        cellulesArray = [TableCell(box=cell_box) for r_box in rows for c_box in cols if (cell_box := get_intersection(r_box, c_box)) and get_area(cell_box) > 0]
        
        # ÉTAPE 2: Minimization des cellules (gestion des 'merged cells')
        spanning_cells_data = [d['bbox'] for d in table_structure['table_data'] if d['label'] == 'table spanning cell']
        
        unit_cells_to_keep = [
            unit_cell for unit_cell in cellulesArray 
            if not any(is_contained(unit_cell.box, sp_box) for sp_box in spanning_cells_data)
        ]
        
        spanning_cells = [TableCell(box=sp_box) for sp_box in spanning_cells_data]
        cellulesArray = unit_cells_to_keep + spanning_cells
        
        if not cellulesArray:
            print("Avertissement : Aucune cellule n'a pu être générée.")
            return text_layout

        # ÉTAPE 3: Affectation du texte
        all_text_boxes = zip(text_layout.get('bbox_text', []), text_layout.get('text', []))
        for text_bbox, text_content in all_text_boxes:
            best_cell = max(cellulesArray, key=lambda cell: get_area(get_intersection(text_bbox, cell.box) or [0,0,0,0]))
            
            if get_area(get_intersection(text_bbox, best_cell.box) or [0,0,0,0]) > 0:
                best_cell.texts_bboxes.append(text_bbox)
                best_cell.texts.append(text_content)
                
        # ÉTAPE 4: Ordonner le texte à l'intérieur de chaque cellule
        for cell in cellulesArray:
            if len(cell.texts) > 1:
                sorted_items = sorted(zip(cell.texts_bboxes, cell.texts), key=lambda item: (item[0][1], item[0][0]))
                cell.texts_bboxes, cell.texts = list(zip(*sorted_items)) if sorted_items else ([], [])

        # ÉTAPE 5: Extraction des lignes structurées
        structured_rows = []
        for r_box in sorted(rows, key=lambda b: b[1]):
            row_center_y = (r_box[1] + r_box[3]) / 2
            
            cells_in_row = [cell for cell in cellulesArray if abs(((cell.box[1] + cell.box[3]) / 2) - row_center_y) < 10]
            sorted_cells = sorted(cells_in_row, key=lambda c: c.x1)
            
            row_texts = [" ".join(cell.texts) for cell in sorted_cells]
            structured_rows.append(row_texts)
            
        # ÉTAPE 6: Sauvegarde dans une nouvelle clé
        processed_layout = text_layout.copy()
        processed_layout['structured_table_data'] = structured_rows
        
        return processed_layout

if __name__ == "__main__":
    
    ROOT_DIR = Path(__file__).resolve().parents[1]
    STATES_DIR = ROOT_DIR / "states"
    
    original_doc_path = STATES_DIR / "result_json" / "2024" / "F2024006.json"
    table_doc_path = STATES_DIR / "result_json_tables" / "2024" / "F2024006_table.json"
    
    PAGE_INDEX_TO_DEBUG = 6

    print(f"Lancement du débogage pour la page {PAGE_INDEX_TO_DEBUG} de {original_doc_path.name}")

    with open(original_doc_path, "r", encoding="utf-8") as f:
        original_doc = json.load(f)
    with open(table_doc_path, "r", encoding="utf-8") as f:
        tables_doc = json.load(f)
        
    original_page = next((p for p in original_doc if p['index'] == PAGE_INDEX_TO_DEBUG), None)
    table_page_info = next((t for t in tables_doc if t['index'] == PAGE_INDEX_TO_DEBUG), None)

    if not original_page or not table_page_info:
        print(f"Erreur : Impossible de trouver la page {PAGE_INDEX_TO_DEBUG} dans les fichiers.")
    else:
        table_text_layout = next((l for l in original_page['page'] if l['position'] == 17), None)
        table_structure = table_page_info['page_data'][0]
        
        if not table_text_layout:
            print("Erreur : Impossible de trouver le layout du tableau (position 17) dans la page.")
        else:
            print(table_text_layout)
            processor = TableProcessor()
            result_layout = processor.process_table_layout(table_text_layout, table_structure)
            
            # --- MODIFIÉ : Sauvegarde du résultat dans un fichier JSON ---
            output_path = Path(__file__).parent / f"debug_{original_doc_path.stem}_page_{PAGE_INDEX_TO_DEBUG}.json"
            
            print("\n--- Sauvegarde du résultat ---")
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result_layout, f, indent=2, ensure_ascii=False)
            
            print(f"Le layout traité a été sauvegardé dans : {output_path}")