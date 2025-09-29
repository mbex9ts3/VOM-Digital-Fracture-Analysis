"""
Main module for the Polyline Mapper application.
Handles initialization, file loading, and mode coordination.
"""

import pyvista as pv
import numpy as np
import os
from pathlib import Path
import json
import tkinter as tk
from tkinter import filedialog, messagebox
import time

# Import mode modules
from select_mode import SelectMode
from digitize_mode import DigitizeMode
from edit_mode import EditMode
from topology_mode import TopologyMode


class InteractiveMeshVisualizer:
    def __init__(self):
        self.plotter = None
        self.mesh = None
        self.texture = None
        self.mode = 'select'  # 'select', 'digitize', 'edit', 'topology'
        self.current_polyline = []
        self.polylines = []
        self.polyline_actors = []
        self.selected_polyline_idx = None
        self.output_directory = None
        
        # Trackball and camera management
        self.last_click_time = 0
        self.last_click_point = None
        self.double_click_threshold = 0.5  # seconds
        self.original_camera_position = None
        self.original_focal_point = None
        
        # Initialize tkinter root (hidden)
        self.root = tk.Tk()
        self.root.withdraw()  # Hide the main tkinter window
        
        # Initialize mode handlers
        self.select_mode = SelectMode(self)
        self.digitize_mode = DigitizeMode(self)
        self.edit_mode = EditMode(self)
        self.topology_mode = TopologyMode(self)
        
    def select_files_dialog(self):
        """Open dialog boxes to select PLY file and texture file"""
        # Select PLY file
        ply_path = filedialog.askopenfilename(
            title="Select PLY Mesh File",
            filetypes=[
                ("PLY files", "*.ply"),
                ("All files", "*.*")
            ]
        )
        
        if not ply_path:
            print("No PLY file selected. Exiting...")
            return None, None
        
        # Ask if user wants to load a texture
        load_texture = messagebox.askyesno(
            "Load Texture", 
            "Would you like to load a texture file for this mesh?"
        )
        
        texture_path = None
        if load_texture:
            texture_path = filedialog.askopenfilename(
                title="Select Texture File (PNG, JPG, etc.)",
                filetypes=[
                    ("Image files", "*.png *.jpg *.jpeg *.bmp *.tiff *.tif"),
                    ("PNG files", "*.png"),
                    ("JPEG files", "*.jpg *.jpeg"),
                    ("All files", "*.*")
                ]
            )
        
        return ply_path, texture_path
    
    def select_output_directory(self):
        """Select output directory for saving polylines"""
        output_dir = filedialog.askdirectory(
            title="Select Output Directory for Polylines",
            initialdir=os.getcwd()
        )
        
        if not output_dir:
            output_dir = os.getcwd()
            print(f"No output directory selected. Using current directory: {output_dir}")
        
        return Path(output_dir)
    
    def load_textured_mesh(self, ply_path, texture_path=None):
        """Load a PLY file and optional texture - using PyVista's built-in picking!"""
        try:
            # Load the mesh
            self.mesh = pv.read(ply_path)
            print(f"Loaded mesh with {self.mesh.n_points} points and {self.mesh.n_cells} cells")
            print("Using PyVista's built-in surface picking - fast and efficient!")
            
            # Load texture if provided
            if texture_path and os.path.exists(texture_path):
                self.texture = pv.read_texture(texture_path)
                print(f"Loaded texture: {texture_path}")
            else:
                print("No texture provided or texture file not found")
                
            return True
        except Exception as e:
            print(f"Error loading mesh: {e}")
            return False
    
    def get_screen_resolution(self):
        """Get screen resolution for window maximization"""
        try:
            import tkinter as tk
            root = tk.Tk()
            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()
            root.destroy()
            
            # Leave some margin for taskbar/dock
            usable_width = int(screen_width * 0.95)
            usable_height = int(screen_height * 0.9)
            
            print(f"Detected screen resolution: {screen_width}x{screen_height}")
            print(f"Using window size: {usable_width}x{usable_height}")
            
            return usable_width, usable_height
        except Exception as e:
            print(f"Could not detect screen resolution: {e}")
            return 1920, 1080  # Fallback
    
    def setup_plotter(self):
        """Initialize the PyVista plotter with interactive controls"""
        # Get screen resolution and create appropriately sized window
        window_width, window_height = self.get_screen_resolution()
        
        # Create plotter with detected screen size
        self.plotter = pv.Plotter(window_size=(window_width, window_height))
        
        # Try additional maximization methods
        try:
            if hasattr(self.plotter, 'render_window'):
                render_window = self.plotter.render_window
                render_window.SetSize(window_width, window_height)
                render_window.SetPosition(50, 50)  # Position away from screen edges
                
            print(f"Window configured to {window_width}x{window_height}")
        except Exception as e:
            print(f"Window sizing failed: {e}")
        
        # Add the mesh to the plotter
        if self.texture:
            self.plotter.add_mesh(self.mesh, texture=self.texture, name='main_mesh')
        else:
            self.plotter.add_mesh(self.mesh, name='main_mesh', color='lightgray')
        
        # Set up camera and lighting
        self.plotter.add_light(pv.Light(position=(10, 10, 10), focal_point=(0, 0, 0)))
        
        # Add trackball widget to avoid gimbal lock
        try:
            # Add orientation widget (trackball) in bottom right
            self.plotter.add_orientation_widget(
                actor=None,  # Use default
                interactive=True,
                outline=True,
                color='black',
                viewport=(0.75, 0.0, 1.0, 0.25)  # Bottom right corner
            )
            print("Added orientation trackball widget")
        except Exception as e:
            print(f"Couldn't add orientation widget: {e}")
        
        # Add axes widget for reference
        try:
            self.plotter.show_axes()
            print("Added axes reference")
        except:
            pass
        
        # Use PyVista's surface point picking
        self.plotter.enable_surface_point_picking(
            callback=self.surface_pick_callback,
            show_message=False,  # Don't show default message
            show_point=False,    # We'll handle visualization ourselves
            tolerance=0.01,      # Fine tolerance for accurate picking
            left_clicking=True,  # Enable left-click picking
            picker='cell',       # Use cell picker for surface accuracy
            use_picker=True      # Use the fast picker
        )
        
        # Set up key press callbacks with extra error protection
        try:
            self.plotter.add_key_event('space', self.toggle_mode)
            self.plotter.add_key_event('Return', self.finish_current_polyline)
            self.plotter.add_key_event('Escape', self.cancel_current_action)
            self.plotter.add_key_event('Delete', self.delete_selected_polyline)
            self.plotter.add_key_event('s', self.save_all_polylines)
            self.plotter.add_key_event('c', self.clear_all_polylines)
            self.plotter.add_key_event('d', self.deselect_all)
            self.plotter.add_key_event('h', self.show_help)
            
            # Disable the default 'e' key exit behavior and add edit mode on 'm'
            self.plotter.add_key_event('e', lambda: None)  # Override with no-op
            self.plotter.add_key_event('m', self.toggle_edit_mode)  # 'M' for modify/edit
            
            # Add topology mode toggle on 't' (replaces trackball reset which is now 'r')
            self.plotter.add_key_event('t', self.toggle_topology_mode)
            
            # Add number keys for topology editing
            self.plotter.add_key_event('1', self.set_topology_blind)
            self.plotter.add_key_event('2', self.set_topology_crossing)
            self.plotter.add_key_event('3', self.set_topology_abutting)
            self.plotter.add_key_event('4', self.set_topology_censored)
            
            # Add orthogonal view hotkeys
            self.plotter.add_key_event('x', self.view_x_axis)
            self.plotter.add_key_event('y', self.view_y_axis)
            self.plotter.add_key_event('z', self.view_z_axis)
            self.plotter.add_key_event('i', self.view_isometric)
            self.plotter.add_key_event('r', self.reset_camera)
            
            print("Key callbacks registered successfully")
        except Exception as e:
            print(f"Error registering key callbacks: {e}")
        
        # Enable trackball style interaction (quaternion-based, no gimbal lock)
        try:
            # Use trackball interaction style instead of joystick to reduce gimbal lock
            self.plotter.iren.SetInteractorStyle(self.plotter.iren.GetInteractorStyle())
            # Alternative: try to use trackball camera style
            if hasattr(self.plotter, 'enable_trackball_style'):
                self.plotter.enable_trackball_style()
                print("Enabled trackball camera style")
        except Exception as e:
            print(f"Trackball style not available: {e}")
        
        # Store original camera position for trackball reset
        self.store_original_camera_position()
        
        # Set up right-click handling for trackball reset
        self.setup_right_click_handler()
        
        # Initialize in select mode
        self.select_mode.activate()
        self.show_help()
    
    def view_x_axis(self):
        """View along X axis (YZ plane)"""
        self.plotter.view_yz()
        print("View: X-axis (YZ plane)")
    
    def view_y_axis(self):
        """View along Y axis (XZ plane)"""
        self.plotter.view_xz()
        print("View: Y-axis (XZ plane)")
    
    def view_z_axis(self):
        """View along Z axis (XY plane)"""
        self.plotter.view_xy()
        print("View: Z-axis (XY plane)")
    
    def view_isometric(self):
        """Isometric view - preserve trackball widget"""
        self.plotter.view_isometric()
        # Re-add the trackball widget if it was removed
        try:
            self.plotter.add_orientation_widget(
                actor=None,  # Use default
                interactive=True,
                outline=True,
                color='black',
                viewport=(0.75, 0.0, 1.0, 0.25)  # Bottom right corner
            )
        except Exception as e:
            print(f"Could not restore orientation widget: {e}")
        print("View: Isometric")
    
    def reset_camera(self):
        """Reset camera to fit all and restore original position"""
        try:
            if (self.original_camera_position is not None and 
                self.original_focal_point is not None):
                
                self.plotter.camera.position = self.original_camera_position
                self.plotter.camera.focal_point = self.original_focal_point
                self.plotter.camera.view_up = [0, 0, 1]  # Reset view up vector
                self.plotter.render()
                print("Reset camera to original position")
            else:
                # Fallback to standard reset if original position not stored
                self.plotter.reset_camera()
                print("Camera reset")
        except Exception as e:
            print(f"Error resetting camera: {e}")
            # Fallback to standard reset
            self.plotter.reset_camera()
    
    def store_original_camera_position(self):
        """Store the original camera position and focal point for trackball reset"""
        try:
            if self.plotter and self.plotter.camera:
                self.original_camera_position = np.array(self.plotter.camera.position)
                self.original_focal_point = np.array(self.plotter.camera.focal_point)
                print(f"Stored original camera position: {self.original_camera_position}")
                print(f"Stored original focal point: {self.original_focal_point}")
        except Exception as e:
            print(f"Could not store original camera position: {e}")
    
    def setup_right_click_handler(self):
        """Set up right-click handler for trackball reset using VTK events"""
        try:
            if hasattr(self.plotter, 'iren') and self.plotter.iren:
                # Add observer for right button press events
                self.plotter.iren.AddObserver('RightButtonPressEvent', self.handle_right_click)
                print("Right-click handler registered for trackball reset")
        except Exception as e:
            print(f"Could not set up right-click handler: {e}")
    
    def handle_right_click(self, obj, event):
        """Handle right-click events for trackball reset"""
        try:
            if self.mode == 'select':
                print("Right-click detected in SELECT mode - resetting trackball")
                self.reset_camera()
        except Exception as e:
            print(f"Error handling right-click: {e}")
    
    def surface_pick_callback(self, *args, **kwargs):
        """Callback for PyVista's surface point picking - routes to appropriate mode handler"""
        print(f"Surface pick callback called with args: {args}, kwargs: {kwargs}")
        
        # Extract the point from different possible callback signatures
        point = None
        
        if len(args) >= 1:
            point = args[0]
        elif 'point' in kwargs:
            point = kwargs['point']
        elif len(args) >= 2:
            # Sometimes the first arg is the picker object, second is the point
            point = args[1] if args[1] is not None else args[0]
        
        if point is None:
            print("No surface point picked or couldn't extract point from callback")
            return
        
        print(f"Extracted surface point: {point}")
        
        # Route to appropriate handler based on current mode
        if self.mode == 'select':
            self.select_mode.handle_pick(point)
        elif self.mode == 'digitize':
            self.digitize_mode.handle_pick(point)
        elif self.mode == 'edit':
            self.edit_mode.handle_pick(point)
        elif self.mode == 'topology':
            self.topology_mode.handle_pick(point)
    
    def toggle_mode(self):
        """Toggle between select and digitize modes"""
        try:
            if self.mode == 'select':
                # Switch to digitize mode
                self.digitize_mode.activate()
            elif self.mode == 'digitize':
                # Switch back to select mode
                self.select_mode.activate()
            elif self.mode == 'edit':
                # Exit edit mode back to select
                self.select_mode.activate()
            elif self.mode == 'topology':
                # Exit topology mode back to select
                self.select_mode.activate()
        except Exception as e:
            print(f"Error toggling mode: {e}")
            import traceback
            traceback.print_exc()
    
    def toggle_edit_mode(self):
        """Toggle edit mode on/off"""
        try:
            if self.mode == 'edit':
                # Exit edit mode back to select
                self.select_mode.activate()
            else:
                # Try to enter edit mode
                self.edit_mode.activate()
        except Exception as e:
            print(f"Error toggling edit mode: {e}")
            import traceback
            traceback.print_exc()
    
    def toggle_topology_mode(self):
        """Toggle topology mode on/off"""
        try:
            if self.mode == 'topology':
                # Exit topology mode back to select
                self.select_mode.activate()
            else:
                # Enter topology mode
                self.topology_mode.activate()
        except Exception as e:
            print(f"Error toggling topology mode: {e}")
            import traceback
            traceback.print_exc()
    
    def set_topology_blind(self):
        """Set selected endpoint as Blind"""
        if self.mode == 'topology':
            self.topology_mode.update_selected_endpoint('B')
    
    def set_topology_crossing(self):
        """Set selected endpoint as Crossing"""
        if self.mode == 'topology':
            self.topology_mode.update_selected_endpoint('X')
    
    def set_topology_abutting(self):
        """Set selected endpoint as Abutting"""
        if self.mode == 'topology':
            self.topology_mode.update_selected_endpoint('A')
    
    def set_topology_censored(self):
        """Set selected endpoint as Censored"""
        if self.mode == 'topology':
            self.topology_mode.update_selected_endpoint('C')
    
    def finish_current_polyline(self):
        """Delegate to digitize mode"""
        if self.mode == 'digitize':
            self.digitize_mode.finish_current_polyline()
    
    def cancel_current_action(self):
        """Cancel the current action (polyline drawing only)"""
        if self.mode == 'digitize':
            self.digitize_mode.cancel_current_polyline()
        else:
            print("ESCAPE only cancels polyline drawing in DIGITIZE mode")
    
    def delete_selected_polyline(self):
        """Delete the currently selected polyline"""
        if self.selected_polyline_idx is None:
            print("No polyline selected for deletion")
            return
        
        # Remove from scene
        actor_name = f'polyline_{self.selected_polyline_idx}'
        try:
            self.plotter.remove_actor(actor_name)
        except:
            pass
        
        # Remove from data
        deleted_idx = self.selected_polyline_idx
        del self.polylines[self.selected_polyline_idx]
        
        print(f"Deleted polyline {deleted_idx + 1}")
        
        # Clear selection
        self.selected_polyline_idx = None
        
        # Refresh all polylines with updated indices
        self.refresh_polyline_visualization()
    
    def deselect_all(self):
        """Deselect all polylines"""
        if self.selected_polyline_idx is not None:
            old_selected = self.selected_polyline_idx
            self.selected_polyline_idx = None
            self.add_polyline_to_scene(old_selected)  # Reset color
            print("Deselected all polylines")
    
    def add_polyline_to_scene(self, polyline_idx):
        """Add a polyline to the 3D scene with thicker lines"""
        if polyline_idx >= len(self.polylines):
            return
        
        points = np.array(self.polylines[polyline_idx]['points'])
        
        # Create polyline
        polyline = pv.PolyData()
        polyline.points = points
        
        # Create line connectivity
        n_points = len(points)
        lines = np.zeros((n_points - 1, 3), dtype=int)
        lines[:, 0] = 2  # Each line has 2 points
        lines[:, 1] = np.arange(n_points - 1)  # Start points
        lines[:, 2] = np.arange(1, n_points)   # End points
        
        polyline.lines = lines.ravel()
        
        # Color based on selection state with much thicker lines
        color = 'yellow' if polyline_idx == self.selected_polyline_idx else 'blue'
        line_width = 12 if polyline_idx == self.selected_polyline_idx else 6
        actor_name = f'polyline_{polyline_idx}'
        
        self.plotter.add_mesh(polyline, color=color, line_width=line_width, name=actor_name)
    
    def refresh_polyline_visualization(self):
        """Refresh all polyline visualizations with updated indices"""
        # Remove all polyline actors
        actors_to_remove = []
        for name in list(self.plotter.renderer.actors.keys()):
            if name.startswith('polyline_'):
                actors_to_remove.append(name)
        
        for actor_name in actors_to_remove:
            try:
                self.plotter.remove_actor(actor_name)
            except:
                pass
        
        # Re-add all polylines
        for i in range(len(self.polylines)):
            self.add_polyline_to_scene(i)
    
    def save_all_polylines(self):
        """Save all polylines to separate files"""
        if not self.polylines:
            print("No polylines to save")
            return
        
        # Ask for output directory at save time
        output_dir = self.select_output_directory()
        if not output_dir:
            print("No output directory selected. Save cancelled.")
            return
        
        # Create output directory
        polylines_dir = output_dir / "polylines_output"
        polylines_dir.mkdir(exist_ok=True)
        
        for i, polyline_data in enumerate(self.polylines):
            # Save as .txt file
            txt_filename = polylines_dir / f"polyline_{i+1:03d}.txt"
            np.savetxt(txt_filename, polyline_data['points'], 
                      fmt='%.6f', header=f'Polyline {i+1} - X Y Z coordinates')
            
            # Save as .dat file (binary)
            dat_filename = polylines_dir / f"polyline_{i+1:03d}.dat"
            np.array(polyline_data['points']).tofile(dat_filename)
            
            print(f"Saved polyline {i+1}: {txt_filename} and {dat_filename}")
        
        # Also save a summary JSON file with topology data if available
        summary_data = {
            'num_polylines': len(self.polylines),
            'polylines': self.polylines
        }
        
        # Add topology data if it exists
        if hasattr(self.topology_mode, 'topology_data') and self.topology_mode.topology_data:
            summary_data['topology'] = self.topology_mode.topology_data
            print("Including topology data in summary")
        
        summary_file = polylines_dir / "polylines_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary_data, f, indent=2)
        
        print(f"Saved summary: {summary_file}")
        print(f"Total: {len(self.polylines)} polylines saved to {polylines_dir}")
    
    def clear_all_polylines(self):
        """Clear all polylines"""
        # Remove all polyline actors and current polyline visualization
        actors_to_remove = []
        for name in list(self.plotter.renderer.actors.keys()):
            if (name.startswith('polyline_') or 
                name == 'current_polyline' or 
                name.startswith('current_point_')):
                actors_to_remove.append(name)
        
        for actor_name in actors_to_remove:
            try:
                self.plotter.remove_actor(actor_name)
            except:
                pass
        
        # Clear data
        self.polylines = []
        self.current_polyline = []
        self.selected_polyline_idx = None
        
        print("Cleared all polylines")
    
    def show_help(self):
        """Display help information with cleaner formatting"""
        print("\n" + "="*60)
        print("POLYLINE MAPPER CONTROLS")
        print("="*60)
        print("MODES:")
        print("  SPACEBAR: Toggle between SELECT and DIGITIZE modes")
        print("           (exits EDIT/TOPOLOGY mode back to SELECT)")
        print("  M: Toggle EDIT mode on/off for selected polyline")
        print("  T: Toggle TOPOLOGY mode on/off for fracture analysis")
        print("")
        print("MOUSE ACTIONS:")
        print("  LEFT CLICK: Select polylines (SELECT) / Add points (DIGITIZE)")
        print("             Extend or delete points (EDIT)")
        print("             Select endpoints (TOPOLOGY)")
        print("  DOUBLE LEFT CLICK: Translate camera/trackball to point (SELECT mode)")
        print("  RIGHT CLICK: Reset trackball to original position (SELECT mode)")
        print("  Mouse drag: Pan, zoom, rotate view")
        print("")
        print("POLYLINE OPERATIONS:")
        print("  ENTER: Finish current polyline (DIGITIZE mode)")
        print("  ESCAPE: Cancel current polyline drawing (DIGITIZE mode only)")
        print("  DELETE: Delete selected polyline")
        print("  D: Deselect all polylines")
        print("")
        print("TOPOLOGY MODE (Press T):")
        print("  1: Set endpoint as Blind (B) - Green")
        print("  2: Set endpoint as Crossing (X) - Blue")
        print("  3: Set endpoint as Abutting (A) - Gold")
        print("  4: Set endpoint as Censored (C) - Red")
        print("  Click endpoint to select, click again to deselect")
        print("")
        print("CAMERA CONTROLS:")
        print("  X: View along X-axis (YZ plane)")
        print("  Y: View along Y-axis (XZ plane)")
        print("  Z: View along Z-axis (XY plane)")
        print("  I: Isometric view")
        print("  R: Reset camera to original position")
        print("  DOUBLE-CLICK: Translate trackball center (SELECT mode)")
        print("")
        print("FILE OPERATIONS:")
        print("  S: Save all polylines (includes topology data)")
        print("  C: Clear all polylines")
        print("  H: Show this help")
        print("")
        print("WORKFLOW:")
        print("1. DIGITIZE mode: Click points to create polylines, ENTER to finish")
        print("2. SELECT mode: Click to select existing polylines")
        print("3. EDIT mode: M to enter, extend/delete points, M to exit")
        print("4. TOPOLOGY mode: T to enter, analyze terminations, T to exit")
        print("")
        print(f"Current mode: {self.mode.upper()}")
        if hasattr(self, 'selected_polyline_idx') and self.selected_polyline_idx is not None:
            print(f"Selected: Polyline {self.selected_polyline_idx + 1}")
        else:
            print("Selected: None")
        print("="*60 + "\n")
    
    def run(self, ply_path=None, texture_path=None):
        """Main function to run the interactive visualization"""
        # If no paths provided, open file selection dialogs
        if ply_path is None:
            ply_path, texture_path = self.select_files_dialog()
            if ply_path is None:
                return  # User cancelled
        
        if not self.load_textured_mesh(ply_path, texture_path):
            return
        
        self.setup_plotter()
        
        print(f"Starting interactive visualization...")
        print(f"Mesh bounds: {self.mesh.bounds}")
        
        # Show the interactive window
        self.plotter.show()


# Example usage
if __name__ == "__main__":
    # Create visualizer instance
    visualizer = InteractiveMeshVisualizer()
    
    # Option 1: Run with dialog boxes to select files (recommended)
    visualizer.run()
    
    # Option 2: Run with specific file paths (uncomment to use)
    # ply_file = "your_mesh.ply"
    # texture_file = "your_texture.png"  # Optional
    # visualizer.run(ply_file, texture_file)