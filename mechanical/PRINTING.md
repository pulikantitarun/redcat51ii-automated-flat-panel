# Printing and sizing

Use PETG, ASA, or ABS. Do not use PLA for a clamp or enclosure that may be left
in sunlight. Start with 0.20 mm layers, four perimeters, five top/bottom layers,
and 35-45% gyroid infill. Use 60% infill for the scope clamp and panel tray.
Print two copies of part 08.

## Fit a different telescope

Measure the outside diameter of the tube or dew shield with calipers at the
actual clamp location. Generate a short gauge before printing the full mount:

```powershell
py -3 generate_parts.py --scope-diameter 100 --panel-diameter 105
```

The clamp bore is calculated from the measured diameter, liner thickness, and
print clearance. The defaults use a 0.8 mm soft liner and 0.5 mm diametral
clearance. Adjust them when needed:

```powershell
py -3 generate_parts.py --scope-diameter 120.4 --liner-thickness 1.0 --fit-clearance 0.6 --panel-diameter 125 --panel-stack 7
```

Print `01-diameter-fit-gauge.stl` first. The gauge should slide over the scope
with the liner fitted, without forcing or scratching the finish. If it does not,
change `--fit-clearance` and regenerate. Never scale the STL non-uniformly in a
slicer because that also distorts screw holes and hardware interfaces.

The OpenSCAD file `universal-scope-clamp-customizer.scad` is an alternative for
users who only need a custom clamp. The complete matched assembly should be
generated with `generate_parts.py`.

## Orientation and hardware

- Fit gauge and retaining ring: print flat.
- Scope clamp: print with its broad split-clamp face on the bed.
- Servo plate and tray: orient for continuous perimeters through the hinge and
  arm; use supports from the build plate only where your slicer requires them.
- Enclosure base and lid: print their largest flat faces on the bed.
- Limit brackets: print flat and make two.

The enclosure matches the Rev C 120 x 75 mm PCB and its asymmetric mounting
holes. Install M3 screws into printed standoffs gently; use heat-set inserts if
the enclosure will be opened repeatedly. Add a soft, non-marring liner inside
the clamp and use the integrated tether eyes as a secondary retention point.
