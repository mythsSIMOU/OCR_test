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
    
    def __init__(self, min_text_boxes: int = 6, min_width: int = 600, min_height: int = 500):
        self.min_text_boxes = min_text_boxes
        self.min_width = min_width
        self.min_height = min_height
    
    def detect_two_column_layout(self, layout: Dict[str, Any]) -> bool:
        """
        Detect if a layout contains a two-column structure.
        
        Args:
            layout: A dictionary containing the layout information with bbox_text
        
        Returns:
            bool: True if the layout has a two-column structure, False otherwise
        """
        # Check if layout contains text boxes
        if 'bbox_text' not in layout or not layout['bbox_text']:
            return False
        
        # Create Layout object
        layout_obj = Layout(
            bbox_layout=layout['bbox_layout'],
            label=layout.get('label', ''),
            bbox_text=layout.get('bbox_text'),
            text=layout.get('text')
        )
        
        text_boxes = layout_obj.text_boxes
        
        # If very few text boxes, not enough data to determine columns
        if len(text_boxes) < self.min_text_boxes:
            return False
        
        # Extract midpoints of each text box along x-axis
        x_midpoints = [box.midpoint_x for box in text_boxes]
        
        # Analyze density distribution along x-axis to find column gaps
        return (self._is_two_column_by_density(x_midpoints, layout_obj.width) or 
                self._is_two_column_by_clustering(text_boxes, layout_obj.width) or
                self._is_two_column_by_vertical_projection(text_boxes, layout_obj.width))

    def _is_two_column_by_density(self, x_midpoints: List[float], layout_width: float) -> bool:
        """
        Detect two-column structure by analyzing the density distribution of text box midpoints.
        
        Args:
            x_midpoints: List of x-axis midpoints of text boxes
            layout_width: Width of the layout
        
        Returns:
            bool: True if the density distribution suggests a two-column structure
        """
        try:
            # Only proceed if we have enough points for meaningful density estimation
            if len(x_midpoints) < 10:
                return False
                
            # Calculate the density estimation
            x_range = np.linspace(min(x_midpoints), max(x_midpoints), 100)
            try:
                # Try to estimate density with gaussian_kde
                kde = gaussian_kde(x_midpoints, bw_method='silverman')
                density = kde(x_range)
                
                # Normalize density
                density = density / np.max(density)
                
                # Find local minima in the middle region (excluding edges)
                middle_region_start = int(len(density) * 0.3)
                middle_region_end = int(len(density) * 0.7)
                middle_density = density[middle_region_start:middle_region_end]
                
                # Check if there's a significant dip in the middle region
                if len(middle_density) > 0:
                    min_density_in_middle = np.min(middle_density)
                    max_density = np.max(density)
                    
                    # If there's a significant dip (less than 40% of max density)
                    if min_density_in_middle < 0.4 * max_density:
                        # Find peaks in the left and right regions
                        left_peak = np.argmax(density[:middle_region_start])
                        right_peak = middle_region_end + np.argmax(density[middle_region_end:])
                        
                        # Check if both peaks are significant
                        if density[left_peak] > 0.6 * max_density and density[right_peak] > 0.6 * max_density:
                            return True
            except Exception:
                # Fallback if gaussian_kde fails
                return False
                
            return False
        except Exception:
            # Handle any exceptions
            return False

    def _is_two_column_by_clustering(self, text_boxes: List[TextBox], layout_width: float) -> bool:
        """
        Detect two-column structure by clustering text boxes into left and right groups.
        
        Args:
            text_boxes: List of TextBox objects
            layout_width: Width of the layout
        
        Returns:
            bool: True if clustering suggests a two-column structure
        """
        # Calculate the layout midpoint
        layout_midpoint = layout_width / 2
        
        # Count boxes predominantly in left or right half
        left_count = 0
        right_count = 0
        
        for box in text_boxes:
            # Allow for some overlap with the center
            if box.midpoint_x < layout_midpoint * 0.9:
                left_count += 1
            elif box.midpoint_x > layout_midpoint * 1.1:
                right_count += 1
        
        # Check if there's a significant number of boxes in both left and right regions
        total_boxes = len(text_boxes)
        if total_boxes < 6:
            return False
        
        left_ratio = left_count / total_boxes
        right_ratio = right_count / total_boxes
        
        # If at least 30% of boxes are in each column
        return left_ratio > 0.3 and right_ratio > 0.3

    def _is_two_column_by_vertical_projection(self, text_boxes: List[TextBox], layout_width: float) -> bool:
        """
        Detect two-column structure by analyzing the vertical projection of text boxes.
        
        Args:
            text_boxes: List of TextBox objects
            layout_width: Width of the layout
        
        Returns:
            bool: True if vertical projection suggests a two-column structure
        """
        # Number of bins for the projection
        num_bins = 20
        bin_width = layout_width / num_bins
        
        # Initialize projection array
        projection = [0] * num_bins
        
        # Fill the projection array
        for box in text_boxes:
            start_bin = max(0, min(num_bins - 1, int(box.x_start / bin_width)))
            end_bin = max(0, min(num_bins - 1, int(box.x_end / bin_width)))
            
            for bin_idx in range(start_bin, end_bin + 1):
                projection[bin_idx] += 1
        
        # Normalize projection
        max_val = max(projection) if max(projection) > 0 else 1
        normalized_projection = [val / max_val for val in projection]
        
        # Check for gap in the middle region
        middle_start = int(num_bins * 0.4)
        middle_end = int(num_bins * 0.6)
        
        # Find minimum value in the middle region
        middle_min = min(normalized_projection[middle_start:middle_end]) if middle_end > middle_start else 1
        
        # Check if there are significant columns on both sides of the gap
        left_max = max(normalized_projection[:middle_start]) if middle_start > 0 else 0
        right_max = max(normalized_projection[middle_end:]) if middle_end < num_bins else 0
        
        # If there's a significant dip in the middle and columns on both sides
        return middle_min < 0.3 and left_max > 0.5 and right_max > 0.5

    def check_vertical_alignment(self, text_boxes: List[TextBox], tolerance: float = 50.0) -> bool:
        """
        Check if text boxes have a vertical alignment pattern typical of columns.
        
        Args:
            text_boxes: List of TextBox objects
            tolerance: Pixels tolerance for alignment
        
        Returns:
            bool: True if text boxes exhibit vertical alignment
        """
        # Group boxes by similar x_start values (potential column alignment)
        x_start_groups: Dict[float, List[TextBox]] = defaultdict(list)
        
        for box in text_boxes:
            # Find appropriate group or create new one
            grouped = False
            for group_key in x_start_groups:
                if abs(box.x_start - group_key) < tolerance:
                    x_start_groups[group_key].append(box)
                    grouped = True
                    break
            
            if not grouped:
                x_start_groups[box.x_start].append(box)
        
        # Check if we have at least two significant column groups
        significant_groups = [group for group in x_start_groups.values() if len(group) >= 3]
        
        return len(significant_groups) >= 2

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
        
        Args:
            page: A page dictionary containing layout information
        
        Returns:
            List of indices of layouts that are either large or contain two-column structures
        """
        layout_indices: List[int] = []
        
        for i, layout_data in enumerate(page['page']):
            layout = Layout(
                bbox_layout=layout_data['bbox_layout'],
                label=layout_data.get('label', ''),
                bbox_text=layout_data.get('bbox_text'),
                text=layout_data.get('text')
            )
            
            # Original condition for large layouts
            large_layout_condition = (
                layout.label == 'Text' and
                layout.width > self.large_layout_width and 
                layout.height > self.large_layout_height
            )
            
            # Check if this is a large layout (original condition)
            if large_layout_condition:
                layout_indices.append(i)
            # Also check for two-column layouts
            elif (layout.label == 'Text' and 
                  layout.bbox_text and 
                  layout.width > self.min_layout_width and
                  layout.height > self.min_layout_height):
                
                # Check if the layout contains a two-column structure
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