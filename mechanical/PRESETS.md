# Mechanical presets

The supplied STL/STEP set is the **RedCat 51 II preset**:

```powershell
python generate_parts.py --scope-diameter 80 --panel-diameter 82
```

For another telescope, measure the actual mounting surface with calipers and run:

```powershell
python generate_parts.py --scope-diameter 95.4 --liner-thickness 1 --fit-clearance 0.5 --panel-diameter 100
```

Always print `01-diameter-fit-gauge.stl` first. Adjust `--fit-clearance` in 0.2 mm
steps until the gauge plus liner fits without force. The PCB, firmware, servo plate,
limit brackets, and electronics enclosure do not change with telescope diameter.

The `universal-scope-clamp-customizer.scad` file exposes the same main clamp settings
in OpenSCAD Customizer for Printables and MakerWorld users.
