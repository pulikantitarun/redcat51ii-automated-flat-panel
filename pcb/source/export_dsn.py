from pathlib import Path
import pcbnew

here=Path(__file__).resolve().parent
source=here/"redcat51ii-flat-panel-controller-revb.kicad_pcb"
dsn=here/"redcat51ii-flat-panel-controller-revb.dsn"
board=pcbnew.LoadBoard(str(source))
for item in list(board.GetTracks()): board.Remove(item)
if not pcbnew.ExportSpecctraDSN(board,str(dsn)): raise SystemExit("DSN export failed")
print(dsn)
