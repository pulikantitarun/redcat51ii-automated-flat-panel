# RedCat 51 II Automated Flat Panel — Revision C

A servo-driven flat panel / dust cover for the William Optics RedCat 51 II,
commanded from an ASIAIR dew-heater port.

---

## Read this before anything else

Rev B was described as fabrication-ready. It was not. It had a firmware loop
that would hold a stalled 20 kg servo at ~2.7 A indefinitely, an ASIAIR input
that could not physically work, four disconnected bodies in an STL, and not one
copper zone on a 4-layer board carrying two switching regulators. It also had
"0 DRC violations", which is exactly why that number should never have
reassured anyone.

**Rev C is not fabrication-ready either.** It is *correct as far as it has been
checked*, and it now tells you loudly where the checking stops. The difference
between Rev B and Rev C is not that Rev C is finished — it is that Rev C
asserts its own assumptions instead of hiding them.

### Status by subsystem

| Subsystem | State | Verified how |
|---|---|---|
| Mechanical | **Verified** | 19 numeric clearance assertions pass; all 10 meshes single-body and watertight; assembly STEP builds in one shared coordinate frame |
| Firmware | **Reviewed, not run** | No ESP32 toolchain was available; not compiled, not flashed, not measured |
| PCB netlist & stackup | **Asserted** | 36 netlist/stackup assertions pass (`verify_board.py`) |
| PCB routing | **Not done** | Signals unrouted; needs the freerouting round-trip + manual widening |
| PCB schematic / ERC | **Does not exist** | ← the single biggest remaining risk |

---

## The four numbers you must measure

Everything in the mechanical model derives from these. Each has a cheap coupon
to check it. Print the coupons first — they are minutes of filament, and every
one of them protects hours of it.

| # | Parameter | Default | Coupon | What happens if it's wrong |
|---|---|---|---|---|
| 1 | `SCOPE_DIAMETER` | 80.0 mm | `01-diameter-fit-gauge` | Clamp won't fit, or won't grip |
| 2 | `SERVO_SHAFT_OFFSET` | 10.0 mm | `09-servo-shaft-gauge` | Closed panel sits 7–13 mm off the optical axis |
| 3 | `SERVO_EAR_TO_TOP` | 10.0 mm | `09-servo-shaft-gauge` | Tray fouls the servo, or floats above the horn |
| 4 | `DC_JACK_AXIS_Z` | 4.7 mm | `10-connector-wall-coupon` | Barrel plugs don't line up with their holes |

The 80 mm default deserves special suspicion: William Optics quote
"228 × 80 mm with the retracted dew shield". That is a *marketing envelope
figure*, not a measurement of the surface this clamp grips. Measure it.

**A fifth measurement, electrical, is just as important — see below.**

---

## The ASIAIR ground question — measure this before you build the board

Rev C replaces Rev B's opto-isolator with a plain resistive divider into an
ADC. That is the right call (see *Firmware* below), but it costs you the
galvanic isolation, and it therefore **assumes the ASIAIR switches the HIGH
side of its dew ports** — i.e. that the port's negative terminal is common with
the ASIAIR's own 12 V input negative.

All the indirect evidence says it does. People run grounded 12 V→5 V buck
converters off these ports, feeding USB devices that plug straight back into
the ASIAIR, which would be a dead short across a low-side switch. And a
multimeter inline reads ~6 V average at the 50 % slider position, which is what
a high-side switch with a grounded return looks like.

But I have not put a meter on one, and neither should you take my word for it:

> **Check continuity between the ASIAIR dew port's barrel SLEEVE and the
> ASIAIR's power input NEGATIVE terminal.**
> - Near 0 Ω → common ground. Build as drawn.
> - Anything else → **stop.** Do not fit R19. The front end needs rethinking
>   and I'd want to see the measurement before redesigning it.

Thirty seconds with a multimeter, before you spend money.

---

## What changed, and why

### Mechanical — `mechanical/generate_parts.py`

Rev B built every part in its own private coordinate system and never
assembled them. That is how all of the following escaped:

- **The enclosure was built centred on z=0 but every cut-out was placed as if
  the floor were z=0.** The connector openings sat ~14 mm too high and breached
  the top rim.
- **The four PCB standoffs floated in mid-air.** They were extruded z=0..7
  while the cavity floor sat at z=−11.5. The STL contained five disconnected
  bodies. A slicer would have printed four little pillars lying on the bed.
- **The tray pivot assumed the servo's output shaft is at the centre of its
  body.** It is not — a standard 40 mm servo has its shaft offset ~10 mm. The
  closed panel would have sat 7–13 mm off the optical axis.
- **The servo platform met the clamp with a ~1 mm sliver of overlap**, no
  gussets, no fillets.
- **The limit-switch bracket's base and upright met on a single plane with zero
  overlap** — a degenerate union that exports a non-watertight mesh.

Rev C builds every part in **one shared scope coordinate frame**, asserts the
clearances numerically, and exports an assembly STEP so the next mistake of
this class is visible instead of latent.

Also new in Rev C:

- **The lid is screwed, not friction-fit.** This box lives outdoors, upside
  down, in dew, on a moving mount. Four M3 corner bosses with heat-set inserts,
  outboard of the cavity so they cost no internal volume. The lid's spigot lip
  is notched around them.
- **Strap ears.** The box now has somewhere to attach. Thread a hook-and-loop
  strap down through one ear, under the dovetail bar, up through the other.
  **Hang it off the dovetail, not the dew shield** — the shield is a slip joint
  and it will happily let go of an 80 mm tube.

Run it:

```bash
cd mechanical && python3 generate_parts.py
```

It prints 19 clearance assertions and exits non-zero if any fail. All 10 STLs
are single-body and watertight; verify with the trimesh snippet in
`docs/verification.md` if you want to confirm that yourself rather than trust
this file.

### Firmware — `firmware/redcat_flat_panel/`

**1. The ASIAIR input is no longer a duty-cycle measurement.** Rev B called
`pulseIn()` on an opto to recover the ASIAIR's PWM duty. That cannot work on an
ASIAIR Plus:

- The Plus **capacitively filters** its power outputs. Rev B's opto drew ~4.9 mA
  through a 2.2 k resistor — nowhere near enough to discharge that filter inside
  a 20 ms period. The port never left 12 V, so **every slider position read as
  100 %**.
- The port period is 20 ms and Rev B's `pulseIn` timeout was 30 ms. A missed
  edge returned 0 → "command 0" → **the flap flings open in the middle of a
  flat sequence.**

Rev C stops fighting the filter and uses it: it loads the port properly (470 Ω,
1 W) and measures the **average voltage** on ADC1. The same filtering that
destroys duty-sniffing is what makes the average track the slider — 50 % reads
~6 V, 100 % reads ~12 V.

**2. A failed move no longer retries forever.** Rev B's `moveFlap()` set
`isClosed = false` on timeout *regardless of which direction it was moving*. So
a jammed flap reported "open", the next loop pass commanded "close" again ~50 ms
later, and it did that forever — holding a stalled DS3218 at ~2.7 A until
something gave up. Rev C latches a **FAULT** after 3 bounded attempts, detaches
the servo between every attempt, and refuses to move again until a human holds
the button for 2 s.

**3. The move is non-blocking.** Rev B blocked inside `moveFlap()` for up to 5 s
with the button dead.

**4. The ASIAIR boot transient is handled.** Every ASIAIR drives all power ports
to FULL for a few seconds at boot before loading its saved settings. Rev B read
that as "100 % — close and light up". Rev C ignores the input until it has been
stable for 6 s.

**5. Thresholds no longer collide.** Rev B used 3 % / 8 % boundaries when the
ASIAIR slider's minimum non-zero step is **5 %**, with no hysteresis — a reading
sitting on a boundary would dither the flap. Rev C works in **port volts**
(what the board can actually observe) with 0.3 V of hysteresis at every
boundary.

**6. It does not move on boot.** Rev B blindly drove to OPEN in `setup()`,
slamming the flap against its stop every time the ASIAIR's 12 V rail browned out
on a mount slew. Rev C adopts whatever state the limit switches report.

> **This firmware has not been compiled.** There was no ESP32 toolchain
> available in the environment it was written in. Expect to fix at least a
> typo. Read it before you flash it.

**Calibration:** if the panel lights at the wrong slider position, put a
voltmeter on the ASIAIR port at 100 %, set `PORT_FULL_V` to what you actually
read (a "12 V" supply is usually 12.2–13.8 V), and reflash. Nothing else needs
touching.

### PCB — `pcb/source/generate_board.py`

**1. Copper zones.** Rev B had **none** — zero zones, zero G36 fill records in
every gerber, on a 4-layer board with a 4 A switcher. GND was 129 individual
tracks totalling ~500 mm.

Rev C makes **both inner layers solid GND** and pours GND on F.Cu/B.Cu, with
124 stitching vias. Every switching node now has an unbroken return directly
beneath it.

Why two ground planes rather than GND + a split power plane: the Rev B
placement interleaves +12V, +6V and +3V3 across the same X range, so **no
rectangular power split is possible without re-placing every part**. SIG/GND/
GND/SIG is the correct stackup for *this* placement, costs nothing, spreads
regulator heat, and removes any chance of a return path crossing a plane split.
+12V and +6V remain wide tracks, as they were in Rev B — but Rev B's actual
defect was that *GND* had no plane, and that is now fixed twice over.

**2. USBLC6-2SC6 net assignment fixed.** Pins 1 and 6 are one internal node;
3 and 4 are another. Rev B straddled the 22 Ω series resistors across them,
**shorting both out**. DRC was perfectly happy.

**3. J3 re-pinned to GND / V+ / SIG.** Rev B wired 6V / GND / SIG, which lands
6 V on the servo lead's black wire whichever way round you plug it in.

**4. Q1's gate is no longer tied straight to GND.** Vgs was the full rail. While
D1 clamps a surge it would have exceeded the AO4407A's ±20 V limit and destroyed
the FET. Now 100 k to GND plus a 10 V zener gate-to-source.

**5. D1 SMBJ18A → SMBJ14A.** An 18 V standoff part clamps at ~29 V — above the
AO4407A's 30 V Vds rating with no margin. 14 V standoff clamps at ~23 V.

**6. F1 3 A → 4 A.** A 3 A PTC derates to ~2.4 A hold in a sealed box, below the
DS3218's 2.7 A stall. It would have nuisance-tripped mid-sequence.

**7. Buck input capacitance raised.** A 10 µF 25 V 0805 X5R at 12 V DC bias
derates to ~4–5 µF; that was the *entire* input reservoir for a 4 A regulator.
Now 2× 10 µF 1210 plus 100 nF per regulator.

**8. Minimum drill 0.2 → 0.3 mm**, above every fab's surcharge threshold.

Run it:

```bash
cd pcb/source
python3 generate_board.py     # places parts, nets, zones, stitching vias
python3 verify_board.py       # 36 netlist/stackup assertions
python3 generate_bom.py       # BOM generated FROM the board, so it can't drift
```

---

## What is still missing — the honest list

1. **There is no schematic, and therefore there has been no ERC.** This is the
   biggest risk in the project. A DRC pass against a hand-typed netlist only
   proves the copper matches what you typed; it cannot tell you the netlist
   itself is wrong. That is *precisely* how the USBLC6 short and the servo
   header pinout survived Rev B's "0 DRC violations". `verify_board.py` raises
   the floor but it is not ERC. **Draw the schematic before you spend money.**

2. **Signals are not routed.** `generate_board.py` emits placement, nets and
   pours. The Rev B flow still applies — `export_dsn.py` → freerouting →
   `import_ses.py` → manually widen the +12 V / +6 V paths — **except that GND
   must no longer be handed to the autorouter.** It lives on the planes now.

3. **Zones are defined but not filled in the saved file.** pcbnew's `ZONE_FILLER`
   segfaults when driven from standalone Python on KiCad 7 (verified: it does so
   even under a wx app and a virtual X display). The zones are defined, netted
   and layered correctly — but **KiCad plots gerbers from the *stored* fill.**
   Open the board in pcbnew, press **B**, run DRC, *then* plot. Plotting without
   filling gives you planeless gerbers — the exact Rev B failure, wearing a
   Rev C label.

4. **The firmware has never been compiled or run.**

5. **The board was generated here against KiCad 7**, because that is what was
   installable; you built Rev B on KiCad 10. The script is version-tolerant now
   (it searches for the footprint libraries instead of hard-coding
   `C:\Users\tarun\...`, and accepts alternate footprint names), but **re-run it
   on your KiCad 10** and use that output. One visible symptom: the BOM here
   lists `SW_Push_1P1T_NO_CK_KMR2` for SW1–3 because KiCad 7's library lacks the
   TL3301; KiCad 10 will pick the TL3301 as intended.

6. **The 6 V rail is still track-routed at up to 2.7 A.** Widen it by hand after
   routing. 3 mm on 1 oz copper is roughly 3 A.

---

## Suggested order of work

1. Multimeter on the ASIAIR dew port ground. **30 seconds. Do it first.**
2. Print `01`, `09`, `10`. Measure the four parameters. Update the constants.
3. Re-run `generate_parts.py`. Confirm 19/19 assertions still pass.
4. Print `02`–`08`. Assemble dry, no electronics.
5. Draw the schematic in KiCad from `generate_board.py`. Run ERC. **Expect it to
   find something.**
6. Route, fill, DRC, then fab.
7. Bench the firmware on the bare board with a current-limited supply and a
   servo you don't love, before it ever goes near the RedCat.

---

## Layout

```
mechanical/
  generate_parts.py          one coordinate frame, 19 assertions, 10 parts
  00-ASSEMBLY.step           everything placed in the scope frame
  01..10-*.stl/.step         printable parts + verification coupons
firmware/
  redcat_flat_panel/redcat_flat_panel.ino
pcb/
  BOM_RevC.csv               generated from the board
  source/
    generate_board.py        placement, nets, zones, stitching
    verify_board.py          36 netlist/stackup assertions
    generate_bom.py
```

## License

Copyright (C) 2026 pulikantitarun

This project - the mechanical design files, firmware, PCB design, and documentation - is licensed under the **GNU Affero General Public License, version 3 or later (AGPL-3.0-or-later)**. See [LICENSE](LICENSE) for the full text.

You are free to use, study, share, and modify this work, including as forks. In return, the copyleft terms require that if you distribute a modified version - or run a modified version to offer a service over a network - you make your modified source available under this same license. Forks and derivatives must remain AGPL-3.0.

Note on scope: AGPL is a software license. It fits the firmware and the generator scripts cleanly; the mechanical CAD/STL and PCB design files are released under it here as copyrightable design works. If you later want a copyleft written specifically for physical hardware, CERN-OHL-S is the usual companion, but AGPL across the whole repository is a common, valid choice and satisfies the goal that forks stay open. This paragraph is not legal advice.
