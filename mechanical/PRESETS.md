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

## Askar 103 APO starting preset

The published dimensional drawing shows a 122 mm dew-shield outside diameter and
a 110 mm main tube. This mechanism is intended to sit at the front, so the starting
preset clamps to the extended dew shield and uses a 125 mm light stack:

```powershell
py -3 generate_parts.py --scope-diameter 122 --panel-diameter 125 --panel-stack 7
```

This produces a 124.1 mm clamp bore with the default 0.8 mm liner and 0.5 mm
diametral clearance. Measure your own shield before printing. Confirm that its
locking screw can carry the complete mechanism without the shield sliding or
rotating; otherwise use a custom axial support tied to the main tube ring.
