# Universal installation

## 1. Measure and generate

Measure the exact outside diameter of the mounting surface with calipers. Do not use a
catalogue diameter. Generate the parts with `mechanical/generate_parts.py`, or use the
OpenSCAD Customizer source. Print the fit gauge first with the intended EVA/cork liner.
The lined gauge must slide on without force and must not rock.

The supplied RedCat 51 II preset uses an 80.0 mm measured OD. Other scopes only need a
new fit gauge and clamp; the PCB, enclosure, servo plate, switch brackets, and firmware
are unchanged. Increase panel diameter and arm reach if the optical aperture is larger.

## 2. Assemble off the telescope

1. Install heat-set inserts in the cold printed parts, away from the telescope.
2. Fit the DS3218 to the servo plate with its output shaft toward the optical axis.
3. Build the tray stack: white reflector, light guide, edge LED, diffusion film, opal
   diffuser, and retaining ring.
4. Wire both KW12-3 switches using **COM and NC**, not NO.
5. Fit the moving tray loosely to the 25T metal horn.
6. Join the printed tether eye on the clamp to the eye on the tray with 3-4 mm cord.
7. Fit the PCB to the four enclosure standoffs. Route LED, servo, and control harnesses
   through their separate exits and zip-tie them to the internal strain-relief posts.
8. Add the optional foam lid gasket. Do not seal the enclosure airtight; trapped moisture
   needs a path to dry.

## 3. Bench setup

Remove the tray from the horn for the first powered test. Connect USB-C, flash firmware,
and verify serial `STATUS`. Wire the keyed J3 harness as 6 V / GND / signal. Apply MAIN
12 V from a current-limited bench supply and follow `FIRST_ARTICLE_TEST.md`.

Adjust the two switch brackets so the target switch opens slightly before the printed
hard-stop tab contacts the bracket. The hard stop is backup protection, not the normal
servo endpoint. Set angles over USB, test at least 20 open/close cycles unloaded, then
attach and centre the tray.

## 4. Fit to the telescope

Viewed from the front, place the split clamp immediately behind the dew-shield lip. Put
the servo platform at roughly 9 o'clock so the panel swings sideways, away from the glass.

```text
FRONT VIEW                         SIDE VIEW — CLOSED

      panel open O---- arm              [diffuser]
                 \                           3 mm minimum gap
          servo @ 9 o'clock             ===== dew shield =====
              ( scope )                 [clamp][servo]
```

Tighten the M4 clamp only enough to prevent rotation; the liner supplies grip. Mount the
electronics enclosure on a dovetail or tripod leg, not on the dew shield. Leave a gentle
service loop at the moving arm and make drip loops below both barrel jacks.

Verify at least 3 mm clearance between the closed diffuser and dew-shield rim. Move the
mount through every expected altitude, meridian-flip, and parking position. Confirm the
open panel, tether, enclosure, and cable loops cannot hit the mount, tripod, focuser, or
ground before unattended imaging.
