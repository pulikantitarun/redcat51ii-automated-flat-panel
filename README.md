# RedCat 51 II automated flat panel - integrated PCBA Revision B

This release replaces the earlier carrier board with one integrated 120 x 75 mm PCB: ESP32-S3, native USB-C programming, protected 12 V input, optically isolated ASIAIR input, 6.0 V / 4 A servo converter, 3.3 V logic converter, LED MOSFET and all field connectors.

## Manufacturing upload set

Upload these three files for a turnkey PCB assembly quote:

1. `pcb/Gerbers_RevB.zip`
2. `pcb/BOM.csv`
3. `pcb/PickAndPlace.csv`

Also attach `pcb/PCB_Assembly_Top.pdf` and the editable KiCad board in the engineering notes. Ask the manufacturer to assemble both SMT and through-hole components. Do not approve substitutions for U1, U3, U4, L1, L2, Q1, C2 or C7 without an electrical review.

Recommended order: 4 layers, 1.6 mm FR-4, 2 oz finished copper on all layers, ENIG, lead-free assembly, impedance control not required, electrical test enabled, turnkey parts sourcing, and component-side inspection photographs.

## Important release status

- KiCad error-level DRC: 0 violations, 0 unconnected pads.
- Routed power widths: 0.8 mm for 12 V / servo rails, 0.5 mm for ground and logic power; specify 2 oz outer copper.
- All eight STL files are closed/watertight meshes.
- The PCB and enclosure dimensions match each other.
- The only owner-specific dimension is the real dew-shield outside diameter. Print `mechanical/01-diameter-fit-gauge.stl` before the clamp. The default assumes 80.0 mm scope OD, 0.8 mm liner and produces an 82.1 mm clamp bore.

This is a fabrication-ready engineering prototype, not a physically qualified commercial product. The manufacturer should perform DFM and parts-availability review before payment. The first assembled board should be powered from a current-limited bench supply and electrically tested before fitting it to the telescope.

## Connections

- `J1 MAIN 12V`: centre-positive 12 V, 4 A recommended. Powers everything.
- `J2 ASIAIR PWM`: centre-positive cable from an adjustable ASIAIR Plus DC output. This input is sensed through U5 and does not power the servo.
- `J3 SERVO`: pin 1 = 6 V, pin 2 = GND, pin 3 = signal.
- `J4 LED PANEL`: pin 1 = protected 12 V, pin 2 = switched LED negative.
- `J5 OPEN LIMIT`: pin 1 signal, pin 2 GND; normally-open switch.
- `J6 CLOSED LIMIT`: pin 1 signal, pin 2 GND; normally-open switch.
- `J7 EXT MANUAL`: pin 1 signal, pin 2 GND; normally-open button.
- `J8 USB-C`: firmware programming/data only. Keep MAIN 12V connected while programming.

## ASIAIR operation

Set the chosen ASIAIR DC port to adjustable/dew-heater mode. Firmware mapping:

- 0-2%: panel opens and LED is off.
- approximately 5%: panel closes and LED remains off (dust-cap mode).
- 8-100%: panel closes and LED brightness follows the setting.

Verify this mapping with the actual ASIAIR Plus before unattended use; firmware thresholds are intentionally editable.

## Package map

- `pcb/` - Gerbers, BOM, centroid, assembly PDF, KiCad source and DRC report.
- `mechanical/` - eight STL and STEP parts plus parametric CadQuery source.
- `firmware/` - Arduino sketch for the onboard ESP32-S3.
- `docs/INSTALLATION.md` - physical assembly and scope installation.
- `docs/CIRCUIT.md` - power/control block diagram and design notes.
- `MECHANICAL_BOM.csv` - everything not installed during PCBA.
