import os
import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from pathlib import Path
from row_detector import RowDetector # Importation du nouveau détecteur

@dataclass
class VisualizationConfig:
    figsize: Tuple[int, int] = (20, 25)
    layout_line_width_detected: float = 3.0
    layout_line_width_regular: float = 1.0
    padding: int = 50

@dataclass
class ColorScheme:
    regular_layout: str = 'blue'
    # Nouvelle couleur pour les layouts détectés
    horizontal_layout: str = 'orange' 
    text_box_alpha: float = 0.7

class PageVisualizer:
    def __init__(self, config: Optional[VisualizationConfig] = None, color_scheme: Optional[ColorScheme] = None):
        self.config = config or VisualizationConfig()
        self.colors = color_scheme or ColorScheme()

    def visualize_page(self, page_data: Dict[str, Any], detected_indices: List[int]) -> plt.Figure:
        fig, ax = plt.subplots(figsize=self.config.figsize)
        
        all_bboxes = [layout['bbox_layout'] for layout in page_data['page']]
        x_coords = [bbox[0] for bbox in all_bboxes] + [bbox[2] for bbox in all_bboxes]
        y_coords = [bbox[1] for bbox in all_bboxes] + [bbox[3] for bbox in all_bboxes]
        
        ax.set_xlim(min(x_coords) - self.config.padding, max(x_coords) + self.config.padding)
        ax.set_ylim(max(y_coords) + self.config.padding, min(y_coords) - self.config.padding)
        ax.set_title(f"Page {page_data['index']} - Horizontal Layout Detection", fontsize=16)

        for idx, layout_data in enumerate(page_data['page']):
            bbox = layout_data['bbox_layout']
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            
            is_detected = idx in detected_indices
            
            edge_color = self.colors.horizontal_layout if is_detected else self.colors.regular_layout
            line_width = self.config.layout_line_width_detected if is_detected else self.config.layout_line_width_regular
            
            rect = patches.Rectangle(
                (bbox[0], bbox[1]), width, height,
                linewidth=line_width,
                edgecolor=edge_color,
                facecolor='none',
                alpha=self.colors.text_box_alpha
            )
            ax.add_patch(rect)
            ax.text(bbox[0], bbox[1] - 5, f"Layout {idx}", fontsize=8, color=edge_color)

        ax.grid(True, linestyle='--')
        legend_elements = [
            patches.Patch(edgecolor=self.colors.horizontal_layout, facecolor='none', label='Detected Horizontal Layout'),
            patches.Patch(edgecolor=self.colors.regular_layout, facecolor='none', label='Regular Layout')
        ]
        ax.legend(handles=legend_elements, loc='upper right')
        
        return fig

class DocumentProcessor:
    def __init__(self, base_dir: str = "result_json", output_dir: str = "horizontal_output"):
        self.base_dir = Path(base_dir)
        self.output_dir = Path(output_dir)
        self.row_detector = RowDetector(min_layouts_in_row=3)
        self.visualizer = PageVisualizer()

    def process_documents(self):
        if not self.base_dir.exists():
            print(f"Le dossier de base '{self.base_dir}' n'existe pas.")
            return
        
        self.output_dir.mkdir(exist_ok=True)
        
        print("Début du traitement...")
        for year_dir in sorted(self.base_dir.iterdir()):
            try:
                # Traite uniquement les dossiers dont le nom est une année entre 1962 et 2025
                year = int(year_dir.name)
                if year_dir.is_dir() and 1962 <= year <= 2025:
                    print(f"--- Traitement de l'année : {year} ---")
                    self._process_year(year_dir)
            except ValueError:
                # Ignore les dossiers qui ne sont pas des années
                continue
        print("Traitement terminé.")

    def _process_year(self, year_dir: Path):
        year_output_dir = self.output_dir / year_dir.name
        year_output_dir.mkdir(exist_ok=True)
        
        for json_file in sorted(year_dir.glob("*.json")):
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            for page_data in data:
                detected_indices = self.row_detector.detect_horizontal_layouts(page_data)
                
                if detected_indices:
                    print(f"  Détection sur {json_file.name}, Page {page_data['index']}. Layouts: {detected_indices}")
                    
                    fig = self.visualizer.visualize_page(page_data, detected_indices)
                    save_path = year_output_dir / f"{json_file.stem}_page{page_data['index']}_detected.png"
                    fig.savefig(save_path, dpi=150, bbox_inches='tight')
                    plt.close(fig)

if __name__ == "__main__":
    processor = DocumentProcessor()
    processor.process_documents()