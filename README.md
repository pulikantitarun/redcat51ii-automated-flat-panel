# Universal automated telescope flat panel — Rev C

Rev C is a single-board automated flat-field panel and motorized dust cover. The
included mechanical preset fits the RedCat 51 II, while the parametric CAD supports
other telescope/dew-shield diameters without changing the electronics.

Control options:

- **ASIAIR Plus:** isolated adjustable-output input on J2.
- **ASCOM:** USB-C to the included ASCOM Alpaca CoverCalibrator bridge.
- **Manual:** long-press the onboard or external button.

ASCOM commands receive a renewable 15-second control lease. If the USB bridge stops,
the controller automatically returns to ASIAIR control. USB-C can power the logic for
safe firmware loading, but MAIN 12 V is required for the servo and light panel.

## Rev C improvements

- valid, separately fused input, LED, and servo branches;
- MCU-switched servo rail that defaults off;
- keyed JST-XH servo connector;
- fail-safe normally-closed limit wiring with RC filtering and ESD protection;
- 12 V presence sensing and USB/12 V logic-power ORing;
- native USB-C programming and ASCOM data;
- test pads and UART recovery header;
- filtered ASIAIR input, command hysteresis, 400 ms stability requirement;
- debounced limits, ramped motion, move timeout, fault reporting, NVS calibration;
- LED warm-up/ramp and brightness gamma setting;
- adjustable-diameter CAD, fit gauge, hard-stop tabs, tether eyes, strain relief,
  gasket channel, and Customizer-friendly OpenSCAD clamp.

## Manufacturing set

For turnkey PCB assembly upload:

1. `pcb/Gerbers_RevC.zip`
2. `pcb/BOM.csv`
3. `pcb/PickAndPlace.csv`

Attach `pcb/PCB_Assembly_Top.pdf` and state that both SMT and through-hole parts are
to be assembled. Recommended board order:

- 120 x 75 mm, 4 layers, 1.6 mm FR-4;
- 2 oz finished copper on all layers;
- ENIG, lead-free assembly;
- green solder mask and white silkscreen;
- electrical test, AOI, and assembly inspection photographs;
- turnkey sourcing with no substitutions for U1, U3, U4, L1, L2, Q1/Q3, F1-F3,
  C2, or C7 without approval.

The routed board passes KiCad error-level DRC with **0 errors and 0 unconnected pads**.
All eight supplied STLs are watertight. Silkscreen-only warnings from edge-mounted
connector footprints are recorded separately and do not affect copper fabrication.

## Default RedCat preset

The included STLs use:

- measured scope/dew-shield OD: 80.0 mm;
- 0.8 mm liner per side;
- 0.5 mm diametral print clearance;
- resulting clamp bore: 82.1 mm;
- optical stack diameter: 82 mm.

Do not assume your telescope matches that measurement. Print the short fit gauge
first. See `mechanical/PRESETS.md` for other diameters.

An additional ready-generated **Askar 103 APO starting preset** is included in
`mechanical/presets/Askar-103-APO`. It uses the published 122 mm dew-shield OD,
a 124.1 mm lined clamp bore, and a 125 mm illuminated stack. Measure the actual
shield and print its fit gauge before using the full clamp.

## Release map

- `pcb/` — Gerbers, BOM, centroid, DRC, PDFs, 3D render, STEP, and KiCad source.
- `mechanical/` — STL/STEP parts, CadQuery generator, and OpenSCAD Customizer source.
- `firmware/` — compiled 8 MB ESP32-S3 image and source sketch.
- `ascom/` — tested Windows Alpaca bridge executable and source.
- `docs/INSTALLATION.md` — universal physical installation and wiring.
- `docs/CIRCUIT.md` — circuit blocks, connector map, and GPIO allocation.
- `docs/CONTROL.md` — ASIAIR, ASCOM, manual operation, and USB command protocol.
- `docs/FIRST_ARTICLE_TEST.md` — mandatory electrical, thermal, and optical checks.
- `docs/PCB_ASSEMBLY_ORDER.md` — manufacturer form values and assembly notes.

## Safety and release status

This is a fabrication-ready open-hardware prototype, not a physically qualified
commercial product. DRC, firmware compilation, ASCOM management API, and mesh integrity
were verified digitally. A real first article must still pass the supplied power,
servo-stall, thermal, ASIAIR-output, full-mount-clearance, and illumination-uniformity
tests before unattended use. Always fit the secondary tether.

## License

Hardware, CAD, firmware, bridge software, and documentation are released under
the GNU General Public License v3.0. See `LICENSE` for the full license text.
