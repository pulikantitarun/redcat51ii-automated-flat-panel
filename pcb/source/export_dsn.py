"""
Export the Rev C board to Specctra DSN for freerouting.

REV C DIFFERENCES - READ THESE, THE REV B VERSION WILL DESTROY THE FIX
---------------------------------------------------------------------
Rev B's export_dsn.py opened with:

    for item in list(board.GetTracks()): board.Remove(item)

GetTracks() returns vias as well as track segments. On Rev B that was harmless,
because Rev B had no vias worth keeping. On Rev C it would silently delete all
124 GND stitching vias, and the planes would go back to being decorative - the
exact defect Rev C exists to fix, quietly reintroduced by a line of
housekeeping.

This version removes only routed SEGMENTS and keeps the stitching vias, so
freerouting sees them as existing GND connections rather than routing over them.
"""

from pathlib import Path
import pcbnew

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "redcat51ii-flat-panel-controller-revc.kicad_pcb"
DSN = HERE / "redcat51ii-flat-panel-controller-revc.dsn"

board = pcbnew.LoadBoard(str(SOURCE))

removed = kept = 0
for item in list(board.GetTracks()):
    if item.GetClass() == "PCB_VIA":
        kept += 1                      # <-- the line Rev B did not have
        continue
    board.Remove(item)
    removed += 1

# The inner layers are solid GND planes. If anything is sitting on them at this
# point the board is already broken, and routing on top of it will only bury the
# evidence.
for lid, nm in ((pcbnew.In1_Cu, "In1.Cu"), (pcbnew.In2_Cu, "In2.Cu")):
    stray = [t for t in board.GetTracks()
             if t.GetClass() == "PCB_TRACK" and t.GetLayer() == lid]
    if stray:
        raise SystemExit(f"{nm} has {len(stray)} track segments on it - "
                         f"that layer is supposed to be a solid plane.")

if not pcbnew.ExportSpecctraDSN(board, str(DSN)):
    raise SystemExit("DSN export failed")

print(f"removed {removed} track segments, kept {kept} stitching vias")
print(DSN)
print()
print("Next: route in freerouting, save the .ses, then run import_ses.py.")
print("GND is on the planes. If freerouting routes GND as tracks anyway,")
print("import_ses.py will refuse them - do not 'fix' that by letting them in.")
