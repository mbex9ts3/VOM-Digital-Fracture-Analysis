"""
Digitize mode module for the Polyline Mapper.
Handles transitions to and from digitize mode, point collection,
and polyline creation.
"""

import numpy as np
import pyvista as pv


class DigitizeMode:
    def __init__(self, visualizer):
        """Initialize digitize mode with reference to main visualizer"""
        self.viz = visualizer
        
    def activate(self):
        """Activate digitize mode - blue background, crosshair cursor"""
        print("Activating DIGITIZE mode...")
        
        # Set mode
        self.viz.mode = 'digitize'
        
        # Deselect all polylines when entering digitization mode
        self.viz.deselect_all()
        
        # Update display
        self.update_display()
        
    def update_display(self):
        """Update display for digitize mode with blue background and crosshair cursor"""
        try:
            if not hasattr(self.viz, 'plotter') or self.viz.plotter is None:
                print("Error: Plotter not initialized")
                return
            
            # Set lightblue background
            self.viz.plotter.set_background('lightblue')
            
            # Set crosshair cursor for precise digitization
            cursor_msg = ""
            if self.set_cursor_style(2):  # Crosshair cursor
                cursor_msg = " (crosshair cursor)"
            
            print(f"DIGITIZE MODE: Left click on mesh to add points to new polyline{cursor_msg}")
            
            # Force camera update to ensure background color changes
            self.force_camera_update()
            
        except Exception as e:
            print(f"Error updating digitize mode display: {e}")
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
        """Handle surface picking in digitize mode - add point to current polyline"""
        self.add_point_to_current_polyline(surface_point)
    
    def add_point_to_current_polyline(self, surface_point):
        """Add a surface point to the current polyline being digitized"""
        try:
            self.viz.current_polyline.append(surface_point)
            print(f"Added point {len(self.viz.current_polyline)}: {surface_point}")
            
            # Visualize the picked point
            self.add_point_visualization(surface_point, len(self.viz.current_polyline) - 1)
            
            # Update the current polyline visualization
            self.update_current_polyline_visualization()
            
        except Exception as e:
            print(f"Error adding point to polyline: {e}")
    
    def add_point_visualization(self, point, point_index):
        """Add a visual marker for a picked point with smaller size"""
        # Calculate appropriate sphere size based on mesh bounds (reduced by factor of 3)
        mesh_size = np.linalg.norm(np.array(self.viz.mesh.bounds[1::2]) - np.array(self.viz.mesh.bounds[::2]))
        sphere_radius = mesh_size * 0.0017  # ~0.17% of mesh size (reduced from 0.5%)
        
        sphere = pv.Sphere(radius=sphere_radius, center=point)
        point_name = f'current_point_{point_index}'
        
        # Add the point marker with bright color
        self.viz.plotter.add_mesh(sphere, color='yellow', name=point_name)
    
    def update_current_polyline_visualization(self):
        """Update visualization of the current polyline being drawn"""
        if len(self.viz.current_polyline) < 2:
            return
        
        # Remove previous current polyline visualization
        try:
            self.viz.plotter.remove_actor('current_polyline')
        except:
            pass
        
        # Create polyline from points
        points = np.array(self.viz.current_polyline)
        
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
        self.viz.plotter.add_mesh(polyline, color='red', line_width=12, name='current_polyline')
    
    def finish_current_polyline(self):
        """Finish the current polyline and add it to the collection"""
        if len(self.viz.current_polyline) < 2:
            print("Need at least 2 points to create a polyline")
            return
        
        # Store the polyline
        polyline_data = {
            'points': np.array(self.viz.current_polyline).tolist(),
            'id': len(self.viz.polylines)
        }
        self.viz.polylines.append(polyline_data)
        
        # Remove current polyline and point visualizations
        self.clear_current_polyline_visualization()
        
        # Add permanent polyline visualization
        self.viz.add_polyline_to_scene(len(self.viz.polylines) - 1)
        
        print(f"Finished polyline {len(self.viz.polylines)} with {len(self.viz.current_polyline)} points")
        
        # Clear current polyline data
        self.viz.current_polyline = []
    
    def cancel_current_polyline(self):
        """Cancel the current polyline being drawn"""
        if len(self.viz.current_polyline) == 0:
            print("No current polyline to cancel")
            return
        
        print(f"Cancelled polyline with {len(self.viz.current_polyline)} points")
        
        # Clear visualization and data
        self.clear_current_polyline_visualization()
        self.viz.current_polyline = []
    
    def clear_current_polyline_visualization(self):
        """Clear all current polyline visualizations"""
        # Remove current polyline
        try:
            self.viz.plotter.remove_actor('current_polyline')
        except:
            pass
        
        # Remove all current point markers
        actors_to_remove = []
        for name in list(self.viz.plotter.renderer.actors.keys()):
            if name.startswith('current_point_'):
                actors_to_remove.append(name)
        
        for actor_name in actors_to_remove:
            try:
                self.viz.plotter.remove_actor(actor_name)
            except:
                pass