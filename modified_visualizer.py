import os
import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from pathlib import Path
from column_detector import LayoutAnalyzer, ColumnDetector, Layout, TextBox

@dataclass
class VisualizationConfig:
    """Configuration for visualization settings."""
    figsize: Tuple[int, int] = (20, 25)
    layout_line_width_detected: float = 2.5
    layout_line_width_regular: float = 1.5
    text_box_line_width: float = 1.0
    padding: int = 50
    grid_alpha: float = 0.3
    
@dataclass
class ColorScheme:
    """Color scheme for different layout types."""
    two_column_layout: str = 'green'
    large_text_layout: str = 'red'
    regular_layout: str = 'blue'
    text_box_alpha: float = 0.7

@dataclass
class ProcessingStats:
    """Statistics for processing results."""
    total_files: int = 0
    total_pages: int = 0
    total_layouts: int = 0

class PageVisualizer:
    """Class for visualizing page layouts and their text boxes."""
    
    def __init__(self, config: Optional[VisualizationConfig] = None, 
                 color_scheme: Optional[ColorScheme] = None):
        self.config = config or VisualizationConfig()
        self.colors = color_scheme or ColorScheme()
        self.column_detector = ColumnDetector()
        
    def visualize_page_layouts(self, page_data: Dict[str, Any], 
                             enhanced_layouts: List[int]) -> plt.Figure:
        """
        Visualize all layouts and their text boxes in a single figure,
        highlighting layouts detected by the enhanced algorithm.
        
        Args:
            page_data: A page dictionary containing layout information
            enhanced_layouts: Indices of layouts detected by the enhanced algorithm
        
        Returns:
            matplotlib figure object
        """
        # Create figure and axis
        fig, ax = plt.subplots(figsize=self.config.figsize)
        
        # Calculate overall document dimensions
        x_coords, y_coords = self._get_document_dimensions(page_data)
        
        # Add some padding
        x_min, x_max = min(x_coords) - self.config.padding, max(x_coords) + self.config.padding
        y_min, y_max = min(y_coords) - self.config.padding, max(y_coords) + self.config.padding
        
        # Set axis limits
        ax.set_xlim(x_min, x_max)
        ax.set_ylim(y_max, y_min)  # Invert y-axis to match document coordinates
        
        # Set title
        ax.set_title(f"Page {page_data['index']} - Enhanced Layout Detection", fontsize=16)
        
        # Prepare color palette for text boxes
        text_box_colors = plt.cm.Blues(np.linspace(0.3, 0.8, 20))
        
        # Draw each layout and its text boxes
        self._draw_layouts(ax, page_data, enhanced_layouts, text_box_colors)
        
        # Add grid for reference
        ax.grid(True, linestyle='--', alpha=self.config.grid_alpha)
        
        # Add legend for layout types
        self._add_legend(ax)
        
        # Add axis labels
        ax.set_xlabel('X coordinate', fontsize=12)
        ax.set_ylabel('Y coordinate', fontsize=12)
        
        plt.tight_layout()
        return fig
    
    def _get_document_dimensions(self, page_data: Dict[str, Any]) -> Tuple[List[float], List[float]]:
        """Calculate overall document dimensions."""
        x_coords = []
        y_coords = []
        for layout in page_data['page']:
            x_coords.extend([layout['bbox_layout'][0], layout['bbox_layout'][2]])
            y_coords.extend([layout['bbox_layout'][1], layout['bbox_layout'][3]])
        return x_coords, y_coords
    
    def _draw_layouts(self, ax: plt.Axes, page_data: Dict[str, Any], 
                     enhanced_layouts: List[int], text_box_colors: np.ndarray) -> None:
        """Draw each layout and its text boxes."""
        for layout_idx, layout_data in enumerate(page_data['page']):
            layout = Layout(
                bbox_layout=layout_data['bbox_layout'],
                label=layout_data.get('label', ''),
                bbox_text=layout_data.get('bbox_text'),
                text=layout_data.get('text')
            )
            
            # Check if this layout was detected by enhanced algorithm
            is_enhanced_detected = layout_idx in enhanced_layouts
            
            # Determine layout characteristics
            layout_info = self._analyze_layout(layout, layout_data)
            
            # Draw layout rectangle
            self._draw_layout_rectangle(ax, layout, layout_info, is_enhanced_detected, layout_idx)
            
            # Draw text boxes if they exist
            if layout.bbox_text and layout.text:
                self._draw_text_boxes(ax, layout, text_box_colors, layout_idx)
    
    def _analyze_layout(self, layout: Layout, layout_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze layout characteristics."""
        is_large_text_layout = (
            layout.label == 'Text' and 
            layout.width > 900 and 
            layout.height > 800
        )
        
        is_two_column = False
        if layout.label == 'Text' and layout.bbox_text:
            is_two_column = self.column_detector.detect_two_column_layout(layout_data)
        
        return {
            'is_large_text_layout': is_large_text_layout,
            'is_two_column': is_two_column
        }
    
    def _draw_layout_rectangle(self, ax: plt.Axes, layout: Layout, 
                              layout_info: Dict[str, Any], is_enhanced_detected: bool, 
                              layout_idx: int) -> None:
        """Draw layout rectangle with appropriate styling."""
        x_start, y_start, x_end, y_end = layout.bbox_layout
        
        # Set layout box style based on detection
        layout_line_width = (self.config.layout_line_width_detected if is_enhanced_detected 
                           else self.config.layout_line_width_regular)
        
        if layout_info['is_two_column']:
            layout_edge_color = self.colors.two_column_layout
        elif layout_info['is_large_text_layout']:
            layout_edge_color = self.colors.large_text_layout
        else:
            layout_edge_color = self.colors.regular_layout
        
        # Draw layout rectangle
        layout_rect = patches.Rectangle(
            (x_start, y_start), layout.width, layout.height,
            linewidth=layout_line_width, 
            edgecolor=layout_edge_color,  
            facecolor='none', 
            alpha=self.colors.text_box_alpha
        )
        ax.add_patch(layout_rect)
        
        # Add layout label
        self._add_layout_label(ax, layout, layout_info, layout_idx, x_start, y_start)
    
    def _add_layout_label(self, ax: plt.Axes, layout: Layout, 
                         layout_info: Dict[str, Any], layout_idx: int, 
                         x_start: float, y_start: float) -> None:
        """Add layout index and label."""
        detection_info = ""
        if layout_info['is_large_text_layout']:
            detection_info = " (Large Text)"
        elif layout_info['is_two_column']:
            detection_info = " (Two-Column)"
            
        ax.text(
            x_start + 5, y_start + 20, 
            f"Layout {layout_idx}: {layout.label}{detection_info}", 
            color='black', 
            fontsize=9, 
            bbox=dict(facecolor='white', alpha=0.8, edgecolor='none', pad=1)
        )
    
    def _draw_text_boxes(self, ax: plt.Axes, layout: Layout, 
                        text_box_colors: np.ndarray, layout_idx: int) -> None:
        """Draw text boxes within a layout."""
        for text_idx, (bbox, text) in enumerate(zip(layout.bbox_text, layout.text)):
            text_box = TextBox(*bbox, text)
            
            # Cycle through text box colors
            text_color = text_box_colors[text_idx % len(text_box_colors)]
            
            # Text box rectangle
            text_rect = patches.Rectangle(
                (text_box.x_start, text_box.y_start), text_box.width, text_box.height,
                linewidth=self.config.text_box_line_width, 
                edgecolor=text_color, 
                facecolor='none', 
                alpha=self.colors.text_box_alpha
            )
            ax.add_patch(text_rect)
            
            # Add text index label
            ax.text(
                text_box.x_start + 2, text_box.y_start + 10, 
                f"L{layout_idx}-T{text_idx}", 
                color='black', 
                fontsize=7, 
                bbox=dict(facecolor='white', alpha=0.6, edgecolor='none', pad=1)
            )
            
            # Add text preview
            text_preview = text[:15] + "..." if len(text) > 15 else text
            ax.text(
                text_box.x_start + 2, text_box.y_start + 20, 
                text_preview, 
                color='black', 
                fontsize=6, 
                bbox=dict(facecolor='white', alpha=0.5, edgecolor='none', pad=1)
            )
    
    def _add_legend(self, ax: plt.Axes) -> None:
        """Add legend for layout types."""
        legend_elements = [
            patches.Patch(edgecolor=self.colors.large_text_layout, facecolor='none', 
                         label='Large Text Layout'),
            patches.Patch(edgecolor=self.colors.two_column_layout, facecolor='none', 
                         label='Two-Column Layout'),
            patches.Patch(edgecolor=self.colors.regular_layout, facecolor='none', 
                         label='Regular Layout')
        ]
        ax.legend(handles=legend_elements, loc='upper right')

class DocumentProcessor:
    """Class for processing documents and generating visualizations."""
    
    def __init__(self, base_dir: str = "result_json", output_dir: str = "visualization_output"):
        self.base_dir = Path(base_dir)
        self.output_dir = Path(output_dir)
        self.layout_analyzer = LayoutAnalyzer()
        self.visualizer = PageVisualizer()
        self.stats = ProcessingStats()
    
    def process_documents(self, mode: int = 1) -> None:
        """
        Process all documents and generate visualizations.
        
        Args:
            mode: Visualization mode (1=Interactive, 2=Batch, 3=Combined)
        """
        # Check if the directory exists
        if not self.base_dir.exists():
            print(f"Directory {self.base_dir} not found. Please check the path and try again.")
            return
        
        # Create output directory
        self.output_dir.mkdir(exist_ok=True)
        
        # Process each year folder
        for year_dir in sorted(self.base_dir.iterdir(), reverse=True):
            if year_dir.is_dir() and year_dir.name > "1964":
                self._process_year(year_dir, mode)
        
        # Print summary statistics
        self._print_statistics()
    
    def _process_year(self, year_dir: Path, mode: int) -> None:
        """Process a single year directory."""
        print(f"Processing year: {year_dir.name}")
        
        # Create year directory for saving figures
        year_output_dir = self.output_dir / year_dir.name
        year_output_dir.mkdir(exist_ok=True)
        
        # Process each JSON file in the year folder
        for json_file in sorted(year_dir.glob("*.json")):
            self._process_json_file(json_file, year_output_dir, mode)
    
    def _process_json_file(self, json_file: Path, year_output_dir: Path, mode: int) -> None:
        """Process a single JSON file."""
        print(f"Processing file: {json_file.name}")
        self.stats.total_files += 1
        
        # Read the JSON file
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Process each page
        pages_with_layouts = []
        
        for page_num, page in enumerate(data):
            self.stats.total_pages += 1
            # Use enhanced layout detection algorithm
            layout_peek = self.layout_analyzer.enhanced_layout_peek(page)
            
            if layout_peek:
                self.stats.total_layouts += len(layout_peek)
                pages_with_layouts.append((page, layout_peek))
                print(f"File: {json_file.name}, Page: {page['index']}, Detected Layouts: {layout_peek}")
        
        # Generate visualizations
        self._generate_visualizations(pages_with_layouts, json_file, year_output_dir, mode)
    
    def _generate_visualizations(self, pages_with_layouts: List[Tuple[Dict[str, Any], List[int]]], 
                               json_file: Path, year_output_dir: Path, mode: int) -> None:
        """Generate visualizations for pages with detected layouts."""
        for page, layout_peek in pages_with_layouts:
            # Generate filename for saving
            base_filename = json_file.stem
            save_path = year_output_dir / f"{base_filename}_page{page['index']}.png"
            
            # Visualize all layouts and their text boxes in one figure
            fig = self.visualizer.visualize_page_layouts(page, layout_peek)
            
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
    
    def _print_statistics(self) -> None:
        """Print processing statistics."""
        print(f"\nProcessing complete!")
        print(f"Total files processed: {self.stats.total_files}")
        print(f"Total pages analyzed: {self.stats.total_pages}")
        print(f"Total layouts detected: {self.stats.total_layouts}")
        print(f"Visualizations saved to directory: {self.output_dir.absolute()}")
    
    def get_visualization_mode(self) -> int:
        """Get visualization mode from user input."""
        print("\nVisualization Options:")
        print("1. Interactive mode (show one window at a time, press close to continue)")
        print("2. Batch mode (save all visualizations as PNG files)")
        print("3. Combined mode (show visualizations and save as PNG files)")
        
        try:
            mode = int(input("Select visualization mode (1-3): ").strip())
            return mode if mode in [1, 2, 3] else 1
        except ValueError:
            return 1  # Default to interactive mode

def main() -> None:
    """Main function to run the document processing and visualization."""
    processor = DocumentProcessor()
    mode = processor.get_visualization_mode()
    processor.process_documents(mode)

if __name__ == "__main__":
    main()