# Installation on the RedCat 51 II

## Orientation

Viewed from the front of the telescope, place the split clamp immediately behind the front lip of the dew shield. Put the servo platform on the left side (about the 9 o'clock position). The flat-panel tray swings sideways, away from the optical opening; it must never swing down onto the glass.

```text
FRONT VIEW                              SIDE VIEW

       panel open                             panel closed
           O------ arm                           [diffuser]
          /                                         ||
   servo @ 9 o'clock                         ===== dew shield =====
       [ clamp ]                              [clamp][servo]
      ( RedCat )                                   cable -> enclosure
```

## Build order

1. Print only `01-diameter-fit-gauge.stl`. Add the 0.8 mm liner. It should slide over the dew shield without force and without rocking.
2. If the fit is wrong, measure the shield with calipers and edit `SCOPE_DIAMETER` in `mechanical/generate_parts.py`; regenerate before printing the clamp.
3. Install M3 heat-set inserts in the clamp platform and panel tray. Keep the iron away from the scope.
4. Fit the DS3218 into the servo plate with its output shaft toward the optical axis. Bolt the plate to the clamp platform.
5. Build the optical stack in the tray: white reflector, engraved light guide, edge LED, diffusion film, opal diffuser, retaining ring.
6. With power disconnected, set the servo horn at the midpoint. Attach the tray arm loosely through its adjustment slots.
7. Install two KW12-3 brackets so one switch trips at fully open and the other at fully closed. Wire only COM and NO.
8. Bolt the integrated PCB into the enclosure on the four printed standoffs. The two barrel jacks face the paired round openings, USB-C faces the rectangular service opening, and J3-J7 face the wide harness opening.
9. Mount the enclosure to the telescope dovetail or tripod leg with hook-and-loop strap. Do not mount its mass on the dew shield or allow cables to tug the flap.
10. Route one servo lead and the LED/limit harness along the clamp, leaving a gentle loop at the moving arm. Add strain relief before the enclosure.

## First motion test

Remove the optical tray from the horn. Power J1 from a current-limited 12 V supply set initially to 1 A. Confirm 3.3 V and 6.0 V rails, flash firmware, then connect the unloaded servo. Confirm open/closed direction and switches. Increase the current limit to 4 A only after the mechanism moves freely. Attach the tray last and adjust the horn slots so the closed diffuser is centred without servo stall.

Keep at least 3 mm clearance between the closed diffuser and the dew-shield rim. Confirm the open tray clears the focuser, mount, cables and ground through the mount's full range before unattended imaging.
