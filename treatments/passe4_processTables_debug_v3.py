import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict

# --- Étape 0 : Structure de Données ---
@dataclass
class TableCell:
    box: List[float]
    texts: List[str] = field(default_factory=list)
    texts_bboxes: List[List[float]] = field(default_factory=list)

    @property
    def x1(self): return self.box[0]
    @property
    def y1(self): return self.box[1]
    @property
    def center_y(self): return (self.box[1] + self.box[3]) / 2

# --- Fonctions Utilitaires ---
def get_intersection(box1: List[float], box2: List[float]) -> Optional[List[float]]:
    x1, y1, x2, y2 = max(box1[0], box2[0]), max(box1[1], box2[1]), min(box1[2], box2[2]), min(box1[3], box2[3])
    if x1 < x2 and y1 < y2:
        return [x1, y1, x2, y2]
    return None

def get_area(box: List[float]) -> float:
    return (box[2] - box[0]) * (box[3] - box[1])

def get_center(box: List[float]) -> tuple[float, float]:
    return ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)

def is_contained(point: tuple[float, float], outer_box: List[float]) -> bool:
    return (outer_box[0] <= point[0] <= outer_box[2] and outer_box[1] <= point[1] <= outer_box[3])

class TableProcessor:
    def process_table_layout(self, text_layout: Dict[str, Any], table_structure: Dict[str, Any]) -> Dict[str, Any]:
        
        # Étapes 1 à 4: Construction des cellules et affectation du texte (inchangées et correctes)
        rows_bboxes_model = [d['bbox'] for d in table_structure['table_data'] if d['label'] in ('table row', 'table row header')]
        cols_bboxes_model = [d['bbox'] for d in table_structure['table_data'] if d['label'] in ('table column', 'table column header')]
        
        unit_cells_grid = [TableCell(box=cell_box) for r_box in rows_bboxes_model for c_box in cols_bboxes_model if (cell_box := get_intersection(r_box, c_box)) and get_area(cell_box) > 0]
        
        super_cells_data = [d['bbox'] for d in table_structure['table_data'] if d['label'] in ('table spanning cell', 'table column header', 'table row header')]
        unit_cells_to_keep = [uc for uc in unit_cells_grid if not any(is_contained(get_center(uc.box), sp_box) for sp_box in super_cells_data)]
        super_cells = [TableCell(box=sp_box) for sp_box in super_cells_data]
        cellulesArray = unit_cells_to_keep + super_cells
        
        if not cellulesArray: return text_layout

        for text_bbox, text_content in zip(text_layout.get('bbox_text', []), text_layout.get('text', [])):
            best_cell = max(cellulesArray, key=lambda cell: get_area(get_intersection(text_bbox, cell.box) or [0,0,0,0]))
            if get_area(get_intersection(text_bbox, best_cell.box) or [0,0,0,0]) > 0:
                best_cell.texts_bboxes.append(text_bbox)
                best_cell.texts.append(text_content)
                
        for cell in cellulesArray:
            if len(cell.texts) > 1:
                sorted_items = sorted(zip(cell.texts_bboxes, cell.texts), key=lambda item: (item[0][1], item[0][0]))
                cell.texts_bboxes, cell.texts = list(zip(*sorted_items)) if sorted_items else ([], [])

        # --- ÉTAPE 5 (FINALE) : Combinaison de la déduction de ligne ET de la duplication ---
        structured_rows = []
        reference_cols = sorted(cols_bboxes_model, key=lambda c: c[0])
        
        # 1. Déduire les lignes en groupant les cellules par hauteur
        row_groups = defaultdict(list)
        snap_grid_size = 15 # Tolérance verticale
        for cell in cellulesArray:
            snapped_y = int(cell.center_y / snap_grid_size) * snap_grid_size
            row_groups[snapped_y].append(cell)

        # 2. Pour chaque ligne déduite, appliquer la duplication
        for snapped_y in sorted(row_groups.keys()):
            cells_in_row = row_groups[snapped_y]
            if not cells_in_row: continue

            flat_row = []
            for ref_col_box in reference_cols:
                ref_col_center = get_center(ref_col_box)
                found_cell_text = ""
                for cell in cells_in_row:
                    if is_contained(ref_col_center, cell.box):
                        found_cell_text = " ".join(cell.texts)
                        break
                flat_row.append(found_cell_text)

            if any(cell_text for cell_text in flat_row):
                structured_rows.append(flat_row)
        # --- FIN DE LA LOGIQUE FINALE ---
            
        # --- ÉTAPE 6: Sauvegarde ---
        processed_layout = text_layout.copy()
        processed_layout['structured_table_data'] = structured_rows
        return processed_layout

if __name__ == "__main__":
    ROOT_DIR = Path(__file__).resolve().parents[1]
    STATES_DIR = ROOT_DIR / "states"
    
    original_doc_path = STATES_DIR / "result_json" / "2024" / "F2024006.json"
    table_doc_path = STATES_DIR / "result_json_tables" / "2024" / "F2024006_table.json"
    PAGE_INDEX_TO_DEBUG = 6

    print(f"Lancement du débogage final pour la page {PAGE_INDEX_TO_DEBUG} de {original_doc_path.name}")

    with open(original_doc_path, "r", encoding="utf-8") as f: original_doc = json.load(f)
    with open(table_doc_path, "r", encoding="utf-8") as f: tables_doc = json.load(f)
        
    original_page = next((p for p in original_doc if p['index'] == PAGE_INDEX_TO_DEBUG), None)
    table_page_info = next((t for t in tables_doc if t['index'] == PAGE_INDEX_TO_DEBUG), None)
    
    if original_page and table_page_info:
        table_text_layout = next((l for l in original_page['page'] if l['position'] == 17), None)
        table_structure = table_page_info['page_data'][0]
        
        if table_text_layout:
            processor = TableProcessor()
            result_layout = processor.process_table_layout(table_text_layout, table_structure)
            
            output_path = Path(__file__).parent / f"debug_{original_doc_path.stem}_page_{PAGE_INDEX_TO_DEBUG}_final.json"
            
            print("\n--- Sauvegarde du résultat final ---")
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result_layout, f, indent=2, ensure_ascii=False)
            
            print(f"Le layout traité a été sauvegardé dans : {output_path}")