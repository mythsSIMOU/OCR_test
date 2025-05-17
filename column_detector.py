import numpy as np
from scipy.stats import gaussian_kde
from collections import defaultdict

def detect_two_column_layout(layout):
    """
    Detect if a layout contains a two-column structure.
    
    Parameters:
    - layout: A dictionary containing the layout information with bbox_text
    
    Returns:
    - bool: True if the layout has a two-column structure, False otherwise
    """
    # Check if layout contains text boxes
    if 'bbox_text' not in layout or not layout['bbox_text']:
        return False
    
    # Extract text box coordinates
    text_boxes = layout['bbox_text']
    
    # Get layout dimensions
    layout_x_start, layout_y_start, layout_x_end, layout_y_end = layout['bbox_layout']
    layout_width = layout_x_end - layout_x_start
    
    # Extract midpoints of each text box along x-axis
    x_midpoints = [(box[0] + box[2]) / 2 for box in text_boxes]
    
    # If very few text boxes, not enough data to determine columns
    if len(x_midpoints) < 6:  # Require minimum number of text boxes
        return False
    
    # Analyze density distribution along x-axis to find column gaps
    return (is_two_column_by_density(x_midpoints, layout_width) or 
            is_two_column_by_clustering(text_boxes, layout_width) or
            is_two_column_by_vertical_projection(text_boxes, layout_width))

def is_two_column_by_density(x_midpoints, layout_width):
    """
    Detect two-column structure by analyzing the density distribution of text box midpoints.
    
    Parameters:
    - x_midpoints: List of x-axis midpoints of text boxes
    - layout_width: Width of the layout
    
    Returns:
    - bool: True if the density distribution suggests a two-column structure
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
        except:
            # Fallback if gaussian_kde fails
            return False
            
        return False
    except:
        # Handle any exceptions
        return False

def is_two_column_by_clustering(text_boxes, layout_width):
    """
    Detect two-column structure by clustering text boxes into left and right groups.
    
    Parameters:
    - text_boxes: List of text box coordinates [x_start, y_start, x_end, y_end]
    - layout_width: Width of the layout
    
    Returns:
    - bool: True if clustering suggests a two-column structure
    """
    # Extract left and right edges of each text box
    left_edges = [box[0] for box in text_boxes]
    right_edges = [box[2] for box in text_boxes]
    
    # Calculate the layout midpoint
    layout_midpoint = layout_width / 2
    
    # Count boxes predominantly in left or right half
    left_count = 0
    right_count = 0
    
    for left, right in zip(left_edges, right_edges):
        box_midpoint = (left + right) / 2
        
        # Allow for some overlap with the center
        if box_midpoint < layout_midpoint * 0.9:
            left_count += 1
        elif box_midpoint > layout_midpoint * 1.1:
            right_count += 1
    
    # Check if there's a significant number of boxes in both left and right regions
    total_boxes = len(text_boxes)
    if total_boxes < 6:
        return False
    
    left_ratio = left_count / total_boxes
    right_ratio = right_count / total_boxes
    
    # If at least 30% of boxes are in each column
    return left_ratio > 0.3 and right_ratio > 0.3

def is_two_column_by_vertical_projection(text_boxes, layout_width):
    """
    Detect two-column structure by analyzing the vertical projection of text boxes.
    
    Parameters:
    - text_boxes: List of text box coordinates [x_start, y_start, x_end, y_end]
    - layout_width: Width of the layout
    
    Returns:
    - bool: True if vertical projection suggests a two-column structure
    """
    # Number of bins for the projection
    num_bins = 20
    bin_width = layout_width / num_bins
    
    # Initialize projection array
    projection = [0] * num_bins
    
    # Fill the projection array
    for box in text_boxes:
        x_start, _, x_end, _ = box
        start_bin = max(0, min(num_bins - 1, int(x_start / bin_width)))
        end_bin = max(0, min(num_bins - 1, int(x_end / bin_width)))
        
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

def check_vertical_alignment(text_boxes):
    """
    Check if text boxes have a vertical alignment pattern typical of columns.
    
    Parameters:
    - text_boxes: List of text box coordinates [x_start, y_start, x_end, y_end]
    
    Returns:
    - bool: True if text boxes exhibit vertical alignment
    """
    # Group boxes by similar x_start values (potential column alignment)
    tolerance = 50  # Pixels tolerance for alignment
    x_start_groups = defaultdict(list)
    
    for box in text_boxes:
        x_start = box[0]
        # Find appropriate group or create new one
        grouped = False
        for group_key in x_start_groups:
            if abs(x_start - group_key) < tolerance:
                x_start_groups[group_key].append(box)
                grouped = True
                break
        
        if not grouped:
            x_start_groups[x_start].append(box)
    
    # Check if we have at least two significant column groups
    significant_groups = [group for group in x_start_groups.values() if len(group) >= 3]
    
    return len(significant_groups) >= 2

# Enhanced layout detection function for the original code
def enhanced_layout_peek(page):
    """
    Enhanced function to detect layouts that might contain two-column structures.
    
    Parameters:
    - page: A page dictionary containing layout information
    
    Returns:
    - list: Indices of layouts that are either large or contain two-column structures
    """
    layout_indices = []
    
    for i, layout in enumerate(page['page']):
        # Original condition for large layouts
        large_layout_condition = (
            (layout['label'] == 'Text') and
            ((layout['bbox_layout'][2] - layout['bbox_layout'][0]) > 900) and 
            ((layout['bbox_layout'][3] - layout['bbox_layout'][1]) > 800)
        )
        
        # Check if this is a large layout (original condition)
        if large_layout_condition:
            layout_indices.append(i)
        # Also check for two-column layouts
        elif (layout['label'] == 'Text' and 
              'bbox_text' in layout and 
              (layout['bbox_layout'][2] - layout['bbox_layout'][0]) > 600 and  # Minimum width
              (layout['bbox_layout'][3] - layout['bbox_layout'][1]) > 500):    # Minimum height
            
            # Check if the layout contains a two-column structure
            if detect_two_column_layout(layout):
                layout_indices.append(i)
    
    return layout_indices