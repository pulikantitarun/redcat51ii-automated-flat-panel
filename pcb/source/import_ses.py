from pathlib import Path
import sys
import pcbnew

here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parents[1]/"python_deps"))
from sexpdata import loads, Symbol

source=here/"redcat51ii-flat-panel-controller-revb.kicad_pcb"
ses=here/"redcat51ii-flat-panel-controller-revb.ses"
target=here/"redcat51ii-flat-panel-controller-revb-routed.kicad_pcb"
board=pcbnew.LoadBoard(str(source))
def atom(x): return x.value() if isinstance(x,Symbol) else str(x)
def find(node,name):
    if isinstance(node,list) and node and atom(node[0])==name:return node
    if isinstance(node,list):
        for child in node:
            got=find(child,name)
            if got is not None:return got
tree=loads(ses.read_text(encoding="utf-8")); network=find(tree,"network_out")
nlookup={n.GetNetname():n for n in board.GetNetInfo().NetsByNetcode().values()}
layers={"F.Cu":pcbnew.F_Cu,"B.Cu":pcbnew.B_Cu,"In1.Cu":pcbnew.In1_Cu,"In2.Cu":pcbnew.In2_Cu}
scale=10000.0
for nf in network[1:]:
    if not isinstance(nf,list) or not nf or atom(nf[0])!="net":continue
    net=nlookup.get(atom(nf[1]));
    if net is None:continue
    for route in nf[2:]:
        if not isinstance(route,list) or not route:continue
        if atom(route[0])=="wire":
            path=route[1]; layer=layers.get(atom(path[1]),pcbnew.F_Cu); width=float(path[2])/scale
            c=[float(z) for z in path[3:]]; pts=[(c[i]/scale,-c[i+1]/scale) for i in range(0,len(c),2)]
            for a,b in zip(pts,pts[1:]):
                t=pcbnew.PCB_TRACK(board); t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(a[0]),pcbnew.FromMM(a[1]))); t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(b[0]),pcbnew.FromMM(b[1]))); t.SetWidth(pcbnew.FromMM(width)); t.SetLayer(layer); t.SetNet(net); board.Add(t)
        elif atom(route[0])=="via":
            x=float(route[2])/scale; y=-float(route[3])/scale
            q=pcbnew.PCB_VIA(board); q.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x),pcbnew.FromMM(y))); q.SetWidth(pcbnew.FromMM(0.70)); q.SetDrill(pcbnew.FromMM(0.35)); q.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu); q.SetNet(net); board.Add(q)
pcbnew.SaveBoard(str(target),board); print(target)
