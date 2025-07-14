from typing import Dict, List, Any
from itertools import combinations
from dataclasses import dataclass

@dataclass
class Layout:
    """Représente un bloc de mise en page pour une analyse simplifiée."""
    index: int
    x_start: float
    y_start: float
    x_end: float
    y_end: float

class RowDetector:
    """Détecte les layouts alignés horizontalement sur une page."""
    
    def __init__(self, min_layouts_in_row: int = 3):
        self.min_layouts_in_row = min_layouts_in_row

    def detect_horizontal_layouts(self, page_data: Dict[str, Any]) -> List[int]:
        """
        Détecte les ensembles de layouts qui sont alignés horizontalement et distincts.
        """
        layouts_on_page = page_data.get('page', [])
        if len(layouts_on_page) < self.min_layouts_in_row:
            return []

        layouts = [
            Layout(
                index=i,
                x_start=layout['bbox_layout'][0],
                y_start=layout['bbox_layout'][1],
                x_end=layout['bbox_layout'][2],
                y_end=layout['bbox_layout'][3]
            )
            for i, layout in enumerate(layouts_on_page)
        ]

        detected_indices = set()

        for layout_group in combinations(layouts, self.min_layouts_in_row):
            # Condition 1: Vérifier le chevauchement vertical (les layouts sont sur la même ligne)
            y_starts = [l.y_start for l in layout_group]
            y_ends = [l.y_end for l in layout_group]
            
            if max(y_starts) >= min(y_ends):
                continue # Pas de chevauchement vertical, on passe au groupe suivant

            # Condition 2: Vérifier le non-chevauchement horizontal (les layouts sont côte à côte)
            horizontally_separate = True
            # On vérifie chaque paire dans le groupe
            for pair in combinations(layout_group, 2):
                l1, l2 = pair
                # Si les layouts se chevauchent horizontalement, la condition est fausse
                if max(l1.x_start, l2.x_start) < min(l1.x_end, l2.x_end):
                    horizontally_separate = False
                    break # Inutile de vérifier les autres paires
            
            if horizontally_separate:
                # Si les deux conditions sont remplies, on ajoute les indices
                for layout in layout_group:
                    detected_indices.add(layout.index)

        return sorted(list(detected_indices))