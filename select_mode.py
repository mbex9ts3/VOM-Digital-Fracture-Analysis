"""
Select mode module for the Polyline Mapper.
Handles transitions to and from select mode, polyline selection,
and double-click camera translation.
"""

import numpy as np
import time


class SelectMode:
    def __init__(self, visualizer):
        """Initialize select mode with reference to main visualizer"""
        self.viz = visualizer
        
    def activate(self):
        """Activate select mode - white background, arrow cursor"""
        print("Activating SELECT mode...")
        
        # Clear any edit mode visualization if coming from edit mode
        if self.viz.mode == 'edit':
            self.clear_control_point_visualization()
            # Reset selected polyline visualization back to normal blue
            if self.viz.selected_polyline_idx is not None:
                old_selected = self.viz.selected_polyline_idx
                self.viz.selected_polyline_idx = None  # Temporarily clear selection
                self.viz.add_polyline_to_scene(old_selected)  # Redraw as blue
                self.viz.selected_polyline_idx = old_selected  # Restore selection
        
        # Clear any digitize mode visualization if coming from digitize mode
        if self.viz.mode == 'digitize':
            # Finish current polyline if in progress
            if len(self.viz.current_polyline) > 1:
                self.viz.digitize_mode.finish_current_polyline()
            elif len(self.viz.current_polyline) > 0:
                self.viz.digitize_mode.cancel_current_polyline()
        
        # Set mode
        self.viz.mode = 'select'
        
        # Update display
        self.update_display()
        
    def update_display(self):
        """Update display for select mode with white background and arrow cursor"""
        try:
            if not hasattr(self.viz, 'plotter') or self.viz.plotter is None:
                print("Error: Plotter not initialized")
                return
            
            # Set white background
            self.viz.plotter.set_background('white')
            
            # Set arrow cursor for selection
            cursor_msg = ""
            if self.set_cursor_style(0):  # Arrow cursor
                cursor_msg = " (arrow cursor)"
            
            print(f"SELECT MODE: Left click to select polylines, D to deselect{cursor_msg}")
            
            # Force camera update to ensure background color changes
            self.force_camera_update()
            
        except Exception as e:
            print(f"Error updating select mode display: {e}")
            import traceback
            traceback.print_exc()
    
    def force_camera_update(self):
        """Force a tiny camera rotation to trigger background update"""
        try:
            camera = self.viz.plotter.camera
            if camera is not None:
                original_azimuth = camera.azimuth
                camera.azimuth = original_azimuth + 0.01
                self.viz.plotter.render()
                camera.azimuth = original_azimuth
                self.viz.plotter.render()
        except Exception as camera_e:
            print(f"Camera update failed (non-critical): {camera_e}")
            # Just render without camera manipulation
            self.viz.plotter.render()
    
    def set_cursor_style(self, cursor_type):
        """Set cursor style using VTK interactor - with VTK constants and detailed debugging"""
        try:
            print(f"DEBUG: Attempting to set cursor to type {cursor_type}")
            
            # VTK cursor constants (these are the actual VTK values)
            VTK_CURSOR_DEFAULT = 0
            VTK_CURSOR_ARROW = 1
            VTK_CURSOR_SIZENE = 2
            VTK_CURSOR_SIZENW = 3
            VTK_CURSOR_SIZESW = 4
            VTK_CURSOR_SIZESE = 5
            VTK_CURSOR_SIZENS = 6
            VTK_CURSOR_SIZEWE = 7
            VTK_CURSOR_SIZEALL = 8
            VTK_CURSOR_HAND = 9
            VTK_CURSOR_CROSSHAIR = 10
            
            # Map our simple codes to VTK constants
            cursor_map = {
                0: VTK_CURSOR_ARROW,      # Arrow
                1: VTK_CURSOR_HAND,       # Hand  
                2: VTK_CURSOR_CROSSHAIR   # Crosshair
            }
            
            vtk_cursor_type = cursor_map.get(cursor_type, VTK_CURSOR_ARROW)
            print(f"DEBUG: Mapped cursor {cursor_type} to VTK constant {vtk_cursor_type}")
            
            # Check what VTK components are available
            print(f"DEBUG: Has iren: {hasattr(self.viz.plotter, 'iren')}")
            print(f"DEBUG: Has render_window: {hasattr(self.viz.plotter, 'render_window')}")
            print(f"DEBUG: Has window: {hasattr(self.viz.plotter, 'window')}")
            
            # Method 1: Direct VTK render window interactor
            if hasattr(self.viz.plotter, 'iren') and self.viz.plotter.iren is not None:
                interactor = self.viz.plotter.iren
                print(f"DEBUG: Got interactor type: {type(interactor)}")
                print(f"DEBUG: Interactor class name: {interactor.__class__.__name__}")
                
                # List all available methods on interactor
                cursor_related_methods = [m for m in dir(interactor) if 'cursor' in m.lower()]
                print(f"DEBUG: Available cursor-related methods on interactor: {cursor_related_methods}")
                
                # Try different VTK cursor methods with correct constants
                cursor_methods = [
                    ('SetCurrentCursorShape', vtk_cursor_type),
                    ('SetCursorShape', vtk_cursor_type), 
                    ('SetCurrentCursor', vtk_cursor_type),
                    ('SetCursor', vtk_cursor_type)
                ]
                
                for method_name, cursor_value in cursor_methods:
                    if hasattr(interactor, method_name):
                        print(f"DEBUG: Found method {method_name} on interactor")
                        try:
                            method = getattr(interactor, method_name)
                            method(cursor_value)
                            print(f"DEBUG: Successfully called {method_name}({cursor_value})")
                            self.viz.plotter.render()
                            return True
                        except Exception as e:
                            print(f"DEBUG: {method_name} failed: {e}")
                    else:
                        print(f"DEBUG: Method {method_name} NOT found on interactor")
                
                # Try through the render window from interactor
                if hasattr(interactor, 'GetRenderWindow'):
                    render_window = interactor.GetRenderWindow()
                    print(f"DEBUG: Got render window from interactor: {type(render_window)}")
                    
                    if render_window:
                        # List cursor methods on render window
                        rw_cursor_methods = [m for m in dir(render_window) if 'cursor' in m.lower()]
                        print(f"DEBUG: Cursor methods on render_window: {rw_cursor_methods}")
                        
                        cursor_rw_methods = [
                            ('SetCurrentCursor', vtk_cursor_type),
                            ('SetCursor', vtk_cursor_type),
                            ('SetDesiredUpdateRate', None)  # Sometimes needed to refresh
                        ]
                        
                        for method_name, cursor_value in cursor_rw_methods:
                            if method_name == 'SetDesiredUpdateRate':
                                continue
                            if hasattr(render_window, method_name):
                                print(f"DEBUG: Trying render_window.{method_name}")
                                try:
                                    method = getattr(render_window, method_name)
                                    method(cursor_value)
                                    render_window.Render()  # Force render on window
                                    print(f"DEBUG: Successfully called render_window.{method_name}")
                                    return True
                                except Exception as e:
                                    print(f"DEBUG: render_window.{method_name} failed: {e}")
            
            # Method 2: Through plotter's render_window directly
            if hasattr(self.viz.plotter, 'render_window') and self.viz.plotter.render_window:
                print("DEBUG: Trying through plotter.render_window directly")
                render_window = self.viz.plotter.render_window
                print(f"DEBUG: Direct render_window type: {type(render_window)}")
                
                # Check for VTK render window
                if hasattr(render_window, '__class__'):
                    print(f"DEBUG: Render window class: {render_window.__class__.__name__}")
                
                cursor_rw_methods = [
                    ('SetCurrentCursor', vtk_cursor_type),
                    ('SetCursor', vtk_cursor_type)
                ]
                
                for method_name, cursor_value in cursor_rw_methods:
                    if hasattr(render_window, method_name):
                        print(f"DEBUG: Found {method_name} on direct render_window")
                        try:
                            method = getattr(render_window, method_name)
                            method(cursor_value)
                            render_window.Render()
                            print(f"DEBUG: Successfully set cursor via direct render_window")
                            return True
                        except Exception as e:
                            print(f"DEBUG: Direct render_window.{method_name} failed: {e}")
            
            # Method 3: Try through plotter.window (sometimes different from render_window)
            if hasattr(self.viz.plotter, 'window'):
                print("DEBUG: Trying through plotter.window")
                window = self.viz.plotter.window
                if window and hasattr(window, 'SetCurrentCursor'):
                    try:
                        window.SetCurrentCursor(vtk_cursor_type)
                        print("DEBUG: Set cursor through plotter.window")
                        return True
                    except Exception as e:
                        print(f"DEBUG: plotter.window cursor setting failed: {e}")
            
            print("DEBUG: WARNING - No cursor methods worked. Cursor will remain default.")
            print("DEBUG: This might be a platform/backend limitation")
            return False
            
        except Exception as e:
            print(f"DEBUG: Cursor setting completely failed with exception: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def handle_pick(self, surface_point):
        """Handle surface picking in select mode - includes double-click detection"""
        # Check for double-click to translate camera
        if self.is_double_click(surface_point):
            print("Double-click detected - translating camera/trackball")
            self.translate_camera_to_point(surface_point)
            return  # Don't process as regular selection
        
        # Otherwise handle normal selection
        self.select_polyline_near_point(surface_point)
    
    def is_double_click(self, surface_point):
        """Check if this click constitutes a double-click"""
        current_time = time.time()
        
        # Check time threshold
        if current_time - self.viz.last_click_time > self.viz.double_click_threshold:
            self.viz.last_click_time = current_time
            self.viz.last_click_point = surface_point
            return False
        
        # Check spatial threshold (must be reasonably close to previous click)
        if self.viz.last_click_point is not None:
            distance = np.linalg.norm(np.array(surface_point) - np.array(self.viz.last_click_point))
            mesh_size = np.linalg.norm(np.array(self.viz.mesh.bounds[1::2]) - np.array(self.viz.mesh.bounds[::2]))
            spatial_threshold = mesh_size * 0.05  # 5% of mesh size
            
            if distance < spatial_threshold:
                print(f"Double-click detected! Distance: {distance:.6f}, threshold: {spatial_threshold:.6f}")
                # Reset click tracking
                self.viz.last_click_time = 0
                self.viz.last_click_point = None
                return True
        
        # Update tracking for next potential double-click
        self.viz.last_click_time = current_time
        self.viz.last_click_point = surface_point
        return False
    
    def translate_camera_to_point(self, surface_point):
        """Translate camera 50% towards clicked point, updating trackball center"""
        try:
            if not self.viz.plotter or not self.viz.plotter.camera:
                print("Camera not available for translation")
                return
            
            current_position = np.array(self.viz.plotter.camera.position)
            current_focal_point = np.array(self.viz.plotter.camera.focal_point)
            target_point = np.array(surface_point)
            
            print(f"Current camera position: {current_position}")
            print(f"Current focal point: {current_focal_point}")
            print(f"Target point: {target_point}")
            
            # Calculate 50% translation towards the clicked point
            # Move both camera position and focal point by the same vector
            translation_vector = (target_point - current_focal_point) * 0.5
            
            new_position = current_position + translation_vector
            new_focal_point = current_focal_point + translation_vector
            
            print(f"Translation vector: {translation_vector}")
            print(f"New camera position: {new_position}")
            print(f"New focal point: {new_focal_point}")
            
            # Apply new camera settings
            self.viz.plotter.camera.position = new_position
            self.viz.plotter.camera.focal_point = new_focal_point
            
            # Update the camera and render
            self.viz.plotter.render()
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
        mesh_size = np.linalg.norm(np.array(self.viz.mesh.bounds[1::2]) - np.array(self.viz.mesh.bounds[::2]))
        selection_threshold = mesh_size * 0.008  # 0.8% of mesh size
        
        # Check distance to all polylines with better tolerance
        for i, polyline_data in enumerate(self.viz.polylines):
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
            if closest_polyline_idx == self.viz.selected_polyline_idx:
                self.viz.deselect_all()
            else:
                # Select the new polyline
                self.select_polyline(closest_polyline_idx)
        else:
            # Deselect if clicked far from any polyline
            self.viz.deselect_all()
    
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
        if self.viz.selected_polyline_idx is not None:
            self.viz.add_polyline_to_scene(self.viz.selected_polyline_idx)  # Reset color
        
        self.viz.selected_polyline_idx = polyline_idx
        self.viz.add_polyline_to_scene(polyline_idx)  # Highlight
        
        print(f"Selected polyline {polyline_idx + 1} (Press M to edit, Delete to remove)")
    
    def clear_control_point_visualization(self, polyline_idx=None):
        """Clear control point visualizations from edit mode"""
        try:
            actors_to_remove = []
            for name in list(self.viz.plotter.renderer.actors.keys()):
                if polyline_idx is not None:
                    if name.startswith(f'control_point_{polyline_idx}_'):
                        actors_to_remove.append(name)
                else:
                    if name.startswith('control_point_'):
                        actors_to_remove.append(name)
            
            for actor_name in actors_to_remove:
                try:
                    self.viz.plotter.remove_actor(actor_name)
                except:
                    pass
        except Exception as e:
            print(f"Error clearing control point visualization: {e}")