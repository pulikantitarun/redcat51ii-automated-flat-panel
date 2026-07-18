"""BOM generated FROM the board file, so it cannot drift out of sync with it.
Rev B's BOM was maintained by hand alongside the generator."""
import csv, sys
from collections import defaultdict
from pathlib import Path
import pcbnew

HERE = Path(__file__).resolve().parent
board = pcbnew.LoadBoard(str(HERE / "redcat51ii-flat-panel-controller-revc.kicad_pcb"))

groups = defaultdict(list)
for fp in board.GetFootprints():
    ref = fp.GetReference()
    if ref.startswith("H"):
        continue  # mounting holes are not parts
    groups[(fp.GetValue(), fp.GetFPIDAsString())].append(ref)

def sortkey(r):
    import re
    m = re.match(r"([A-Z]+)(\d+)", r)
    return (m.group(1), int(m.group(2))) if m else (r, 0)

rows = []
for (value, fpid), refs in groups.items():
    refs.sort(key=sortkey)
    rows.append({
        "Comment": value,
        "Designator": ",".join(refs),
        "Footprint": fpid.split(":")[-1],
        "Quantity": len(refs),
    })
rows.sort(key=lambda r: sortkey(r["Designator"].split(",")[0]))

out = HERE.parent / "BOM_RevC.csv"
with open(out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["Comment", "Designator", "Footprint", "Quantity"])
    w.writeheader()
    w.writerows(rows)
print(f"{sum(r['Quantity'] for r in rows)} placements, {len(rows)} line items -> {out}")
for r in rows:
    print(f"  {r['Designator']:<12} {r['Comment']:<22} {r['Footprint']}")
