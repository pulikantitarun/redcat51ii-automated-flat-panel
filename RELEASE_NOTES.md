# Rev C release notes

Rev C turns the original RedCat-specific prototype into a universal automated
flat panel and dust cover. The supplied files remain a ready-to-print RedCat 51
II preset, while the included generator produces a matched clamp and arm for a
measured telescope or dew-shield diameter.

Major changes from Rev B:

- native USB-C control and a Windows ASCOM Alpaca CoverCalibrator bridge;
- adjustable-diameter mechanical generator plus OpenSCAD clamp Customizer;
- USB/12 V logic power ORing and sensed main-power availability;
- separately fused main, LED, and servo branches;
- firmware-controlled servo power, keyed servo plug, fail-safe NC limits,
  filtered inputs, ESD protection, test pads, and UART recovery;
- ASIAIR input filtering, hysteresis, continuous brightness tracking, and safe
  automatic fallback after an ASCOM lease expires;
- motion ramping, timeouts, persistent endpoint calibration, LED warm-up, fault
  reporting, hard stops, tethers, strain relief, and gasket channel;
- complete first-article electrical, thermal, optical, and installation test plan.

This is a fabrication-ready engineering prototype, not a physically qualified
commercial product. Complete `docs/FIRST_ARTICLE_TEST.md` on the first assembled
unit before unattended or telescope-mounted operation.
