import numpy as np
import time


class SelectMode:
    def __init__(self, visualizer):
        self.visualizer = visualizer
    
    def handle_surface_pick(self, point):
        """Handle surface picking in select mode"""
        # Handle double-click trackball adjustment
        if self.is_double_click(point):
            print("Double-click detected - translating camera/trackball")
            self.translate_camera_to_point(point)
            return  # Don't process as regular selection
        
        # Regular selection
        self.select_polyline_near_point(point)
    
    def is_double_click(self, surface_point):
        """Check if this click constitutes a double-click"""
        current_time = time.time()
        
        # Check time threshold
        if current_time - self.visualizer.last_click_time > self.visualizer.double_click_threshold:
            self.visualizer.last_click_time = current_time
            self.visualizer.last_click_point = surface_point
            return False
        
        # Check spatial threshold (must be reasonably close to previous click)
        if self.visualizer.last_click_point is not None:
            distance = np.linalg.norm(np.array(surface_point) - np.array(self.visualizer.last_click_point))
            mesh_size = np.linalg.norm(np.array(self.visualizer.mesh.bounds[1::2]) - np.array(self.visualizer.mesh.bounds[::2]))
            spatial_threshold = mesh_size * 0.05  # 5% of mesh size
            
            if distance < spatial_threshold:
                print(f"Double-click detected! Distance: {distance:.6f}, threshold: {spatial_threshold:.6f}")
                # Reset click tracking
                self.visualizer.last_click_time = 0
                self.visualizer.last_click_point = None
                return True
        
        # Update tracking for next potential double-click
        self.visualizer.last_click_time = current_time
        self.visualizer.last_click_point = surface_point
        return False
    
    def translate_camera_to_point(self, surface_point):
        """Translate camera 50% towards clicked point, updating trackball center"""
        try:
            if not self.visualizer.plotter or not self.visualizer.plotter.camera:
                print("Camera not available for translation")
                return
            
            current_position = np.array(self.visualizer.plotter.camera.position)
            current_focal_point = np.array(self.visualizer.plotter.camera.focal_point)
            target_point = np.array(surface_point)
            
            print(f"Current camera position: {current_position}")
            print(f"Current focal point: {current_focal_point}")
            print(f"Target point: {target_point}")
            
            # Calculate 50% translation towards the clicked point
            translation_vector = (target_point - current_focal_point) * 0.5
            
            new_position = current_position + translation_vector
            new_focal_point = current_focal_point + translation_vector
            
            print(f"Translation vector: {translation_vector}")
            print(f"New camera position: {new_position}")
            print(f"New focal point: {new_focal_point}")
            
            # Apply new camera settings
            self.visualizer.plotter.camera.position = new_position
            self.visualizer.plotter.camera.focal_point = new_focal_point
            
            # Update the camera and render
            self.visualizer.plotter.render()
            print("Camera translated - trackball center updated")
            
        except Exception as e:
            print(f"Error translating camera: {e}")
            import traceback
            traceback.print_exc()
    
    def select_polyline_near_point(self, click_point):
        """Select a polyline near the clicked point or deselect if clicking on selected polyline"""
        min_distance = float('inf')
        closest_polyline_idx = None
        
        # Calculate smaller, more precise selection threshold
        mesh_size = np.linalg.norm(np.array(self.visualizer.mesh.bounds[1::2]) - np.array(self.visualizer.mesh.bounds[::2]))
        selection_threshold = mesh_size * 0.008  # 0.8% of mesh size
        
        # Check distance to all polylines with better tolerance
        for i, polyline_data in enumerate(self.visualizer.polylines):
            points = np.array(polyline_data['points'])
            
            # Check distance to line segments, not just points
            for j in range(len(points) - 1):
                p1, p2 = points[j], points[j + 1]
                # Distance from point to line segment
                distance = self.point_to_line_distance(click_point, p1, p2)
                if distance < min_distance:
                    min_distance = distance
                    closest_polyline_idx = i
        
        if closest_polyline_idx is not None and min_distance < selection_threshold:
            # If clicking on already selected polyline, deselect it
            if closest_polyline_idx == self.visualizer.selected_polyline_idx:
                self.deselect_all()
            else:
                # Select the new polyline
                self.select_polyline(closest_polyline_idx)
        else:
            # Deselect if clicked far from any polyline
            self.deselect_all()
    
    def point_to_line_distance(self, point, line_start, line_end):
        """Calculate distance from a point to a line segment"""
        point = np.array(point)
        line_start = np.array(line_start)
        line_end = np.array(line_end)
        
        # Vector from line_start to line_end
        line_vec = line_end - line_start
        # Vector from line_start to point
        point_vec = point - line_start
        
        # Handle degenerate case where line_start == line_end
        line_len_sq = np.dot(line_vec, line_vec)
        if line_len_sq == 0:
            return np.linalg.norm(point_vec)
        
        # Project point onto line
        t = max(0, min(1, np.dot(point_vec, line_vec) / line_len_sq))
        projection = line_start + t * line_vec
        
        return np.linalg.norm(point - projection)
    
    def select_polyline(self, polyline_idx):
        """Select a polyline"""
        # Deselect previous
        if self.visualizer.selected_polyline_idx is not None:
            self.visualizer.add_polyline_to_scene(self.visualizer.selected_polyline_idx)  # Reset color
        
        self.visualizer.selected_polyline_idx = polyline_idx
        self.visualizer.add_polyline_to_scene(polyline_idx)  # Highlight
        
        print(f"Selected polyline {polyline_idx + 1} (Press M to edit, Delete to remove)")
    
    def deselect_all(self):
        """Deselect all polylines"""
        if self.visualizer.selected_polyline_idx is not None:
            old_selected = self.visualizer.selected_polyline_idx
            self.visualizer.selected_polyline_idx = None
            self.visualizer.add_polyline_to_scene(old_selected)  # Reset color
            print("Deselected all polylines")
    
    def handle_delete_key(self):
        """Handle Delete key press"""
        if self.visualizer.selected_polyline_idx is None:
            print("No polyline selected for deletion")
            return
        
        # Remove from scene
        actor_name = f'polyline_{self.visualizer.selected_polyline_idx}'
        try:
            self.visualizer.plotter.remove_actor(actor_name)
        except:
            pass
        
        # Remove from data
        deleted_idx = self.visualizer.selected_polyline_idx
        del self.visualizer.polylines[self.visualizer.selected_polyline_idx]
        
        print(f"Deleted polyline {deleted_idx + 1}")
        
        # Clear selection
        self.visualizer.selected_polyline_idx = None
        
        # Refresh all polylines with updated indices
        self.visualizer.refresh_polyline_visualization()
    
    def handle_deselect_key(self):
        """Handle D key press"""
        self.deselect_all()
    
    def update_display(self):
        """Update display for select mode"""
        self.visualizer.plotter.set_background('white')
        
        # Set arrow cursor for selection
        if self.set_cursor_style(0):  # Arrow cursor
            print("SELECT MODE: Left click to select polylines, D to deselect (arrow cursor)")
        else:
            print("SELECT MODE: Left click to select polylines, D to deselect")
    
    def set_cursor_style(self, cursor_type):
        """Set cursor style using VTK interactor"""
        try:
            # VTK cursor constants
            VTK_CURSOR_DEFAULT = 0
            VTK_CURSOR_ARROW = 1
            VTK_CURSOR_CROSSHAIR = 10
            
            # Map our simple codes to VTK constants
            cursor_map = {
                0: VTK_CURSOR_ARROW,      # Arrow
                1: VTK_CURSOR_DEFAULT,    # Hand  
                2: VTK_CURSOR_CROSSHAIR   # Crosshair
            }
            
            vtk_cursor_type = cursor_map.get(cursor_type, VTK_CURSOR_ARROW)
            
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