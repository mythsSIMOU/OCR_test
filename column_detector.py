import numpy as np
from scipy.stats import gaussian_kde
from collections import defaultdict
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass

@dataclass
class TextBox:
    """Represents a text box with coordinates and optional text content."""
    x_start: float
    y_start: float
    x_end: float
    y_end: float
    text: Optional[str] = None
    
    @property
    def width(self) -> float:
        return self.x_end - self.x_start
    
    @property
    def height(self) -> float:
        return self.y_end - self.y_start
    
    @property
    def midpoint_x(self) -> float:
        return (self.x_start + self.x_end) / 2
    
    @property
    def midpoint_y(self) -> float:
        return (self.y_start + self.y_end) / 2

@dataclass
class Layout:
    """Represents a layout with bounding box and text boxes."""
    bbox_layout: Tuple[float, float, float, float]
    label: str
    bbox_text: Optional[List[Tuple[float, float, float, float]]] = None
    text: Optional[List[str]] = None
    
    @property
    def width(self) -> float:
        return self.bbox_layout[2] - self.bbox_layout[0]
    
    @property
    def height(self) -> float:
        return self.bbox_layout[3] - self.bbox_layout[1]
    
    @property
    def text_boxes(self) -> List[TextBox]:
        """Convert bbox_text and text to TextBox objects."""
        if not self.bbox_text:
            return []
        
        text_boxes = []
        for i, bbox in enumerate(self.bbox_text):
            text_content = self.text[i] if self.text and i < len(self.text) else None
            text_boxes.append(TextBox(*bbox, text_content))
        return text_boxes

class ColumnDetector:
    """Class for detecting two-column layouts in document pages."""
    
    def __init__(self, min_text_boxes: int = 8, min_width: int = 600, min_height: int = 500):
        # Note: min_text_boxes is now primarily handled inside the density function per rules.
        self.min_text_boxes_init = min_text_boxes
        self.min_width = min_width
        self.min_height = min_height
    
    def detect_two_column_layout(self, layout: Dict[str, Any]) -> bool:
        """
        Detect if a layout contains a two-column structure using only the density method.
        """
        if 'bbox_text' not in layout or not layout['bbox_text']:
            return False
        
        layout_obj = Layout(
            bbox_layout=layout['bbox_layout'],
            label=layout.get('label', ''),
            bbox_text=layout.get('bbox_text'),
            text=layout.get('text')
        )
        
        all_text_boxes = layout_obj.text_boxes
        layout_width = layout_obj.width

        if layout_width == 0: return False # Éviter la division par zéro
        
        selected_text_boxes = [
            box for box in all_text_boxes 
            if (box.width / layout_width) >= 0.15
        ]
        
        # Le seuil du nombre de boîtes est maintenant appliqué aux boîtes sélectionnées.
        if len(selected_text_boxes) < self.min_text_boxes_init:
            return False
        
        x_midpoints = [box.midpoint_x for box in selected_text_boxes]
        
        # The only algorithm now being called is the density based one.
        return self._is_two_column_by_density(x_midpoints, layout_obj.width)

    def _is_two_column_by_density(self, x_midpoints: List[float], layout_width: float) -> bool:
        """
        Detect two-column structure by analyzing the density distribution of text box midpoints.
        This version includes checks to avoid false positives on signatures or narrow content.
        """
        # Ne pas exécuter la détection si le nombre de boîtes est inférieur à 8.
        if len(x_midpoints) < 8:
            return False

        # --- RÈGLE 2: Vérification de la largeur du contenu (filtre anti-signature) ---
        # Calculer l'étendue horizontale réelle occupée par le texte.
        text_spread = max(x_midpoints) - min(x_midpoints)
        
        # Le contenu textuel doit occuper au moins 60% de la largeur totale du layout.
        # Cela empêche les blocs de texte étroits (comme les signatures) d'être détectés.
        if (text_spread / layout_width) < 0.6:
            return False

        try:
            x_range = np.linspace(min(x_midpoints), max(x_midpoints), 100)
            try:
                kde = gaussian_kde(x_midpoints, bw_method='silverman')
                density = kde(x_range)
                density = density / np.max(density)
                
                middle_region_start = int(len(density) * 0.3)
                middle_region_end = int(len(density) * 0.7)
                middle_density = density[middle_region_start:middle_region_end]
                
                if len(middle_density) > 0:
                    min_density_in_middle = np.min(middle_density)
                    max_density = 1.0 # Since it's normalized
                    
                    if min_density_in_middle < 0.4:
                        left_peak = np.max(density[:middle_region_start])
                        right_peak = np.max(density[middle_region_end:])
                        
                        if left_peak > 0.6  and right_peak > 0.6 :
                            return True
            except Exception:
                return False
                
            return False
        except Exception:
            return False

class LayoutAnalyzer:
    """Class for analyzing page layouts and detecting enhanced layouts."""
    
    def __init__(self, 
                 large_layout_width: int = 900, 
                 large_layout_height: int = 800,
                 min_layout_width: int = 600,
                 min_layout_height: int = 500):
        self.large_layout_width = large_layout_width
        self.large_layout_height = large_layout_height
        self.min_layout_width = min_layout_width
        self.min_layout_height = min_layout_height
        self.column_detector = ColumnDetector()
    
    def enhanced_layout_peek(self, page: Dict[str, Any]) -> List[int]:
        """
        Enhanced function to detect layouts that might contain two-column structures.
        """
        layout_indices: List[int] = []
        
        for i, layout_data in enumerate(page['page']):
            layout = Layout(
                bbox_layout=layout_data['bbox_layout'],
                label=layout_data.get('label', ''),
                bbox_text=layout_data.get('bbox_text'),
                text=layout_data.get('text')
            )
            
            large_layout_condition = (
                
                layout.width > self.large_layout_width and 
                layout.height > self.large_layout_height
            )
            
            if large_layout_condition:
                layout_indices.append(i)
            elif (
                  layout.bbox_text and 
                  layout.width > self.min_layout_width and
                  layout.height > self.min_layout_height):
                
                if self.column_detector.detect_two_column_layout(layout_data):
                    layout_indices.append(i)
        
        return layout_indices
    
# Legacy functions for backward compatibility
def detect_two_column_layout(layout: Dict[str, Any]) -> bool:
    """Legacy function for backward compatibility."""
    detector = ColumnDetector()
    return detector.detect_two_column_layout(layout)

def enhanced_layout_peek(page: Dict[str, Any]) -> List[int]:
    """Legacy function for backward compatibility."""
    analyzer = LayoutAnalyzer()
    return analyzer.enhanced_layout_peek(page)