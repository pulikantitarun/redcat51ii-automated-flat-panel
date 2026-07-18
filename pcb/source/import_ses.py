"""
Import a freerouting .ses back onto the Rev C board.

REV C GUARDS - the Rev B version has none of these
--------------------------------------------------
1. It REFUSES to place any track on In1.Cu or In2.Cu. Those are solid GND
   planes now; a track there slots the plane and reintroduces the return-path
   problem Rev C exists to fix.
2. It REFUSES to place GND tracks at all. GND is carried by the planes and the
   stitching vias. If freerouting emitted GND wiring, the DSN was exported
   wrong - fix that, do not import it.
3. It preserves the stitching vias already on the board.
4. Via drill is 0.4 mm, not Rev B's 0.35, to stay above the 0.3 mm minimum with
   margin and off every fab's surcharge list.

After this, you STILL have to:
  - open the board in pcbnew and press B to fill the zones (KiCad plots gerbers
    from the stored fill - unfilled zones produce planeless gerbers);
  - widen the +12V and +6V paths by hand (the 6 V rail carries up to 2.7 A;
    ~3 mm on 1 oz copper is ~3 A);
  - run DRC;
  - and, ideally, have drawn a schematic and run ERC long before any of this.
"""

from pathlib import Path
import sys
import pcbnew

HERE = Path(__file__).resolve().parent
for cand in (HERE.parents[1] / "python_deps", HERE.parents[2] / "python_deps"):
    if cand.is_dir():
        sys.path.insert(0, str(cand))
from sexpdata import loads, Symbol  # noqa: E402

SOURCE = HERE / "redcat51ii-flat-panel-controller-revc.kicad_pcb"
SES = HERE / "redcat51ii-flat-panel-controller-revc.ses"
TARGET = HERE / "redcat51ii-flat-panel-controller-revc-routed.kicad_pcb"

if not SES.exists():
    raise SystemExit(f"No {SES.name} - route the .dsn in freerouting first.")

board = pcbnew.LoadBoard(str(SOURCE))


def atom(x):
    return x.value() if isinstance(x, Symbol) else str(x)


def find(node, name):
    if isinstance(node, list) and node and atom(node[0]) == name:
        return node
    if isinstance(node, list):
        for child in node:
            got = find(child, name)
            if got is not None:
                return got
    return None


tree = loads(SES.read_text(encoding="utf-8"))
network = find(tree, "network_out")
if network is None:
    raise SystemExit("No network_out in the .ses")

nlookup = {n.GetNetname(): n for n in board.GetNetInfo().NetsByNetcode().values()}
LAYERS = {"F.Cu": pcbnew.F_Cu, "B.Cu": pcbnew.B_Cu,
          "In1.Cu": pcbnew.In1_Cu, "In2.Cu": pcbnew.In2_Cu}
PLANE_LAYERS = {pcbnew.In1_Cu, pcbnew.In2_Cu}
SCALE = 10000.0

added = vias = 0
rejected_plane = rejected_gnd = 0

for nf in network[1:]:
    if not isinstance(nf, list) or not nf or atom(nf[0]) != "net":
        continue
    netname = atom(nf[1])
    net = nlookup.get(netname)
    if net is None:
        continue
    if netname == "GND":
        rejected_gnd += sum(1 for r in nf[2:] if isinstance(r, list) and r)
        continue                                   # GND lives on the planes
    for route in nf[2:]:
        if not isinstance(route, list) or not route:
            continue
        if atom(route[0]) == "wire":
            path = route[1]
            layer = LAYERS.get(atom(path[1]), pcbnew.F_Cu)
            if layer in PLANE_LAYERS:
                rejected_plane += 1
                continue                           # never slot a plane
            width = float(path[2]) / SCALE
            c = [float(z) for z in path[3:]]
            pts = [(c[i] / SCALE, -c[i + 1] / SCALE) for i in range(0, len(c), 2)]
            for a, b in zip(pts, pts[1:]):
                t = pcbnew.PCB_TRACK(board)
                t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(a[0]), pcbnew.FromMM(a[1])))
                t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(b[0]), pcbnew.FromMM(b[1])))
                t.SetWidth(pcbnew.FromMM(width))
                t.SetLayer(layer)
                t.SetNet(net)
                board.Add(t)
                added += 1
        elif atom(route[0]) == "via":
            x = float(route[2]) / SCALE
            y = -float(route[3]) / SCALE
            q = pcbnew.PCB_VIA(board)
            q.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
            q.SetWidth(pcbnew.FromMM(0.80))
            q.SetDrill(pcbnew.FromMM(0.40))        # Rev B used 0.35
            q.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            q.SetNet(net)
            board.Add(q)
            vias += 1

pcbnew.SaveBoard(str(TARGET), board)
print(f"added {added} segments, {vias} vias -> {TARGET.name}")
if rejected_plane:
    print(f"REJECTED {rejected_plane} wires that targeted In1/In2 (plane layers)")
if rejected_gnd:
    print(f"REJECTED {rejected_gnd} GND routes (GND is on the planes)")
print("\nNow: open in pcbnew, press B to fill zones, widen +12V/+6V, run DRC.")
