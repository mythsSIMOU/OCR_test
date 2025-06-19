import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from pathlib import Path

class ImageViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Visualization Viewer")
        self.root.geometry("1200x800")  
        
        self.base_folder = "visualization_output"
        self.current_year = 1965
        self.current_image_index = 0
        self.years = list(range(1965, 2026))
        self.current_images = []
        
        # Variables pour le zoom
        self.zoom_level = 1.0
        self.original_image = None
        self.image_on_canvas = None
        
        self.setup_ui()
        self.load_images_for_year()
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        year_frame = ttk.Frame(main_frame)
        year_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(year_frame, text="Year:").pack(side=tk.LEFT)
        self.year_var = tk.StringVar(value=str(self.current_year))
        year_combo = ttk.Combobox(year_frame, textvariable=self.year_var, 
                                 values=[str(y) for y in self.years], state="readonly")
        year_combo.pack(side=tk.LEFT, padx=(5, 0))
        year_combo.bind('<<ComboboxSelected>>', self.on_year_change)
        
        canvas_frame = ttk.Frame(main_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(canvas_frame, bg='white')
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Bind mouse events pour le zoom et le déplacement
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.canvas.bind("<Button-4>", self.on_mousewheel)  # Linux
        self.canvas.bind("<Button-5>", self.on_mousewheel)  # Linux
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<Double-Button-1>", self.reset_zoom)
        
        # Variables pour le drag
        self.start_x = 0
        self.start_y = 0
        
        # Navigation frame
        nav_frame = ttk.Frame(main_frame)
        nav_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.prev_button = ttk.Button(nav_frame, text="Previous", command=self.previous_image)
        self.prev_button.pack(side=tk.LEFT)
        
        size_frame = ttk.Frame(nav_frame)
        size_frame.pack(side=tk.LEFT, padx=(20, 0))
        
        ttk.Label(size_frame, text="Taille:").pack(side=tk.LEFT)
        self.size_var = tk.StringVar(value="Ajustée")
        size_combo = ttk.Combobox(size_frame, textvariable=self.size_var, 
                                 values=["Originale", "Ajustée", "Grande"], state="readonly", width=10)
        size_combo.pack(side=tk.LEFT, padx=(5, 0))
        size_combo.bind('<<ComboboxSelected>>', self.on_size_change)
        
        zoom_frame = ttk.Frame(nav_frame)
        zoom_frame.pack(side=tk.LEFT, padx=(20, 0))
        
        self.zoom_label = ttk.Label(zoom_frame, text="Zoom: 100%")
        self.zoom_label.pack(side=tk.LEFT)
        
        ttk.Button(zoom_frame, text="Reset", command=self.reset_zoom, width=6).pack(side=tk.LEFT, padx=(5, 0))
        
        
        self.image_info_label = ttk.Label(nav_frame, text="")
        self.image_info_label.pack(side=tk.LEFT, expand=True)
        
        self.next_button = ttk.Button(nav_frame, text="Next", command=self.next_image)
        self.next_button.pack(side=tk.RIGHT)
        
    def load_images_for_year(self):
        year_folder = Path(self.base_folder) / str(self.current_year)
        self.current_images = []
        
        if year_folder.exists():
            image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff'}
            for file_path in year_folder.iterdir():
                if file_path.suffix.lower() in image_extensions:
                    self.current_images.append(file_path)
        
        self.current_images.sort()
        self.current_image_index = 0
        self.zoom_level = 1.0  # Reset zoom when changing year
        self.display_current_image()
        self.update_navigation_buttons()
        
    def display_current_image(self):
        if not self.current_images:
            self.canvas.delete("all")
            self.canvas.create_text(400, 300, text="No images found for this year", 
                                  font=("Arial", 16), fill="gray")
            self.image_info_label.config(text="")
            self.zoom_label.config(text="Zoom: 100%")
            return
            
        try:
            image_path = self.current_images[self.current_image_index]
            self.original_image = Image.open(image_path)
            
            # Appliquer le zoom à l'image originale
            self.apply_zoom()
            
            # Update info label
            info_text = f"Image {self.current_image_index + 1} of {len(self.current_images)} - {image_path.name}"
            self.image_info_label.config(text=info_text)
            
        except Exception as e:
            self.canvas.delete("all")
            self.canvas.create_text(400, 300, text=f"Error loading image: {str(e)}", 
                                  font=("Arial", 12), fill="red")
            self.image_info_label.config(text="")
            self.zoom_label.config(text="Zoom: 100%")
    
    def apply_zoom(self):
        if self.original_image is None:
            return
            
        # Calculer la nouvelle taille avec le zoom
        original_width, original_height = self.original_image.size
        new_width = int(original_width * self.zoom_level)
        new_height = int(original_height * self.zoom_level)
        
        # Redimensionner l'image
        if self.zoom_level != 1.0:
            resized_image = self.original_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        else:
            resized_image = self.original_image
        
        # Choix de la taille selon la sélection (seulement si zoom = 1.0)
        if self.zoom_level == 1.0:
            size_option = self.size_var.get()
            if size_option == "Grande":
                resized_image.thumbnail((1000, 700), Image.Resampling.LANCZOS)
            elif size_option == "Ajustée":
                canvas_width = self.canvas.winfo_width() - 20
                canvas_height = self.canvas.winfo_height() - 20
                if canvas_width > 1 and canvas_height > 1:
                    resized_image.thumbnail((canvas_width, canvas_height), Image.Resampling.LANCZOS)
                else:
                    resized_image.thumbnail((800, 600), Image.Resampling.LANCZOS)
        
        self.photo = ImageTk.PhotoImage(resized_image)
        
        # Effacer le canvas et afficher la nouvelle image
        self.canvas.delete("all")
        self.image_on_canvas = self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
        
        # Mettre à jour la zone de défilement
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
        # Mettre à jour l'affichage du zoom
        zoom_percent = int(self.zoom_level * 100)
        self.zoom_label.config(text=f"Zoom: {zoom_percent}%")
    
    def update_navigation_buttons(self):
        self.prev_button.config(state=tk.NORMAL if self.current_image_index > 0 else tk.DISABLED)
        self.next_button.config(state=tk.NORMAL if self.current_image_index < len(self.current_images) - 1 else tk.DISABLED)
    
    def previous_image(self):
        if self.current_image_index > 0:
            self.current_image_index -= 1
            self.zoom_level = 1.0  # Reset zoom when changing image
            self.display_current_image()
            self.update_navigation_buttons()
    
    def next_image(self):
        if self.current_image_index < len(self.current_images) - 1:
            self.current_image_index += 1
            self.zoom_level = 1.0 
            self.display_current_image()
            self.update_navigation_buttons()
    
    def on_year_change(self, event):
        self.current_year = int(self.year_var.get())
        self.load_images_for_year()
    
    def on_size_change(self, event):
        self.zoom_level = 1.0  # Reset zoom when changing size option
        self.display_current_image()
    
   
    def on_mousewheel(self, event):
        # Déterminer la direction du scroll
        if event.num == 4 or event.delta > 0:  
            zoom_factor = 1.1
        elif event.num == 5 or event.delta < 0:  
            zoom_factor = 0.9
        else:
            return
        
        new_zoom = self.zoom_level * zoom_factor
        if 0.1 <= new_zoom <= 10.0:
            self.zoom_level = new_zoom
            self.apply_zoom()
    
    def on_button_press(self, event):
        
        self.start_x = event.x
        self.start_y = event.y
    
    def on_mouse_drag(self, event):
        dx = event.x - self.start_x
        dy = event.y - self.start_y
        
        self.canvas.scan_dragto(event.x, event.y, gain=1)

        self.start_x = event.x
        self.start_y = event.y
    
    def reset_zoom(self, event=None):
        self.zoom_level = 1.0
        self.apply_zoom()
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageViewer(root)
    root.mainloop()