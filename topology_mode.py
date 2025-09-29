"""
Topology mode module for the Polyline Mapper.
Handles fracture trace topology analysis including automated detection
and manual editing of termination styles (Blind, Crossing, Abutting, Censored).
"""

import numpy as np
import pyvista as pv
import tkinter as tk
from tkinter import messagebox


class TopologyMode:
    def __init__(self, visualizer):
        """Initialize topology mode with reference to main visualizer"""
        self.viz = visualizer
        self.topology_data = {}  # Store topology for each polyline
        self.boundary_vertices = None  # Mesh boundary vertices
        self.selected_endpoint = None  # Currently selected endpoint for editing
        self.tau_threshold = None  # Distance threshold for topology detection
        
    def activate(self):
        """Activate topology mode - goldenrod background, crosshair cursor"""
        try:
            print("DEBUG: 'T' key pressed - entering topology mode...")
            
            # Check if we have polylines
            if not hasattr(self.viz, 'polylines') or len(self.viz.polylines) == 0:
                print("WARNING: No polylines exist yet. Create polylines first before topology analysis.")
                return
            
            # Check plotter state
            if not hasattr(self.viz, 'plotter') or self.viz.plotter is None:
                print("ERROR: Plotter not initialized")
                return
            
            print("DEBUG: Switching to topology mode")
            
            # Set mode
            self.viz.mode = 'topology'
            
            # Update display
            self.update_display()
            
            # Ask user if they want automated detection
            use_automated = self.ask_automated_detection()
            
            if use_automated:
                print("Running automated topology detection...")
                self.run_automated_detection()
            else:
                print("Manual topology editing mode - click endpoints to edit")
                # Initialize empty topology if not already present
                self.initialize_empty_topology()
            
            # Render topology labels
            self.render_topology_labels()
            
            print("\n" + "="*60)
            print("TOPOLOGY MODE ACTIVATED")
            print("="*60)
            print("Topology Definitions:")
            print("  B (GREEN) = Blind: terminates cleanly without intersection")
            print("  X (BLUE) = Crossing: crosses another fracture with taper")
            print("  A (GOLD) = Abutting: terminates abruptly against another")
            print("  C (RED) = Censored: terminates at outcrop boundary")
            print("")
            print("Controls:")
            print("  • Click near endpoint to select for editing")
            print("  • 1: Set selected endpoint as Blind (B)")
            print("  • 2: Set selected endpoint as Crossing (X)")
            print("  • 3: Set selected endpoint as Abutting (A)")
            print("  • 4: Set selected endpoint as Censored (C)")
            print("  • Click again on selected endpoint to deselect")
            print("  • Press T to exit topology mode")
            print("="*60 + "\n")
            
        except Exception as e:
            print(f"CRITICAL ERROR in activate topology mode: {e}")
            import traceback
            traceback.print_exc()
            
            # Try to revert to safe state
            try:
                self.viz.mode = 'select'
                self.viz.select_mode.activate()
                print("ERROR: Failed to enter topology mode. Reverted to SELECT mode.")
            except:
                print("Could not revert to safe mode")
    
    def update_display(self):
        """Update display for topology mode with goldenrod background and crosshair cursor"""
        try:
            if not hasattr(self.viz, 'plotter') or self.viz.plotter is None:
                print("Error: Plotter not initialized")
                return
            
            # Set goldenrod pale background
            self.viz.plotter.set_background('palegoldenrod')
            
            # Set crosshair cursor for precision
            cursor_msg = ""
            if self.set_cursor_style(2):  # Crosshair cursor
                cursor_msg = " (crosshair cursor)"
            
            print(f"TOPOLOGY MODE: Analyzing fracture trace terminations{cursor_msg}")
            
            # Force camera update to ensure background color changes
            self.force_camera_update()
            
        except Exception as e:
            print(f"Error updating topology mode display: {e}")
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
            self.viz.plotter.render()
    
    def set_cursor_style(self, cursor_type):
        """Set cursor style using VTK interactor - crosshair for topology mode"""
        try:
            # VTK cursor constants
            VTK_CURSOR_ARROW = 1
            VTK_CURSOR_HAND = 9
            VTK_CURSOR_CROSSHAIR = 10
            
            cursor_map = {
                0: VTK_CURSOR_ARROW,
                1: VTK_CURSOR_HAND,
                2: VTK_CURSOR_CROSSHAIR
            }
            
            vtk_cursor_type = cursor_map.get(cursor_type, VTK_CURSOR_ARROW)
            
            if hasattr(self.viz.plotter, 'iren') and self.viz.plotter.iren is not None:
                interactor = self.viz.plotter.iren
                
                cursor_methods = [
                    'SetCurrentCursorShape',
                    'SetCursorShape',
                    'SetCurrentCursor',
                    'SetCursor'
                ]
                
                for method_name in cursor_methods:
                    if hasattr(interactor, method_name):
                        try:
                            method = getattr(interactor, method_name)
                            method(vtk_cursor_type)
                            self.viz.plotter.render()
                            return True
                        except:
                            pass
            
            return False
            
        except Exception as e:
            print(f"DEBUG: Cursor setting failed: {e}")
            return False
    
    def ask_automated_detection(self):
        """Ask user if they want automated topology detection"""
        try:
            result = messagebox.askyesno(
                "Automated Topology Detection",
                "Would you like to run automated topology detection?\n\n"
                "This will analyze all polylines and assign termination types based on:\n"
                "• Distance to other polylines\n"
                "• Distance to mesh boundaries\n"
                "• Intersection patterns\n\n"
                "You can manually edit the results afterwards."
            )
            return result
        except Exception as e:
            print(f"Error showing dialog: {e}")
            return False
    
    def compute_mesh_boundary_vertices(self):
        """Compute boundary vertices of the mesh (edges belonging to only one triangle)"""
        try:
            print("Computing mesh boundary vertices...")
            
            if not hasattr(self.viz, 'mesh') or self.viz.mesh is None:
                print("ERROR: No mesh available")
                return None
            
            # Extract edges from mesh
            edges = self.viz.mesh.extract_all_edges()
            
            # Get mesh faces (triangles)
            faces = self.viz.mesh.faces.reshape(-1, 4)[:, 1:]  # Skip count, get vertex indices
            
            # Count edge occurrences
            edge_counts = {}
            for face in faces:
                # Create edges from triangle vertices
                for i in range(3):
                    v1, v2 = face[i], face[(i + 1) % 3]
                    edge = tuple(sorted([v1, v2]))
                    edge_counts[edge] = edge_counts.get(edge, 0) + 1
            
            # Boundary edges appear exactly once
            boundary_edges = [edge for edge, count in edge_counts.items() if count == 1]
            
            # Get unique boundary vertex indices
            boundary_vertex_indices = set()
            for edge in boundary_edges:
                boundary_vertex_indices.add(edge[0])
                boundary_vertex_indices.add(edge[1])
            
            # Get actual boundary vertex coordinates
            boundary_vertices = self.viz.mesh.points[list(boundary_vertex_indices)]
            
            print(f"Found {len(boundary_vertices)} boundary vertices from {len(boundary_edges)} boundary edges")
            
            return boundary_vertices
            
        except Exception as e:
            print(f"Error computing boundary vertices: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def calculate_mean_vertex_spacing(self):
        """Calculate mean vertex spacing across all polylines for threshold"""
        try:
            total_distance = 0
            total_segments = 0
            
            for polyline_data in self.viz.polylines:
                points = np.array(polyline_data['points'])
                for i in range(len(points) - 1):
                    dist = np.linalg.norm(points[i + 1] - points[i])
                    total_distance += dist
                    total_segments += 1
            
            if total_segments == 0:
                return 0.01  # Fallback
            
            mean_spacing = total_distance / total_segments
            print(f"Mean vertex spacing: {mean_spacing:.6f}")
            return mean_spacing
            
        except Exception as e:
            print(f"Error calculating mean spacing: {e}")
            return 0.01
    
    def run_automated_detection(self):
        """Run automated topology detection for all polylines"""
        try:
            # Compute boundary vertices
            self.boundary_vertices = self.compute_mesh_boundary_vertices()
            
            # Calculate threshold (2x mean vertex spacing)
            mean_spacing = self.calculate_mean_vertex_spacing()
            self.tau_threshold = 2.0 * mean_spacing
            print(f"Using tau threshold: {self.tau_threshold:.6f}")
            
            # Initialize topology for all polylines
            for i in range(len(self.viz.polylines)):
                self.topology_data[i] = {
                    'terminations': ['B', 'B'],  # Default: blind at both ends
                    'intersecting_polylines': []
                }
            
            # Analyze each polyline
            for i in range(len(self.viz.polylines)):
                self.analyze_polyline_topology(i)
            
            print("Automated topology detection complete")
            
        except Exception as e:
            print(f"Error in automated detection: {e}")
            import traceback
            traceback.print_exc()
    
    def analyze_polyline_topology(self, polyline_idx):
        """Analyze topology for a single polyline"""
        try:
            points = np.array(self.viz.polylines[polyline_idx]['points'])
            
            if len(points) < 2:
                return
            
            start_point = points[0]
            end_point = points[-1]
            
            # Analyze start point
            start_type, start_intersections = self.classify_endpoint(
                polyline_idx, start_point, points, is_start=True
            )
            
            # Analyze end point
            end_type, end_intersections = self.classify_endpoint(
                polyline_idx, end_point, points, is_start=False
            )
            
            # Store results
            self.topology_data[polyline_idx]['terminations'] = [start_type, end_type]
            self.topology_data[polyline_idx]['intersecting_polylines'] = list(
                set(start_intersections + end_intersections)
            )
            
            print(f"Polyline {polyline_idx + 1}: [{start_type}, {end_type}], "
                  f"intersects: {self.topology_data[polyline_idx]['intersecting_polylines']}")
            
        except Exception as e:
            print(f"Error analyzing polyline {polyline_idx}: {e}")
    
    def classify_endpoint(self, polyline_idx, endpoint, polyline_points, is_start):
        """Classify a single endpoint and return type and intersecting polylines"""
        intersecting_polylines = []
        
        # Check distance to boundary first (highest priority)
        if self.boundary_vertices is not None:
            min_boundary_dist = self.min_distance_to_points(endpoint, self.boundary_vertices)
            if min_boundary_dist < self.tau_threshold:
                return 'C', intersecting_polylines  # Censored
        
        # Check relationships with other polylines
        min_dist_to_others = float('inf')
        intersects_within_tau = False
        within_tau_of_segment = False
        
        for j, other_polyline in enumerate(self.viz.polylines):
            if j == polyline_idx:
                continue
            
            other_points = np.array(other_polyline['points'])
            
            # Check distance to segments
            for k in range(len(other_points) - 1):
                seg_dist = self.point_to_segment_distance(
                    endpoint, other_points[k], other_points[k + 1]
                )
                
                if seg_dist < min_dist_to_others:
                    min_dist_to_others = seg_dist
                
                if seg_dist < self.tau_threshold:
                    within_tau_of_segment = True
                    intersecting_polylines.append(j)
            
            # Check if polylines actually intersect (line-line distance)
            if self.polylines_intersect(polyline_points, other_points, self.tau_threshold):
                intersects_within_tau = True
                if j not in intersecting_polylines:
                    intersecting_polylines.append(j)
        
        # Apply classification logic
        if min_dist_to_others > self.tau_threshold:
            return 'B', intersecting_polylines  # Blind
        elif intersects_within_tau and not within_tau_of_segment:
            return 'X', intersecting_polylines  # Crossing
        elif within_tau_of_segment:
            return 'A', intersecting_polylines  # Abutting
        else:
            return 'B', intersecting_polylines  # Default to blind
    
    def min_distance_to_points(self, point, points_array):
        """Calculate minimum distance from point to array of points"""
        distances = np.linalg.norm(points_array - point, axis=1)
        return np.min(distances)
    
    def point_to_segment_distance(self, point, seg_start, seg_end):
        """Calculate distance from point to line segment"""
        point = np.array(point)
        seg_start = np.array(seg_start)
        seg_end = np.array(seg_end)
        
        line_vec = seg_end - seg_start
        point_vec = point - seg_start
        
        line_len_sq = np.dot(line_vec, line_vec)
        if line_len_sq == 0:
            return np.linalg.norm(point_vec)
        
        t = max(0, min(1, np.dot(point_vec, line_vec) / line_len_sq))
        projection = seg_start + t * line_vec
        
        return np.linalg.norm(point - projection)
    
    def polylines_intersect(self, points1, points2, threshold):
        """Check if two polylines intersect within threshold"""
        for i in range(len(points1) - 1):
            for j in range(len(points2) - 1):
                dist = self.segment_to_segment_distance(
                    points1[i], points1[i + 1],
                    points2[j], points2[j + 1]
                )
                if dist < threshold:
                    return True
        return False
    
    def segment_to_segment_distance(self, p1, p2, p3, p4):
        """Calculate minimum distance between two line segments"""
        # Simplified implementation - minimum distance between segment endpoints and segments
        d1 = self.point_to_segment_distance(p1, p3, p4)
        d2 = self.point_to_segment_distance(p2, p3, p4)
        d3 = self.point_to_segment_distance(p3, p1, p2)
        d4 = self.point_to_segment_distance(p4, p1, p2)
        
        return min(d1, d2, d3, d4)
    
    def initialize_empty_topology(self):
        """Initialize empty topology structure for manual editing"""
        for i in range(len(self.viz.polylines)):
            if i not in self.topology_data:
                self.topology_data[i] = {
                    'terminations': ['B', 'B'],
                    'intersecting_polylines': []
                }
    
    def render_topology_labels(self):
        """Render 3D text labels at polyline endpoints"""
        try:
            # Clear existing topology labels
            self.clear_topology_labels()
            
            # Calculate label size based on mesh
            mesh_size = np.linalg.norm(
                np.array(self.viz.mesh.bounds[1::2]) - np.array(self.viz.mesh.bounds[::2])
            )
            label_height = mesh_size * 0.015
            
            for i, polyline_data in enumerate(self.viz.polylines):
                if i not in self.topology_data:
                    continue
                
                points = np.array(polyline_data['points'])
                terminations = self.topology_data[i]['terminations']
                
                # Render start point label
                self.render_endpoint_label(
                    points[0], terminations[0], i, 0, label_height
                )
                
                # Render end point label
                self.render_endpoint_label(
                    points[-1], terminations[1], i, 1, label_height
                )
            
            self.viz.plotter.render()
            
        except Exception as e:
            print(f"Error rendering topology labels: {e}")
            import traceback
            traceback.print_exc()
    
    def render_endpoint_label(self, position, termination_type, polyline_idx, endpoint_idx, height):
        """Render a single endpoint label"""
        try:
            # Color mapping
            color_map = {
                'B': 'green',
                'X': 'blue',
                'A': 'gold',
                'C': 'red'
            }
            
            color = color_map.get(termination_type, 'gray')
            
            # Create 3D text
            text = pv.Text3D(termination_type, depth=height * 0.3)
            text.points *= height
            text.points += position
            
            actor_name = f'topology_label_{polyline_idx}_{endpoint_idx}'
            
            # Add with bold appearance (larger size)
            self.viz.plotter.add_mesh(
                text,
                color=color,
                name=actor_name,
                render_points_as_spheres=True
            )
            
        except Exception as e:
            print(f"Error rendering endpoint label: {e}")
    
    def clear_topology_labels(self):
        """Clear all topology label actors"""
        try:
            actors_to_remove = []
            for name in list(self.viz.plotter.renderer.actors.keys()):
                if name.startswith('topology_label_') or name.startswith('topology_highlight_'):
                    actors_to_remove.append(name)
            
            for actor_name in actors_to_remove:
                try:
                    self.viz.plotter.remove_actor(actor_name)
                except:
                    pass
        except Exception as e:
            print(f"Error clearing topology labels: {e}")
    
    def handle_pick(self, surface_point):
        """Handle surface picking in topology mode - select endpoints for editing"""
        try:
            # Find closest endpoint
            min_distance = float('inf')
            closest_polyline = None
            closest_endpoint = None
            
            mesh_size = np.linalg.norm(
                np.array(self.viz.mesh.bounds[1::2]) - np.array(self.viz.mesh.bounds[::2])
            )
            selection_threshold = mesh_size * 0.02  # 2% of mesh size
            
            for i, polyline_data in enumerate(self.viz.polylines):
                points = np.array(polyline_data['points'])
                
                # Check start point
                dist_start = np.linalg.norm(np.array(surface_point) - points[0])
                if dist_start < min_distance:
                    min_distance = dist_start
                    closest_polyline = i
                    closest_endpoint = 0
                
                # Check end point
                dist_end = np.linalg.norm(np.array(surface_point) - points[-1])
                if dist_end < min_distance:
                    min_distance = dist_end
                    closest_polyline = i
                    closest_endpoint = 1
            
            print(f"Closest endpoint: polyline {closest_polyline}, endpoint {closest_endpoint}, distance: {min_distance:.6f}")
            
            if min_distance < selection_threshold:
                # Check if clicking on already selected endpoint
                if (self.selected_endpoint and 
                    self.selected_endpoint[0] == closest_polyline and 
                    self.selected_endpoint[1] == closest_endpoint):
                    # Deselect
                    self.deselect_endpoint()
                else:
                    # Select new endpoint
                    self.select_endpoint(closest_polyline, closest_endpoint)
            else:
                # Click far from endpoints - deselect
                self.deselect_endpoint()
                
        except Exception as e:
            print(f"Error in topology pick: {e}")
            import traceback
            traceback.print_exc()
    
    def select_endpoint(self, polyline_idx, endpoint_idx):
        """Select an endpoint for editing"""
        try:
            self.selected_endpoint = (polyline_idx, endpoint_idx)
            
            # Highlight selected endpoint
            points = np.array(self.viz.polylines[polyline_idx]['points'])
            endpoint_pos = points[0] if endpoint_idx == 0 else points[-1]
            
            mesh_size = np.linalg.norm(
                np.array(self.viz.mesh.bounds[1::2]) - np.array(self.viz.mesh.bounds[::2])
            )
            sphere_radius = mesh_size * 0.005
            
            sphere = pv.Sphere(radius=sphere_radius, center=endpoint_pos)
            self.viz.plotter.add_mesh(
                sphere,
                color='yellow',
                name='topology_highlight',
                opacity=0.7
            )
            
            current_type = self.topology_data[polyline_idx]['terminations'][endpoint_idx]
            print(f"Selected polyline {polyline_idx + 1} endpoint {endpoint_idx + 1} "
                  f"(current: {current_type})")
            print("Press 1=Blind, 2=Crossing, 3=Abutting, 4=Censored to change")
            
        except Exception as e:
            print(f"Error selecting endpoint: {e}")
    
    def deselect_endpoint(self):
        """Deselect current endpoint"""
        if self.selected_endpoint:
            try:
                self.viz.plotter.remove_actor('topology_highlight')
            except:
                pass
            
            print("Endpoint deselected")
            self.selected_endpoint = None
    
    def update_selected_endpoint(self, termination_type):
        """Update termination type of selected endpoint"""
        if not self.selected_endpoint:
            print("No endpoint selected")
            return
        
        try:
            polyline_idx, endpoint_idx = self.selected_endpoint
            
            # Update topology data
            self.topology_data[polyline_idx]['terminations'][endpoint_idx] = termination_type
            
            type_names = {'B': 'Blind', 'X': 'Crossing', 'A': 'Abutting', 'C': 'Censored'}
            print(f"Updated polyline {polyline_idx + 1} endpoint {endpoint_idx + 1} to {type_names[termination_type]}")
            
            # Re-render labels
            self.render_topology_labels()
            
            # Deselect after update
            self.deselect_endpoint()
            
        except Exception as e:
            print(f"Error updating endpoint: {e}")
            import traceback
            traceback.print_exc()