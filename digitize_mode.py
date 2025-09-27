import numpy as np
import pyvista as pv


class DigitizeMode:
    def __init__(self, visualizer):
        self.visualizer = visualizer
    
    def handle_surface_pick(self, point):
        """Handle surface picking in digitize mode"""
        self.add_point_to_current_polyline(point)
    
    def add_point_to_current_polyline(self, surface_point):
        """Add a surface point to the current polyline being digitized"""
        try:
            self.visualizer.current_polyline.append(surface_point)
            print(f"Added point {len(self.visualizer.current_polyline)}: {surface_point}")
            
            # Visualize the picked point
            self.add_point_visualization(surface_point, len(self.visualizer.current_polyline) - 1)
            
            # Update the current polyline visualization
            self.update_current_polyline_visualization()
            
        except Exception as e:
            print(f"Error adding point to polyline: {e}")
    
    def add_point_visualization(self, point, point_index):
        """Add a visual marker for a picked point with smaller size"""
        # Calculate appropriate sphere size based on mesh bounds
        mesh_size = np.linalg.norm(np.array(self.visualizer.mesh.bounds[1::2]) - np.array(self.visualizer.mesh.bounds[::2]))
        sphere_radius = mesh_size * 0.0017  # ~0.17% of mesh size
        
        sphere = pv.Sphere(radius=sphere_radius, center=point)
        point_name = f'current_point_{point_index}'
        
        # Add the point marker with bright color
        self.visualizer.plotter.add_mesh(sphere, color='yellow', name=point_name)
    
    def update_current_polyline_visualization(self):
        """Update visualization of the current polyline being drawn"""
        if len(self.visualizer.current_polyline) < 2:
            return
        
        # Remove previous current polyline visualization
        try:
            self.visualizer.plotter.remove_actor('current_polyline')
        except:
            pass
        
        # Create polyline from points
        points = np.array(self.visualizer.current_polyline)
        
        # Create a PolyData object for the line
        polyline = pv.PolyData()
        polyline.points = points
        
        # Create line connectivity
        n_points = len(points)
        lines = np.zeros((n_points - 1, 3), dtype=int)
        lines[:, 0] = 2  # Each line has 2 points
        lines[:, 1] = np.arange(n_points - 1)  # Start points
        lines[:, 2] = np.arange(1, n_points)   # End points
        
        polyline.lines = lines.ravel()
        
        # Add to plotter with thicker line
        self.visualizer.plotter.add_mesh(polyline, color='red', line_width=12, name='current_polyline')
    
    def handle_enter_key(self):
        """Handle Enter key press - finish current polyline"""
        self.finish_current_polyline()
    
    def handle_escape_key(self):
        """Handle Escape key press - cancel current polyline"""
        self.cancel_current_action()
    
    def finish_current_polyline(self):
        """Finish the current polyline and add it to the collection"""
        if len(self.visualizer.current_polyline) < 2:
            print("Need at least 2 points to create a polyline")
            return
        
        # Store the polyline
        polyline_data = {
            'points': np.array(self.visualizer.current_polyline).tolist(),
            'id': len(self.visualizer.polylines)
        }
        self.visualizer.polylines.append(polyline_data)
        
        # Remove current polyline and point visualizations
        self.clear_current_polyline_visualization()
        
        # Add permanent polyline visualization
        self.visualizer.add_polyline_to_scene(len(self.visualizer.polylines) - 1)
        
        print(f"Finished polyline {len(self.visualizer.polylines)} with {len(self.visualizer.current_polyline)} points")
        
        # Clear current polyline data
        self.visualizer.current_polyline = []
    
    def cancel_current_action(self):
        """Cancel the current polyline drawing"""
        if len(self.visualizer.current_polyline) == 0:
            print("No current polyline to cancel")
            return
        
        print(f"Cancelled polyline with {len(self.visualizer.current_polyline)} points")
        
        # Clear visualization and data
        self.clear_current_polyline_visualization()
        self.visualizer.current_polyline = []
    
    def clear_current_polyline_visualization(self):
        """Clear all current polyline visualizations"""
        # Remove current polyline
        try:
            self.visualizer.plotter.remove_actor('current_polyline')
        except:
            pass
        
        # Remove all current point markers
        actors_to_remove = []
        for name in list(self.visualizer.plotter.renderer.actors.keys()):
            if name.startswith('current_point_'):
                actors_to_remove.append(name)
        
        for actor_name in actors_to_remove:
            try:
                self.visualizer.plotter.remove_actor(actor_name)
            except:
                pass
    
    def update_display(self):
        """Update display for digitize mode"""
        self.visualizer.plotter.set_background('lightblue')
        
        # Deselect all polylines when entering digitization mode
        if hasattr(self.visualizer, 'select_mode'):
            self.visualizer.select_mode.deselect_all()
        
        # Set crosshair cursor for precise digitization
        if self.set_cursor_style(2):  # Crosshair cursor
            print("DIGITIZE MODE: Left click on mesh to add points to new polyline (crosshair cursor)")
        else:
            print("DIGITIZE MODE: Left click on mesh to add points to new polyline")
        
        # Force a small render update to ensure background changes
        try:
            camera = self.visualizer.plotter.camera
            if camera is not None:
                original_azimuth = camera.azimuth
                camera.azimuth = original_azimuth + 0.01
                self.visualizer.plotter.render()
                camera.azimuth = original_azimuth
                self.visualizer.plotter.render()
        except Exception:
            # Just render without camera manipulation
            self.visualizer.plotter.render()
    
    def set_cursor_style(self, cursor_type):
        """Set cursor style using VTK interactor"""
        try:
            # VTK cursor constants
            VTK_CURSOR_ARROW = 1
            VTK_CURSOR_CROSSHAIR = 10
            
            # Map our simple codes to VTK constants
            cursor_map = {
                0: VTK_CURSOR_ARROW,      # Arrow
                2: VTK_CURSOR_CROSSHAIR   # Crosshair
            }
            
            vtk_cursor_type = cursor_map.get(cursor_type, VTK_CURSOR_CROSSHAIR)
            
            # Try setting cursor through various methods
            if hasattr(self.visualizer.plotter, 'iren') and self.visualizer.plotter.iren is not None:
                interactor = self.visualizer.plotter.iren
                
                cursor_methods = [
                    ('SetCurrentCursorShape', vtk_cursor_type),
                    ('SetCursorShape', vtk_cursor_type), 
                    ('SetCurrentCursor', vtk_cursor_type),
                    ('SetCursor', vtk_cursor_type)
                ]
                
                for method_name, cursor_value in cursor_methods:
                    if hasattr(interactor, method_name):
                        try:
                            method = getattr(interactor, method_name)
                            method(cursor_value)
                            self.visualizer.plotter.render()
                            return True
                        except Exception:
                            continue
            
            return False
            
        except Exception as e:
            print(f"Cursor setting failed: {e}")
            return False