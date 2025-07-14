# row_detector.py

from typing import Dict, List, Any

class RowDetector:
    """Détecte les pages contenant des alignements horizontaux de plusieurs layouts."""
    
    def __init__(self, min_layouts_in_row: int = 3, scan_step: int = 15, threshold_percentage: float = 50.0):
        """
        Initialise le détecteur avec les nouveaux paramètres.
        """
        self.min_layouts_in_row = min_layouts_in_row
        self.scan_step = scan_step
        self.threshold_percentage = threshold_percentage

    def detect_multi_layout_rows_on_page(self, page_data: Dict[str, Any]) -> bool:
        """
        Détecte si une page contient suffisamment de lignes avec 3+ layouts.
        """
        layouts_on_page = page_data.get('page', [])
        if not layouts_on_page:
            return False

        # Déterminer la hauteur totale de la zone
        all_y_coords = [coord for layout in layouts_on_page for coord in (layout['bbox_layout'][1], layout['bbox_layout'][3])]
        min_y, max_y = min(all_y_coords), max(all_y_coords)

        if max_y <= min_y:
            return False

        scanline_results = []
        for y in range(int(min_y), int(max_y), self.scan_step):
            intersected_count = sum(1 for layout in layouts_on_page if layout['bbox_layout'][1] <= y <= layout['bbox_layout'][3])
            scanline_results.append(intersected_count >= self.min_layouts_in_row)

        if not scanline_results:
            return False
            
        percentage_of_true = (scanline_results.count(True) / len(scanline_results)) * 100
        return percentage_of_true > self.threshold_percentage