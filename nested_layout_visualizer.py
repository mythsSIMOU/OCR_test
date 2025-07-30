# nested_layout_visualizer.py

import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path
from typing import Dict, List, Tuple, Any
from nested_detector import NestedLayoutsDetector

class PageVisualizer:
    """Gère la création des visualisations pour les layouts imbriqués."""
    
    def visualize_page(self, page_data: Dict[str, Any], nested_pairs: List[Tuple[int, int]]) -> plt.Figure:
        fig, ax = plt.subplots(figsize=(20, 25))

        # Couleurs
        COLOR_OUTER = 'red'
        COLOR_INNER = 'green'
        COLOR_REGULAR = 'blue'

        # Calcul des dimensions pour cadrer la figure
        all_bboxes = [layout['bbox_layout'] for layout in page_data['page']]
        x_coords = [bbox[0] for bbox in all_bboxes] + [bbox[2] for bbox in all_bboxes]
        y_coords = [bbox[1] for bbox in all_bboxes] + [bbox[3] for bbox in all_bboxes]
        padding = 50
        ax.set_xlim(min(x_coords) - padding, max(x_coords) + padding)
        ax.set_ylim(max(y_coords) + padding, min(y_coords) - padding)
        ax.set_title(f"Page {page_data['index']} - Nested Layout Detection", fontsize=16)

        # Dessiner tous les layouts
        for idx, layout_data in enumerate(page_data['page']):
            bbox = layout_data['bbox_layout']
            width, height = bbox[2] - bbox[0], bbox[3] - bbox[1]

            # Déterminer la couleur et le style
            edge_color = COLOR_REGULAR
            line_width = 1.0
            for outer_idx, inner_idx in nested_pairs:
                if idx == outer_idx:
                    edge_color = COLOR_OUTER
                    line_width = 2.5
                    break
                elif idx == inner_idx:
                    edge_color = COLOR_INNER
                    line_width = 2.5
                    break
            
            rect = patches.Rectangle((bbox[0], bbox[1]), width, height, linewidth=line_width, edgecolor=edge_color, facecolor='none')
            ax.add_patch(rect)
            ax.text(bbox[0], bbox[1] - 5, f"Layout {idx}", fontsize=9, color=edge_color)

        # Dessiner les flèches pour montrer les relations
        for outer_idx, inner_idx in nested_pairs:
            outer_bbox = page_data['page'][outer_idx]['bbox_layout']
            inner_bbox = page_data['page'][inner_idx]['bbox_layout']
            
            center_outer_x = (outer_bbox[0] + outer_bbox[2]) / 2
            center_outer_y = (outer_bbox[1] + outer_bbox[3]) / 2
            center_inner_x = (inner_bbox[0] + inner_bbox[2]) / 2
            center_inner_y = (inner_bbox[1] + inner_bbox[3]) / 2

            ax.arrow(center_outer_x, center_outer_y, 
                     center_inner_x - center_outer_x, 
                     center_inner_y - center_outer_y,
                     head_width=15, head_length=15, fc='black', ec='black', length_includes_head=True, alpha=0.6)

        ax.grid(True, linestyle='--')
        return fig

class DocumentProcessor:
    def __init__(self, base_dir: str = "result_json", output_dir: str = "nested_output"):
        self.base_dir = Path(base_dir)
        self.output_dir = Path(output_dir)
        self.detector = NestedLayoutsDetector()
        self.visualizer = PageVisualizer()

    def process_documents(self):
        if not self.base_dir.exists():
            print(f"Le dossier de base '{self.base_dir}' n'existe pas.")
            return
        
        self.output_dir.mkdir(exist_ok=True)
        print("Début de la détection des layouts imbriqués...")

        for json_file in sorted(self.base_dir.rglob("*.json")):
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            for page_data in data:
                nested_pairs = self.detector.detect(page_data)
                
                if nested_pairs:
                    print(f"  Détection dans {json_file.name}, Page {page_data['index']}: {len(nested_pairs)} paire(s) trouvée(s).")
                    
                    fig = self.visualizer.visualize_page(page_data, nested_pairs)
                    
                    # S'assurer que le dossier de sortie pour l'année existe
                    year_output_dir = self.output_dir / json_file.parent.name
                    year_output_dir.mkdir(exist_ok=True)
                    
                    save_path = year_output_dir / f"{json_file.stem}_page{page_data['index']}_nested.png"
                    fig.savefig(save_path, dpi=150, bbox_inches='tight')
                    plt.close(fig)

        print("Traitement terminé.")

if __name__ == "__main__":
    processor = DocumentProcessor()
    processor.process_documents()