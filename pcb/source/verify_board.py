"""
Rev C board assertions.

Rev B shipped with "0 DRC violations" and was still wrong, because DRC only
proves that the copper matches the netlist you typed. It cannot tell you the
netlist itself is nonsense. Every one of the checks below would have FAILED on
Rev B while DRC stayed green:

  - USBLC6 pins 1/6 and 3/4 are internally common; Rev B straddled the 22R
    series resistors across them, shorting both out.
  - J3 put +6 V on the servo lead's ground wire.
  - Q1's gate was hard-tied to GND, so Vgs = the full rail.
  - There was not one copper zone on a 4-layer board with two switchers.

This is not a substitute for a schematic and ERC. It is the minimum bar for
noticing that the netlist is wrong before a fab does it for you.

Run:  python3 verify_board.py [board.kicad_pcb]
"""

import sys
from pathlib import Path
from collections import defaultdict

import pcbnew

HERE = Path(__file__).resolve().parent
path = Path(sys.argv[1]) if len(sys.argv) > 1 else \
    HERE / "redcat51ii-flat-panel-controller-revc.kicad_pcb"

board = pcbnew.LoadBoard(str(path))
print(f"verifying {path.name}  (KiCad {pcbnew.Version()})\n")

fails = []
warns = []


def chk(cond, name, detail=""):
    if cond:
        print(f"  [PASS] {name}")
    else:
        print(f"  [FAIL] {name}   {detail}")
        fails.append(name)


def warn(cond, name, detail=""):
    if not cond:
        print(f"  [WARN] {name}   {detail}")
        warns.append(name)


# --------------------------------------------------------------------------
fps = {fp.GetReference(): fp for fp in board.GetFootprints()}


def padnet(ref, pad):
    fp = fps.get(ref)
    if fp is None:
        return None
    for p in fp.Pads():
        if p.GetNumber() == pad:
            return p.GetNetname()
    return None


print("Netlist assertions:")

# 1. USBLC6-2SC6 - pins 1+6 are one internal node, 3+4 are another.
n1, n6 = padnet("U2", "1"), padnet("U2", "6")
n3, n4 = padnet("U2", "3"), padnet("U2", "4")
chk(n1 == n6 and n1 is not None,
    "U2 pins 1 and 6 share a net (they are internally common)", f"{n1} vs {n6}")
chk(n3 == n4 and n3 is not None,
    "U2 pins 3 and 4 share a net (they are internally common)", f"{n3} vs {n4}")
chk(n1 != n3, "U2 I/O1 and I/O2 are different nets", f"{n1} vs {n3}")
# and the TVS must sit on the connector side of the series resistors
chk(padnet("R3", "1") == n1 and padnet("R3", "2") == "USB_D+",
    "R3 22R runs from the protected D+ node to the module", 
    f"{padnet('R3','1')} -> {padnet('R3','2')}")
chk(padnet("R4", "1") == n3 and padnet("R4", "2") == "USB_D-",
    "R4 22R runs from the protected D- node to the module",
    f"{padnet('R4','1')} -> {padnet('R4','2')}")

# 2. Servo header must be GND / V+ / SIG - the universal hobby servo order.
chk(padnet("J3", "1") == "GND", "J3 pin 1 = GND (brown)", padnet("J3", "1"))
chk(padnet("J3", "2") == "+6V", "J3 pin 2 = +6V (red)", padnet("J3", "2"))
chk(padnet("J3", "3") == "SERVO_SIG", "J3 pin 3 = signal (orange)", padnet("J3", "3"))

# 3. Q1 reverse-polarity FET gate must not be hard-tied to GND.
gate = padnet("Q1", "4")
chk(gate not in ("GND", None), "Q1 gate is not hard-tied to GND", str(gate))
chk("R21" in fps and "GND" in (padnet("R21", "1"), padnet("R21", "2")),
    "Q1 gate has a pulldown resistor (R21)")
chk("D3" in fps and padnet("D3", "1") == "+12V" and padnet("D3", "2") == gate,
    "Q1 gate has a Vgs clamp zener to source (D3)",
    f"{padnet('D3','1')}/{padnet('D3','2')}")

# 4. The opto is gone and the ADC front end is present.
netnames = {board.GetNetInfo().GetNetItem(i).GetNetname()
            for i in range(board.GetNetInfo().GetNetCount())}
chk("ASIAIR_LED" not in netnames, "opto-isolator net ASIAIR_LED removed")
chk("U5" not in fps, "opto-isolator U5 removed")
chk(padnet("R10", "1") == "ASIAIR+" and padnet("R10", "2") == "ASIAIR_SIG",
    "R10 is the divider top leg (ASIAIR+ -> ASIAIR_SIG)")
chk(padnet("R20", "1") == "ASIAIR_SIG" and padnet("R20", "2") == "GND",
    "R20 is the divider bottom leg (ASIAIR_SIG -> GND)")
chk(padnet("C14", "1") == "ASIAIR_SIG", "C14 filters the ADC node")
chk(padnet("D2", "1") == "ASIAIR_SIG" and padnet("D2", "2") == "GND",
    "D2 clamps the ADC node (cathode to signal)")
chk("R9" in fps, "R9 port bleeder present")
# the bleeder has to be a real power part - 12V across 470R is 306 mW
if "R9" in fps:
    fpid = fps["R9"].GetFPIDAsString()
    chk("2512" in fpid, "R9 is a 2512 (306 mW needs >0.25 W)", fpid)
chk(padnet("R19", "1") == "ASIAIR-" and padnet("R19", "2") == "GND",
    "R19 bonds ASIAIR- to board GND")

# 5. Nothing should still reference the deleted parts.
for ref in ("U5",):
    chk(ref not in fps, f"{ref} is absent")

# --------------------------------------------------------------------------
print("\nCopper / stackup assertions:")

chk(board.GetCopperLayerCount() == 4, "4 copper layers",
    str(board.GetCopperLayerCount()))

zones_by_layer = defaultdict(list)
for z in board.Zones():
    for lid in z.GetLayerSet().CuStack():
        zones_by_layer[lid].append(z)

for lid, nm in ((pcbnew.F_Cu, "F.Cu"), (pcbnew.In1_Cu, "In1.Cu"),
                (pcbnew.In2_Cu, "In2.Cu"), (pcbnew.B_Cu, "B.Cu")):
    zs = zones_by_layer.get(lid, [])
    chk(len(zs) > 0, f"{nm} has at least one copper zone (Rev B had none anywhere)")
    if zs:
        chk(any(z.GetNetname() == "GND" for z in zs), f"{nm} zone is on GND")

# Inner layers must be GND and nothing else - a stray signal on In1/In2 would
# slot a plane and undo the whole point.
for lid, nm in ((pcbnew.In1_Cu, "In1.Cu"), (pcbnew.In2_Cu, "In2.Cu")):
    tracks_on = [t for t in board.GetTracks()
                 if t.GetClass() == "PCB_TRACK" and t.GetLayer() == lid]
    chk(len(tracks_on) == 0,
        f"{nm} carries no signal tracks (it is a solid plane)", f"{len(tracks_on)} tracks")

# --------------------------------------------------------------------------
print("\nManufacturing assertions:")

drills = sorted({t.GetDrillValue() for t in board.GetTracks()
                 if t.GetClass() == "PCB_VIA"})
if drills:
    smallest = min(drills) / 1e6
    chk(smallest >= 0.29, f"smallest via drill >= 0.3 mm (fabs surcharge below)",
        f"{smallest:.3f} mm")

vias = [t for t in board.GetTracks() if t.GetClass() == "PCB_VIA"]
chk(len(vias) >= 50, f"GND stitching vias present ({len(vias)})",
    "planes without stitching are decorative")
chk(all(vv.GetNetname() == "GND" for vv in vias),
    "every stitching via is on GND")

# stitching vias must not sit inside a pad
collisions = []
for vv in vias:
    vp = vv.GetPosition()
    r = vv.GetWidth() / 2 + pcbnew.FromMM(0.2)
    for fp in board.GetFootprints():
        for p in fp.Pads():
            bb = p.GetBoundingBox()
            if (bb.GetLeft() - r < vp.x < bb.GetRight() + r and
                    bb.GetTop() - r < vp.y < bb.GetBottom() + r):
                collisions.append((fp.GetReference(), p.GetNumber()))
chk(not collisions, "no stitching via lands on a pad",
    f"{len(collisions)} collisions: {collisions[:5]}")

# --------------------------------------------------------------------------
print("\nRouting status (informational - this script does not route):")
board.BuildConnectivity()
conn = board.GetConnectivity()
unrouted = conn.GetUnconnectedCount(True) if hasattr(conn, "GetUnconnectedCount") else -1
print(f"  unconnected ratsnest lines: {unrouted}")
print("  -> non-zero is EXPECTED here: signals are routed by the freerouting")
print("     step, and GND is carried by the planes, not the ratsnest.")

# --------------------------------------------------------------------------
print()
if fails:
    print(f"*** {len(fails)} ASSERTION(S) FAILED ***")
    for f in fails:
        print(f"    - {f}")
    sys.exit(1)
print(f"All netlist/stackup assertions PASS ({len(warns)} warnings)")
print("\nReminder: this proves the netlist is self-consistent, NOT that the")
print("circuit is right. There is still no schematic and therefore no ERC.")
sys.exit(0)
