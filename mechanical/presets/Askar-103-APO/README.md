# Askar 103 APO starting preset

This preset was generated from the universal Rev C mechanics with:

- mounting surface: 122.0 mm published dew-shield outside diameter;
- soft liner: 0.8 mm per side;
- diametral print clearance: 0.5 mm;
- generated clamp bore: 124.1 mm;
- illuminated panel stack: 125.0 mm diameter x 7.0 mm thick;
- generated panel-tray outside diameter: 147.0 mm;
- servo pivot distance from the optical axis: 93.5 mm.

Generation command:

```powershell
py -3 generate_parts.py --scope-diameter 122 --panel-diameter 125 --panel-stack 7
```

The published Askar drawing also lists a 110 mm main-tube diameter, but the
standard short mechanism is positioned at the front and therefore uses the
extended dew shield as its mounting surface. The renders are dimensionally
representative installation references; they are not manufacturer CAD.

Before printing the clamp, measure the exact outside diameter of your own dew
shield and print `01-diameter-fit-gauge.stl`. Confirm that the dew-shield lock
holds securely against the mechanism's weight and servo torque. If the shield
can slide or rotate, add a separate axial restraint tied to the factory tube
ring rather than relying on clamp force against the optical assembly.

Source dimensions:
https://www.firstlightoptics.com/user/manuals/askar-103-apo-manual.pdf
