import os
import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from column_detector import enhanced_layout_peek, detect_two_column_layout

def visualize_page_layouts(page_data, enhanced_layouts, figsize=(20, 25)):
    """
    Visualize all layouts and their text boxes in a single figure,
    highlighting layouts detected by the enhanced algorithm.
    
    Parameters:
    - page_data: A page dictionary containing layout information
    - enhanced_layouts: Indices of layouts detected by the enhanced algorithm
    - figsize: Size of the figure (width, height)
    
    Returns:
    - matplotlib figure object
    """
    # Create figure and axis
    fig, ax = plt.subplots(figsize=figsize)
    
    # Calculate overall document dimensions
    x_coords = []
    y_coords = []
    for layout in page_data['page']:
        x_coords.extend([layout['bbox_layout'][0], layout['bbox_layout'][2]])
        y_coords.extend([layout['bbox_layout'][1], layout['bbox_layout'][3]])
    
    # Add some padding
    x_min, x_max = min(x_coords) - 50, max(x_coords) + 50
    y_min, y_max = min(y_coords) - 50, max(y_coords) + 50
    
    # Set axis limits
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_max, y_min)  # Invert y-axis to match document coordinates
    
    # Set title
    ax.set_title(f"Page {page_data['index']} - Enhanced Layout Detection", fontsize=16)
    
    # Prepare color palette for text boxes
    text_box_colors = plt.cm.Blues(np.linspace(0.3, 0.8, 20))
    
    # Draw each layout and its text boxes
    for layout_idx, layout in enumerate(page_data['page']):
        # Draw layout bounding box
        layout_bbox = layout['bbox_layout']
        x_start, y_start, x_end, y_end = layout_bbox
        layout_width = x_end - x_start
        layout_height = y_end - y_start
        
        # Check if this layout was detected by enhanced algorithm
        is_enhanced_detected = layout_idx in enhanced_layouts
        
        # Determine if this is a large text layout (original condition)
        is_large_text_layout = (
            layout['label'] == 'Text' and 
            layout_width > 900 and 
            layout_height > 800
        )
        
        # Determine if this layout contains a two-column structure
        is_two_column = False
        if layout['label'] == 'Text' and 'bbox_text' in layout:
            is_two_column = detect_two_column_layout(layout)
        
        # Set layout box style based on detection
        layout_line_width = 2.5 if is_enhanced_detected else 1.5
        layout_edge_color = 'green' if is_two_column else ('red' if is_large_text_layout else 'blue')
        
        # Draw layout rectangle with appropriate border
        layout_rect = patches.Rectangle(
            (x_start, y_start), layout_width, layout_height,
            linewidth=layout_line_width, 
            edgecolor=layout_edge_color,  
            facecolor='none', 
            alpha=0.7
        )
        ax.add_patch(layout_rect)
        
        # Add layout index and label
        layout_label = layout.get('label', 'Unknown')
        detection_info = ""
        if is_large_text_layout:
            detection_info = " (Large Text)"
        elif is_two_column:
            detection_info = " (Two-Column)"
            
        ax.text(
            x_start + 5, y_start + 20, 
            f"Layout {layout_idx}: {layout_label}{detection_info}", 
            color='black', 
            fontsize=9, 
            bbox=dict(facecolor='white', alpha=0.8, edgecolor='none', pad=1)
        )
        
        # If layout has bbox_text, draw its text boxes
        if 'bbox_text' in layout and 'text' in layout:
            # Draw each text box
            for text_idx, (bbox, text) in enumerate(zip(layout['bbox_text'], layout['text'])):
                x_start_text, y_start_text, x_end_text, y_end_text = bbox
                text_width = x_end_text - x_start_text
                text_height = y_end_text - y_start_text
                
                # Cycle through text box colors
                text_color = text_box_colors[text_idx % len(text_box_colors)]
                
                # Text box rectangle
                text_rect = patches.Rectangle(
                    (x_start_text, y_start_text), text_width, text_height,
                    linewidth=1, 
                    edgecolor=text_color, 
                    facecolor='none', 
                    alpha=0.7
                )
                ax.add_patch(text_rect)
                
                # Add text index label
                ax.text(
                    x_start_text + 2, y_start_text + 10, 
                    f"L{layout_idx}-T{text_idx}", 
                    color='black', 
                    fontsize=7, 
                    bbox=dict(facecolor='white', alpha=0.6, edgecolor='none', pad=1)
                )
                
                # Optionally add text preview
                text_preview = text[:15] + "..." if len(text) > 15 else text
                ax.text(
                    x_start_text + 2, y_start_text + 20, 
                    text_preview, 
                    color='black', 
                    fontsize=6, 
                    bbox=dict(facecolor='white', alpha=0.5, edgecolor='none', pad=1)
                )
    
    # Add grid for reference
    ax.grid(True, linestyle='--', alpha=0.3)
    
    # Add legend for layout types
    legend_elements = [
        patches.Patch(edgecolor='red', facecolor='none', label='Large Text Layout'),
        patches.Patch(edgecolor='green', facecolor='none', label='Two-Column Layout'),
        patches.Patch(edgecolor='blue', facecolor='none', label='Regular Layout')
    ]
    ax.legend(handles=legend_elements, loc='upper right')
    
    # Add axis labels
    ax.set_xlabel('X coordinate', fontsize=12)
    ax.set_ylabel('Y coordinate', fontsize=12)
    
    plt.tight_layout()
    return fig

def main():
    # Path to the directory containing yearly result_json folders
    base_dir = "result_json"
    
    # Check if the directory exists
    if not os.path.exists(base_dir):
        print(f"Directory {base_dir} not found. Please check the path and try again.")
        return
    
    # Create output directory for saving figures
    output_dir = "visualization_output"
    os.makedirs(output_dir, exist_ok=True)
    
    # Ask user for visualization preference
    print("\nVisualization Options:")
    print("1. Interactive mode (show one window at a time, press close to continue)")
    print("2. Batch mode (save all visualizations as PNG files)")
    print("3. Combined mode (show visualizations and save as PNG files)")
    
    try:
        mode = int(input("Select visualization mode (1-3): ").strip())
    except ValueError:
        mode = 1  # Default to interactive mode
    
    # Counters for statistics
    total_files = 0
    total_pages = 0
    total_layouts = 0
    
    # Iterate through each year folder
    for year in sorted(os.listdir(base_dir), reverse=True):
        year_path = os.path.join(base_dir, year)
        
        if os.path.isdir(year_path) and (year > "1964"):  # Ensure it's a directory
            print(f"Processing year: {year}")
            
            # Create year directory for saving figures
            year_output_dir = os.path.join(output_dir, year)
            os.makedirs(year_output_dir, exist_ok=True)
    
            # Iterate through each JSON file in the year folder
            for filename in sorted(os.listdir(year_path)):
                if filename.endswith(".json"):
                    file_path = os.path.join(year_path, filename)
                    print(f"Processing file: {filename}")
                    total_files += 1
    
                    # Read the JSON file
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
    
                    # Process each page
                    pages_with_layouts = []
                    
                    for page_num, page in enumerate(data):
                        total_pages += 1
                        # Use enhanced layout detection algorithm
                        layout_peek = enhanced_layout_peek(page)
                        
                        if layout_peek:
                            total_layouts += len(layout_peek)
                            pages_with_layouts.append((page, layout_peek))
                            print(f"File: {filename}, Page: {page['index']}, Detected Layouts: {layout_peek}")
                    
                    # Now handle visualization based on selected mode
                    for page, layout_peek in pages_with_layouts:
                        # Generate filename for saving
                        base_filename = os.path.splitext(filename)[0]
                        save_path = os.path.join(year_output_dir, f"{base_filename}_page{page['index']}.png")
                        
                        # Visualize all layouts and their text boxes in one figure
                        fig = visualize_page_layouts(page, layout_peek)
                        
                        if mode == 1 or mode == 3:  # Interactive or Combined mode
                            plt.show(block=False)  # Non-blocking to prevent freezing in batch processing
                            plt.pause(0.1)  # Short pause to render the figure
                            
                            if mode == 1:  # Interactive mode only
                                # Wait for user to press a key before continuing
                                input("Press Enter to continue to next visualization...")
                                plt.close(fig)
                        
                        if mode == 2 or mode == 3:  # Batch or Combined mode
                            # Save figure to file
                            fig.savefig(save_path, dpi=150, bbox_inches='tight')
                            print(f"Saved visualization to {save_path}")
                        
                        if mode != 1:  # Close figure if not in interactive mode
                            plt.close(fig)
    
    # Print summary statistics
    print(f"\nProcessing complete!")
    print(f"Total files processed: {total_files}")
    print(f"Total pages analyzed: {total_pages}")
    print(f"Total layouts detected: {total_layouts}")
    
    if mode == 2 or mode == 3:
        print(f"Visualizations saved to directory: {os.path.abspath(output_dir)}")

if __name__ == "__main__":
    main()