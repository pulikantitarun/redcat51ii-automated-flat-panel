# Verifying Rev C yourself

Rev B's problem was not that it was wrong. Everything is wrong at some point.
Rev B's problem was that nothing in it could tell you it was wrong — the
generators had no assertions, the parts were never assembled, and the one number
that *did* get reported ("0 DRC violations") was measuring something that had no
bearing on whether the design worked.

So: don't take Rev C's word for it either. Here is how to re-check every claim
in the README from scratch.

---

## 1. Mechanical clearances

```bash
cd mechanical && python3 generate_parts.py
```

Prints 19 assertions and returns a non-zero exit code if any fail. Requires
`cadquery`.

To confirm they're real rather than decorative, break one on purpose:

```python
# in generate_parts.py, temporarily:
PIVOT_R = 55.0          # was 72.0
```

Re-run. You should see the servo body clearance go negative and the run fail.
If it doesn't, the assertion isn't testing what it claims.

## 2. Mesh integrity

The Rev B enclosure base exported **five disconnected bodies** and nobody
noticed, because nothing looked. This is the check that would have caught it:

```bash
cd mechanical
python3 -c "
import trimesh, glob
for f in sorted(glob.glob('*.stl')):
    m = trimesh.load(f, force='mesh')
    print('%-42s tris=%-6d bodies=%-2d watertight=%s' % (
        f, len(m.faces), len(m.split(only_watertight=False)), m.is_watertight))
"
```

Every line must read `bodies=1 watertight=True`. Anything else is a part that
will slice into nonsense.

Expected:

```
01-diameter-fit-gauge.stl                  tris=984    bodies=1  watertight=True
02-scope-clamp.stl                         tris=27994  bodies=1  watertight=True
03-ds3218-servo-plate.stl                  tris=5152   bodies=1  watertight=True
04-flat-panel-tray.stl                     tris=5776   bodies=1  watertight=True
05-diffuser-retaining-ring.stl             tris=3040   bodies=1  watertight=True
06-electronics-enclosure-base.stl          tris=7944   bodies=1  watertight=True
07-electronics-enclosure-lid.stl           tris=5724   bodies=1  watertight=True
08-limit-switch-bracket-print-two.stl      tris=2068   bodies=1  watertight=True
09-servo-shaft-gauge.stl                   tris=2076   bodies=1  watertight=True
10-connector-wall-coupon.stl               tris=524    bodies=1  watertight=True
```

## 3. Assembly

Open `mechanical/00-ASSEMBLY.step` in any CAD viewer. It contains the clamp,
servo plate, tray, retaining ring, a servo envelope block and a dew-shield
cylinder — all placed in the shared scope frame.

Look for the thing the numbers can't tell you: does the closed panel sit on the
optical axis, and does the open panel get out of the light path? The assertions
check both, but eyes are better at "that looks wrong" than any assertion is.

## 4. PCB netlist

```bash
cd pcb/source
python3 generate_board.py
python3 verify_board.py
```

36 assertions. These are the ones that would have failed on Rev B while DRC
reported zero violations:

- `U2 pins 1 and 6 share a net` — Rev B shorted R3 out
- `U2 pins 3 and 4 share a net` — Rev B shorted R4 out
- `J3 pin 1 = GND` — Rev B had +6 V there
- `Q1 gate is not hard-tied to GND` — Rev B tied it
- `F.Cu / In1.Cu / In2.Cu / B.Cu has at least one copper zone` — Rev B had none, anywhere

Same trick as before — break one deliberately and confirm the check catches it:

```python
# in generate_board.py, temporarily:
setnets(j3, {"1": "+6V", "2": "GND", "3": "SERVO_SIG"})   # the Rev B pinout
```

`verify_board.py` must fail on `J3 pin 1 = GND`.

## 5. The gerber check Rev B needed

After routing and filling, before you upload anything, count the fill records:

```bash
cd <gerber dir>
for f in *.gbr *.g?? ; do
  printf '%-40s G36 fills: %s\n' "$f" "$(grep -c '^G36' "$f" 2>/dev/null)"
done
```

The two inner layers must show a healthy non-zero count. Rev B's showed **zero
on every single layer** — that one command, run once, would have caught the
entire copper problem before it reached a fab queue.

---

## What none of this proves

- **That the circuit is correct.** There is no schematic and no ERC. Every
  assertion in `verify_board.py` is a thing I thought to check. The bug that
  gets you is the one nobody thought to check — which is the entire argument for
  drawing the schematic and letting ERC look at it with fresh eyes.
- **That the firmware runs.** It has never been compiled.
- **That the four measured parameters are right.** Only a caliper proves that.
- **That the ASIAIR port is high-side switched.** Only a multimeter proves that.

The point of Rev C isn't that it's right. It's that when it's wrong, something
says so.
