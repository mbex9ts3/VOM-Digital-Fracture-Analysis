import numpy as np
import pyvista as pv


class EditMode:
    def __init__(self, visualizer):
        self.visualizer = visualizer
    
    def can_enter_edit_mode(self):
        """Check if edit mode can be entered"""
        if not hasattr(self.visualizer, 'polylines') or len(self.visualizer.polylines) == 0:
            print("WARNING: No polylines exist yet. Create polylines first before editing.")
            return False
            
        if not hasattr(self.visualizer, 'selected_polyline_idx') or self.visualizer.selected_polyline_idx is None:
            print("WARNING: No polyline selected. Select a polyline first by clicking on it in SELECT mode, then press M to edit.")
            return False
        
        # Validate selected index
        if self.visualizer.selected_polyline_idx >= len(self.visualizer.polylines):
            print("ERROR: Selected polyline index out of range")
            self.visualizer.selected_polyline_idx = None
            print("WARNING: Selected polyline is invalid. Please select a polyline again.")
            return False
        
        return True
    
    def enter_edit_mode(self):
        """Enter edit mode for the selected polyline"""
        try:
            print(f"DEBUG: Switching to edit mode for polyline {self.visualizer.selected_polyline_idx + 1}")
            
            # Show control points for the selected polyline
            self.update_control_point_visualization(self.visualizer.selected_polyline_idx)
            
            print("\n" + "="*50)
            print("EDIT MODE ACTIVATED")
            print("="*50)
            print(f"Editing polyline {self.visualizer.selected_polyline_idx + 1}")
            print("")
            print("Edit Controls:")
            print("• Click to extend polyline from nearest end")
            print("• Click near control points to delete them")
            print("• Click near endpoint of another polyline to join them")
            print("• GREEN sphere = start point, RED sphere = end point")
            print("• ORANGE spheres = middle points")
            print("• Press M to exit edit mode")
            print("="*50 + "\n")
                
        except Exception as e:
            print(f"CRITICAL ERROR in enter_edit_mode: {e}")
            import traceback
            traceback.print_exc()
    
    def exit_edit_mode(self):
        """Exit edit mode"""
        try:
            print("DEBUG: Exiting edit mode...")
            self.clear_control_point_visualization()
            
            # Reset selected polyline visualization back to normal blue
            if self.visualizer.selected_polyline_idx is not None:
                old_selected = self.visualizer.selected_polyline_idx
                self.visualizer.selected_polyline_idx = None  # Temporarily clear selection
                self.visualizer.add_polyline_to_scene(old_selected)  # Redraw as blue
                self.visualizer.selected_polyline_idx = old_selected  # Restore selection
            
            print("Exited edit mode - polyline returned to normal visualization")
            
        except Exception as e:
            print(f"Error exiting edit mode: {e}")
    
    def handle_surface_pick(self, point):
        """Handle surface picking in edit mode"""
        if self.visualizer.selected_polyline_idx is None:
            print("No polyline selected for editing")
            return
        
        try:
            polyline_points = np.array(self.visualizer.polylines[self.visualizer.selected_polyline_idx]['points'])
            mesh_size = np.linalg.norm(np.array(self.visualizer.mesh.bounds[1::2]) - np.array(self.visualizer.mesh.bounds[::2]))
            
            # Use smaller threshold for point deletion (0.3% of mesh size)
            delete_threshold = mesh_size * 0.003
            
            # Find closest control point for potential deletion
            min_distance = float('inf')
            closest_point_idx = None
            
            for i, point_pos in enumerate(polyline_points):
                distance = np.linalg.norm(np.array(point) - point_pos)
                if distance < min_distance:
                    min_distance = distance
                    closest_point_idx = i
            
            print(f"Closest control point: {closest_point_idx}, distance: {min_distance:.6f}, threshold: {delete_threshold:.6f}")
            
            # If pick is close to a control point, delete it
            if closest_point_idx is not None and min_distance < delete_threshold:
                if len(polyline_points) <= 2:
                    print("Cannot delete control point - polyline must have at least 2 points")
                    return
                
                # Delete the control point
                self.visualizer.polylines[self.visualizer.selected_polyline_idx]['points'].pop(closest_point_idx)
                print(f"Deleted control point {closest_point_idx + 1} from polyline {self.visualizer.selected_polyline_idx + 1}")
                
                # Refresh the polyline visualization
                self.refresh_single_polyline_visualization(self.visualizer.selected_polyline_idx)
                return
            
            # Check for potential polyline joining at endpoints
            join_threshold = mesh_size * 0.008  # Slightly larger threshold for joining (0.8% of mesh size)
            join_result = self.check_for_polyline_join(point, join_threshold)
            
            if join_result:
                target_polyline_idx, target_endpoint_idx, target_point = join_result
                print(f"Join opportunity detected with polyline {target_polyline_idx + 1}")
                self.join_polylines(self.visualizer.selected_polyline_idx, target_polyline_idx, target_endpoint_idx, point)
                return
            
            # If not near a control point and no join opportunity, extend the polyline from the nearest end
            # Find which end point (first or last) is closer to the clicked point
            first_point = polyline_points[0]
            last_point = polyline_points[-1]
            
            dist_to_first = np.linalg.norm(np.array(point) - first_point)
            dist_to_last = np.linalg.norm(np.array(point) - last_point)
            
            print(f"Distance to first point: {dist_to_first:.6f}, to last point: {dist_to_last:.6f}")
            
            if dist_to_first < dist_to_last:
                # Extend from the beginning (prepend)
                self.visualizer.polylines[self.visualizer.selected_polyline_idx]['points'].insert(0, point.tolist())
                print(f"Extended polyline {self.visualizer.selected_polyline_idx + 1} from BEGINNING with new point: {point}")
            else:
                # Extend from the end (append)
                self.visualizer.polylines[self.visualizer.selected_polyline_idx]['points'].append(point.tolist())
                print(f"Extended polyline {self.visualizer.selected_polyline_idx + 1} from END with new point: {point}")
            
            # Refresh the polyline visualization
            self.refresh_single_polyline_visualization(self.visualizer.selected_polyline_idx)
            
        except Exception as e:
            print(f"Error in edit mode pick: {e}")
            import traceback
            traceback.print_exc()
    
    def check_for_polyline_join(self, surface_point, threshold):
        """Check if the surface point is near an endpoint of any other polyline"""
        try:
            for i, polyline_data in enumerate(self.visualizer.polylines):
                if i == self.visualizer.selected_polyline_idx:
                    continue  # Skip the currently selected polyline
                
                points = np.array(polyline_data['points'])
                if len(points) < 2:
                    continue
                
                # Check distance to first point (start of polyline)
                first_point = points[0]
                dist_to_first = np.linalg.norm(np.array(surface_point) - first_point)
                
                # Check distance to last point (end of polyline)
                last_point = points[-1]
                dist_to_last = np.linalg.norm(np.array(surface_point) - last_point)
                
                print(f"Polyline {i+1}: dist to start={dist_to_first:.6f}, dist to end={dist_to_last:.6f}, threshold={threshold:.6f}")
                
                # Return the closest endpoint if within threshold
                if dist_to_first < threshold:
                    return (i, 0, first_point)  # polyline_idx, endpoint_idx (0=start), point
                elif dist_to_last < threshold:
                    return (i, -1, last_point)  # polyline_idx, endpoint_idx (-1=end), point
            
            return None  # No join opportunity found
            
        except Exception as e:
            print(f"Error checking for polyline join: {e}")
            return None
    
    def join_polylines(self, source_idx, target_idx, target_endpoint_idx, clicked_point):
        """Join two polylines at their endpoints"""
        try:
            source_points = self.visualizer.polylines[source_idx]['points']
            target_points = self.visualizer.polylines[target_idx]['points']
            
            print(f"Joining polyline {source_idx + 1} with polyline {target_idx + 1}")
            print(f"Source has {len(source_points)} points, target has {len(target_points)} points")
            
            # Determine which end of the source polyline is closer to the join point
            source_first = np.array(source_points[0])
            source_last = np.array(source_points[-1])
            join_point = np.array(clicked_point)
            
            dist_to_source_first = np.linalg.norm(join_point - source_first)
            dist_to_source_last = np.linalg.norm(join_point - source_last)
            
            # Create the new joined polyline
            new_points = []
            
            if dist_to_source_first < dist_to_source_last:
                # Join from the beginning of source polyline
                print("Joining from start of source polyline")
                if target_endpoint_idx == 0:
                    # Target start to source start: reverse source, then add target
                    new_points = list(reversed(source_points)) + target_points[1:]  # Skip duplicate point
                else:
                    # Target end to source start: add target, then source
                    new_points = target_points + source_points[1:]  # Skip duplicate point
            else:
                # Join from the end of source polyline
                print("Joining from end of source polyline")
                if target_endpoint_idx == 0:
                    # Source end to target start: add source, then target
                    new_points = source_points + target_points[1:]  # Skip duplicate point
                else:
                    # Source end to target end: add source, then reversed target
                    new_points = source_points + list(reversed(target_points))[1:]  # Skip duplicate point
            
            print(f"New joined polyline will have {len(new_points)} points")
            
            # Update the source polyline with joined points
            self.visualizer.polylines[source_idx]['points'] = new_points
            
            # Remove the target polyline (it's now part of the source)
            self.remove_polyline(target_idx)
            
            # Update selected index if necessary (target was removed)
            if target_idx < source_idx:
                self.visualizer.selected_polyline_idx -= 1
            
            # Refresh all visualizations
            self.visualizer.refresh_polyline_visualization()
            
            # Update control points for the newly joined polyline
            self.update_control_point_visualization(self.visualizer.selected_polyline_idx)
            
            print(f"Successfully joined polylines! New polyline {self.visualizer.selected_polyline_idx + 1} has {len(new_points)} points")
            
        except Exception as e:
            print(f"Error joining polylines: {e}")
            import traceback
            traceback.print_exc()
    
    def remove_polyline(self, polyline_idx):
        """Remove a polyline from the data structure and visualization"""
        try:
            if polyline_idx >= len(self.visualizer.polylines):
                return
            
            # Remove from scene
            actor_name = f'polyline_{polyline_idx}'
            try:
                self.visualizer.plotter.remove_actor(actor_name)
            except:
                pass
            
            # Remove control points if any
            self.clear_control_point_visualization(polyline_idx)
            
            # Remove from data
            del self.visualizer.polylines[polyline_idx]
            
            print(f"Removed polyline {polyline_idx + 1}")
            
        except Exception as e:
            print(f"Error removing polyline: {e}")
    
    def refresh_single_polyline_visualization(self, polyline_idx):
        """Refresh visualization of a single polyline"""
        if polyline_idx >= len(self.visualizer.polylines):
            return
            
        try:
            # Remove old visualization
            actor_name = f'polyline_{polyline_idx}'
            try:
                self.visualizer.plotter.remove_actor(actor_name)
            except:
                pass
            
            # Re-add with updated data
            self.visualizer.add_polyline_to_scene(polyline_idx)
            
            # Update control point visualization if in edit mode
            if self.visualizer.mode == 'edit' and polyline_idx == self.visualizer.selected_polyline_idx:
                self.update_control_point_visualization(polyline_idx)
                
        except Exception as e:
            print(f"Error refreshing polyline visualization: {e}")
    
    def update_control_point_visualization(self, polyline_idx):
        """Show/hide control points for editing"""
        if polyline_idx >= len(self.visualizer.polylines):
            return
            
        try:
            # Remove existing control point actors
            self.clear_control_point_visualization(polyline_idx)
            
            if self.visualizer.mode == 'edit' and polyline_idx == self.visualizer.selected_polyline_idx:
                # Add control point spheres
                points = np.array(self.visualizer.polylines[polyline_idx]['points'])
                mesh_size = np.linalg.norm(np.array(self.visualizer.mesh.bounds[1::2]) - np.array(self.visualizer.mesh.bounds[::2]))
                sphere_radius = mesh_size * 0.002  # Small spheres for control points
                
                for i, point in enumerate(points):
                    sphere = pv.Sphere(radius=sphere_radius, center=point)
                    # Color end points differently
                    if i == 0:
                        color = 'green'  # First point
                    elif i == len(points) - 1:
                        color = 'red'    # Last point  
                    else:
                        color = 'orange' # Middle points
                        
                    actor_name = f'control_point_{polyline_idx}_{i}'
                    self.visualizer.plotter.add_mesh(sphere, color=color, name=actor_name)
                    
        except Exception as e:
            print(f"Error updating control point visualization: {e}")
    
    def clear_control_point_visualization(self, polyline_idx=None):
        """Clear control point visualizations"""
        try:
            actors_to_remove = []
            for name in list(self.visualizer.plotter.renderer.actors.keys()):
                if polyline_idx is not None:
                    if name.startswith(f'control_point_{polyline_idx}_'):
                        actors_to_remove.append(name)
                else:
                    if name.startswith('control_point_'):
                        actors_to_remove.append(name)
            
            for actor_name in actors_to_remove:
                try:
                    self.visualizer.plotter.remove_actor(actor_name)
                except:
                    pass
        except Exception as e:
            print(f"Error clearing control point visualization: {e}")
    
    def update_display(self):
        """Update display for edit mode"""
        self.visualizer.plotter.set_background('lightgreen')
        
        # Set crosshair cursor for editing operations
        if self.set_cursor_style(2):  # Crosshair cursor for precision
            print("EDIT MODE: Left click to extend selected polyline or click near control points to delete them (crosshair cursor)")
        else:
            print("EDIT MODE: Left click to extend selected polyline or click near control points to delete them")
        
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