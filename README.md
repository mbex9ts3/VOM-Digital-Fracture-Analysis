# trace_mapper

A Python implemented textured mesh editor for the analysis of fractures from virtual outcrop models. 

## File Structure

```
polyline_mapper/
├── polyline_mapper.py    # Main application and coordinator
├── select_mode.py        # Selection mode handler (default mode)
├── digitize_mode.py      # Digitization mode handler
├── edit_mode.py          # Edit mode handler
└── README.md            # This file
```

## Module Overview

### 1. `polyline_mapper.py` (Main Module)
- **Purpose**: Main application coordinator and UI setup
- **Responsibilities**:
  - File loading (PLY mesh and textures)
  - PyVista plotter setup and configuration
  - Key event handling and mode switching
  - Camera controls and view management
  - File I/O operations (save/load polylines)
  - Mode delegation to appropriate handlers

### 2. `select_mode.py` (Default Mode)
- **Purpose**: Handle polyline selection and navigation
- **Key Features**:
  - Click to select/deselect polylines
  - Double-click camera translation
  - Right-click trackball reset
  - Visual feedback for selected polylines
  - Delete selected polylines
- **Controls**:
  - Left Click: Select polyline
  - Double Left Click: Translate camera to point
  - Right Click: Reset trackball
  - D: Deselect all
  - Delete: Remove selected polyline

### 3. `digitize_mode.py` (Polyline Creation)
- **Purpose**: Create new polylines by digitizing points
- **Key Features**:
  - Click to add points to current polyline
  - Real-time visualization during creation
  - Finish or cancel polyline creation
- **Controls**:
  - Left Click: Add point to current polyline
  - Enter: Finish current polyline
  - Escape: Cancel current polyline

### 4. `edit_mode.py` (Polyline Modification)
- **Purpose**: Edit existing polylines
- **Key Features**:
  - Extend polylines from either end
  - Delete control points
  - Join polylines at endpoints
  - Visual control point indicators
- **Controls**:
  - Left Click: Extend polyline or delete control points
  - Click near endpoints of other polylines to join them
  - M: Exit edit mode

## Mode Switching

| Key | Action |
|-----|--------|
| **SPACEBAR** | Toggle between SELECT ↔ DIGITIZE modes |
| **M** | Toggle EDIT mode on/off (requires selected polyline) |

## Workflow

1. **START**: Application opens in SELECT mode
2. **CREATE**: Press SPACEBAR to enter DIGITIZE mode
   - Click points on mesh to create polylines
   - Press ENTER to finish each polyline
3. **SELECT**: Press SPACEBAR to return to SELECT mode
   - Click on polylines to select them
4. **EDIT**: Press M to enter EDIT mode (requires selection)
   - Extend, delete points, or join polylines
   - Press M again to exit edit mode

## Installation and Usage

```bash
# Required dependencies
pip install pyvista numpy

# Run the application
import polyline_mapper
visualizer = polyline_mapper.InteractiveMeshVisualizer()
visualizer.run()
```

## Code Architecture Benefits

### Separation of Concerns
- Each mode handles only its specific functionality
- Main module coordinates between modes
- Easier debugging and testing

### Maintainability
- Changes to one mode don't affect others
- Clear interfaces between modules
- Easier to add new features

### Extensibility
- Easy to add new modes (e.g., measurement mode)
- Mode-specific features can be developed independently
- Plugin-like architecture for future enhancements

## Key Design Patterns

### Mode Pattern
Each mode is a separate class that handles:
- Surface picking callbacks
- Display updates
- Key event handling
- Mode-specific visualizations

### Delegation Pattern
The main visualizer delegates mode-specific operations to the appropriate handler:
```python
if self.mode == 'select':
    self.select_mode.handle_surface_pick(point)
elif self.mode == 'digitize':
    self.digitize_mode.handle_surface_pick(point)
elif self.mode == 'edit':
    self.edit_mode.handle_surface_pick(point)
```

### State Management
- Main visualizer maintains global state (polylines, selection)
- Mode handlers modify state through the visualizer reference
- Consistent state across mode transitions

## Future Enhancements

The modular structure makes it easy to add:
- **Measurement Mode**: Distance and angle measurements
- **Analysis Mode**: Polyline statistics and properties
- **Export Mode**: Different file format exports
- **Collaboration Mode**: Multi-user polyline editing
- **Undo/Redo System**: Command pattern implementation

## Dependencies

- **PyVista**: 3D visualization and mesh handling
- **NumPy**: Numerical operations and array handling
- **Tkinter**: File dialogs (built into Python)
- **JSON**: Configuration and data serialization

## Error Handling

Each module includes comprehensive error handling:
- Graceful fallbacks for cursor setting
- Safe mode transitions
- Detailed debugging output

- Recovery from invalid states

