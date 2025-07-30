# multi_layout_visualizer.py

import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

# Importation du nouveau détecteur avec la nouvelle logique
from row_detector import ThreeColumnsMajorityDetector

@dataclass
class VisualizationConfig:
    figsize: Tuple[int, int] = (20, 25)
    layout_line_width: float = 2.0
    padding: int = 50

@dataclass
class ColorScheme:
    detected_layout: str = 'orange' 
    text_box_alpha: float = 0.8

class PageVisualizer:
    def __init__(self, config: Optional[VisualizationConfig] = None, color_scheme: Optional[ColorScheme] = None):
        self.config = config or VisualizationConfig()
        self.colors = color_scheme or ColorScheme()

    # La méthode est simplifiée : elle ne visualise qu'une page DÉTECTÉE
    def visualize_detected_page(self, page_data: Dict[str, Any]) -> plt.Figure:
        fig, ax = plt.subplots(figsize=self.config.figsize)
        
        all_bboxes = [layout['bbox_layout'] for layout in page_data['page']]
        x_coords = [bbox[0] for bbox in all_bboxes] + [bbox[2] for bbox in all_bboxes]
        y_coords = [bbox[1] for bbox in all_bboxes] + [bbox[3] for bbox in all_bboxes]
        
        ax.set_xlim(min(x_coords) - self.config.padding, max(x_coords) + self.config.padding)
        ax.set_ylim(max(y_coords) + self.config.padding, min(y_coords) - self.config.padding)
        ax.set_title(f"Page {page_data['index']} - Horizontal Layout Case Detected", fontsize=16)

        # Puisque cette méthode n'est appelée que pour les pages détectées, tous les layouts sont colorés
        for idx, layout_data in enumerate(page_data['page']):
            bbox = layout_data['bbox_layout']
            width, height = bbox[2] - bbox[0], bbox[3] - bbox[1]
            
            rect = patches.Rectangle(
                (bbox[0], bbox[1]), width, height,
                linewidth=self.config.layout_line_width,
                edgecolor=self.colors.detected_layout,
                facecolor='none',
                alpha=self.colors.text_box_alpha
            )
            ax.add_patch(rect)
            ax.text(bbox[0], bbox[1] - 5, f"Layout {idx}", fontsize=8, color=self.colors.detected_layout)

        ax.grid(True, linestyle='--')
        legend_elements = [
            patches.Patch(edgecolor=self.colors.detected_layout, facecolor='none', label='Detected Page'),
        ]
        ax.legend(handles=legend_elements, loc='upper right')
        
        return fig

class DocumentProcessor:
    def __init__(self, base_dir: str = "result_json", output_dir: str = "horizontal_output_scanline"):
        self.base_dir = Path(base_dir)
        self.output_dir = Path(output_dir)
        self.row_detector = ThreeColumnsMajorityDetector() # Utilise la nouvelle version
        self.visualizer = PageVisualizer()

    def process_documents(self):
        if not self.base_dir.exists():
            print(f"Le dossier de base '{self.base_dir}' n'existe pas.")
            return
        
        self.output_dir.mkdir(exist_ok=True)
        print("Début du traitement avec l'algorithme de balayage...")
        
        for json_file in sorted(self.base_dir.rglob("*.json")):
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            for page_data in data:
                # La fonction de détection retourne maintenant un simple booléen
                is_complex_page = self.row_detector.detect(page_data)
                
                if is_complex_page:
                    print(f"  Détection sur {json_file.name}, Page {page_data['index']}.")
                    
                    # La méthode de visualisation n'a plus besoin des indices
                    fig = self.visualizer.visualize_detected_page(page_data)
                    
                    year_dir = self.output_dir / json_file.parent.name
                    year_dir.mkdir(exist_ok=True)
                    save_path = year_dir / f"{json_file.stem}_page{page_data['index']}_detected.png"
                    
                    fig.savefig(save_path, dpi=150, bbox_inches='tight')
                    plt.close(fig)

        print("Traitement terminé.")

if __name__ == "__main__":
    processor = DocumentProcessor()
    processor.process_documents()