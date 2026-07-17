# Release verification

Automated and file-level checks completed for this package:

- KiCad error-level DRC: 0 violations, 0 unconnected pads, 0 footprint errors;
- Gerber archive contains four copper layers, masks, paste, silkscreen, outline,
  Excellon drill, drill map, and Gerber job file;
- BOM covers every non-mechanical PCB reference; the centroid file covers all 70
  placed SMT/hybrid parts and intentionally omits eight through-hole headers and
  jacks plus the DNP test pads;
- all eight supplied STL files are closed, watertight meshes;
- ESP32-S3 firmware compiles with Arduino-ESP32 3.3.10 and ESP32Servo 3.2.1;
- Windows ASCOM Alpaca bridge executable starts and answers its management API;
- mechanical RedCat preset regenerated from the same parameterized source;
- manufacturer upload names and board silkscreen contain no manufacturer branding.

Not yet possible without physical hardware:

- incoming PCB inspection, continuity, load, thermal, and fuse-branch tests;
- real ASIAIR Plus PWM characterization;
- USB serial and ASCOM command tests against the assembled controller;
- servo direction, endpoint, limit, hard-stop, and stall-current tests;
- flat-field brightness, flicker, and illumination-uniformity tests;
- fit and retention tests on each target telescope.

Those are mandatory first-article tests, not optional release polish. Follow
`docs/FIRST_ARTICLE_TEST.md` before fitting the mechanism to optics.
