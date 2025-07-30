# nested_detector.py

from typing import Dict, List, Tuple, Any
from itertools import permutations

class NestedLayoutsDetector:
    """Détecte les layouts strictement imbriqués les uns dans les autres."""

    def detect(self, page_data: Dict[str, Any]) -> List[Tuple[int, int]]:
        """
        Trouve les paires de layouts (extérieur, intérieur) sur une page.

        Args:
            page_data: Les données d'une seule page.

        Returns:
            Une liste de tuples, où chaque tuple contient (index_exterieur, index_interieur).
        """
        layouts = page_data.get('page', [])
        if len(layouts) < 2:
            return []

        nested_pairs = []

        # On teste toutes les paires ordonnées de layouts (l'ordre est important)
        for outer_candidate, inner_candidate in permutations(layouts, 2):
            
            # Récupération des bounding boxes
            outer_bbox = outer_candidate['bbox_layout']
            inner_bbox = inner_candidate['bbox_layout']
            
            # Décomposition des coordonnées pour lisibilité
            x1_outer, y1_outer, x2_outer, y2_outer = outer_bbox
            x1_inner, y1_inner, x2_inner, y2_inner = inner_bbox

            # Vérification de la condition d'inclusion stricte
            is_strictly_nested = (
                x1_inner > x1_outer and
                y1_inner > y1_outer and
                x2_inner < x2_outer and
                y2_inner < y2_outer
            )

            if is_strictly_nested:
                # Récupération des index originaux
                outer_index = layouts.index(outer_candidate)
                inner_index = layouts.index(inner_candidate)
                nested_pairs.append((outer_index, inner_index))
                
        return nested_pairs