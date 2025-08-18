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


class TableDetector:
    """Class for analyzing tables layouts and detecting enhanced layouts."""

    
    def __init__(self):
        pass
    
    def detect_table_label(self, page: Dict[str, Any]) -> Dict[str, Any]:
        """
        'selected_page' boolean
        'full_page' boolean
        'list' a list of and 'box' 
        returns the layout index, and the coords of table, and inform if all table
        """
        layout_indices: List[List[float]] = []
        global_all_page = False
        
        for i, layout_data in enumerate(page['page']):
            layout = Layout(
                bbox_layout=layout_data['bbox_layout'],
                label=layout_data.get('label', ''),
                bbox_text=layout_data.get('bbox_text'),
                text=layout_data.get('text')
            )
            
            if (layout.label == 'Table'):
                dimensions = layout.bbox_layout
                layout_indices.append(dimensions)
                
                if (layout.bbox_text and layout.height > 1000):
                    global_all_page = True
                    break
                    
                
        
        if (global_all_page):
            return { 'selected_page': (len(layout_indices) > 0) ,'full_page': True,  'list': [] }
        else:
            if (len(layout_indices) > 0):
                return { 'selected_page': True, 'full_page': False,  'list': layout_indices }
            else:
                return False
        
    
    def detect_3_columns_case(self, page: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        returns the layout index, and the coords of table, and inform if all table
        Dict contains the keys 'index' 'box' 'full_page'
        """
        
        min_layouts_in_row = 3
        scan_step = 15
        threshold_percentage = 50.0
        
        layouts_on_page = page.get('page', [])
        if not layouts_on_page:
            return False

        # Déterminer la hauteur totale de la zone
        all_y_coords = [coord for layout in layouts_on_page for coord in (layout['bbox_layout'][1], layout['bbox_layout'][3])]
        min_y, max_y = min(all_y_coords), max(all_y_coords)

        if max_y <= min_y:
            return False

        scanline_results = []
        for y in range(int(min_y), int(max_y), scan_step):
            intersected_count = sum(1 for layout in layouts_on_page if layout['bbox_layout'][1] <= y <= layout['bbox_layout'][3])
            scanline_results.append(intersected_count >= min_layouts_in_row)

        if not scanline_results:
            return False
            
        percentage_of_true = (scanline_results.count(True) / len(scanline_results)) * 100
        if percentage_of_true > threshold_percentage:
            return [{'selected_page': True, 'full_page': True, 'list': []}]
        else:
            return False
    
    


