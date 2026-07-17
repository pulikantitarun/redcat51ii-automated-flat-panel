from pathlib import Path
import os
import pcbnew

HERE = Path(__file__).resolve().parent
KICAD_FP = Path(r"C:\Users\tarun\AppData\Local\Programs\KiCad\10.0\share\kicad\footprints")
MM = pcbnew.FromMM

board = pcbnew.BOARD()
board.SetCopperLayerCount(4)
ds = board.GetDesignSettings()
ds.m_TrackMinWidth = MM(0.20)
ds.m_MinClearance = MM(0.20)
ds.m_MinThroughDrill = MM(0.20)
ds.m_CopperEdgeClearance = MM(0.20)
ds.m_HoleClearance = MM(0.15)

def v(x, y): return pcbnew.VECTOR2I(MM(x), MM(y))

net_names = [
    "GND", "+12V_RAW", "+12V_FUSED", "+12V", "+6V", "+3V3", "USB_VBUS",
    "USB_D+_J", "USB_D-_J", "USB_D+", "USB_D-", "CC1", "CC2", "EN", "BOOT",
    "ASIAIR+", "ASIAIR-", "ASIAIR_LED", "ASIAIR_SIG", "LED_PWM", "LED_GATE", "LED_NEG",
    "SERVO_SIG", "OPEN_SIG", "CLOSED_SIG", "BUTTON_SIG", "STATUS_LED", "STATUS_A", "PWR_LED",
    "SW6", "BST6", "FB6", "EN6", "SW3", "BST3"
]
nets = {}
for name in net_names:
    n = pcbnew.NETINFO_ITEM(board, name); board.Add(n); nets[name] = n

default = board.GetAllNetClasses()["Default"]
default.SetClearance(MM(0.20)); default.SetTrackWidth(MM(0.25)); default.SetViaDiameter(MM(0.70)); default.SetViaDrill(MM(0.35))
net_settings=board.GetDesignSettings().m_NetSettings
power12=pcbnew.NETCLASS("Power12"); power12.SetClearance(MM(0.20)); power12.SetTrackWidth(MM(0.80)); power12.SetViaDiameter(MM(1.2)); power12.SetViaDrill(MM(0.55))
servo6=pcbnew.NETCLASS("Servo6"); servo6.SetClearance(MM(0.20)); servo6.SetTrackWidth(MM(0.80)); servo6.SetViaDiameter(MM(1.2)); servo6.SetViaDrill(MM(0.55))
logicp=pcbnew.NETCLASS("LogicPower"); logicp.SetClearance(MM(0.20)); logicp.SetTrackWidth(MM(0.50)); logicp.SetViaDiameter(MM(0.90)); logicp.SetViaDrill(MM(0.40))
net_settings.SetNetclass("Power12",power12); net_settings.SetNetclass("Servo6",servo6); net_settings.SetNetclass("LogicPower",logicp)
for name in ["+12V_RAW","+12V_FUSED","+12V"]: net_settings.SetNetclassPatternAssignment(name,"Power12")
for name in ["+6V","SW6"]: net_settings.SetNetclassPatternAssignment(name,"Servo6")
for name in ["GND","+3V3","SW3"]: net_settings.SetNetclassPatternAssignment(name,"LogicPower")
net_settings.RecomputeEffectiveNetclasses()

def line(parent, x1, y1, x2, y2, layer, width=0.15):
    s=pcbnew.PCB_SHAPE(parent); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetStart(v(x1,y1)); s.SetEnd(v(x2,y2)); s.SetLayer(layer); s.SetWidth(MM(width)); parent.Add(s)

for a,b in [((3,0),(117,0)),((117,0),(120,3)),((120,3),(120,72)),((120,72),(117,75)),((117,75),(3,75)),((3,75),(0,72)),((0,72),(0,3)),((0,3),(3,0))]: line(board,*a,*b,pcbnew.Edge_Cuts,0.1)

def load(lib, name, ref, value, x, y, angle=0):
    fp=pcbnew.FootprintLoad(str(KICAD_FP/f"{lib}.pretty"), name)
    if fp is None: raise RuntimeError(f"Missing footprint {lib}:{name}")
    fp.SetReference(ref); fp.SetValue(value); fp.SetPosition(v(x,y)); fp.SetOrientationDegrees(angle)
    fp.Reference().SetVisible(True); fp.Value().SetVisible(False); board.Add(fp); return fp

def setnets(fp, mapping):
    for p in fp.Pads():
        if p.GetNumber() in mapping: p.SetNet(nets[mapping[p.GetNumber()]])

def smd2(ref, value, net1, net2, x, y, kind="R", size="0603", angle=0):
    lib="Resistor_SMD" if kind=="R" else ("Capacitor_SMD" if kind=="C" else "Inductor_SMD")
    if kind=="R": name=f"R_{size}_1608Metric" if size=="0603" else f"R_{size}_2012Metric"
    elif kind=="C": name=f"C_{size}_1608Metric" if size=="0603" else (f"C_{size}_2012Metric" if size=="0805" else f"C_{size}_3225Metric")
    else: name="L_6.3x6.3_H3" if size=="6.3" else "L_4.0x4.0_H2.0"
    fp=load(lib,name,ref,value,x,y,angle); setnets(fp,{"1":net1,"2":net2}); return fp

def jst(ref, value, n1, n2, x, y, angle=0):
    fp=load("Connector_JST","JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical",ref,value,x,y,angle); setnets(fp,{"1":n1,"2":n2}); return fp

def via(net,x,y):
    q=pcbnew.PCB_VIA(board); q.SetPosition(v(x,y)); q.SetNet(nets[net]); q.SetWidth(MM(0.9)); q.SetDrill(MM(0.45)); q.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu); board.Add(q)

def track(net, pts, width=0.25, layer=pcbnew.F_Cu):
    for a,b in zip(pts,pts[1:]):
        t=pcbnew.PCB_TRACK(board); t.SetStart(v(*a)); t.SetEnd(v(*b)); t.SetWidth(MM(width)); t.SetLayer(layer); t.SetNet(nets[net]); board.Add(t)

# Mounting holes: 112 x 67 mm rectangle, referenced by enclosure CAD.
for i,(x,y) in enumerate([(40,4),(116,4),(40,71),(116,71)],1): load("MountingHole", "MountingHole_3.2mm_M3", f"H{i}", "M3", x,y)

# ESP32-S3 module at the left edge, antenna end facing outside board. Pin mapping is Espressif WROOM-1.
u1=load("RF_Module","ESP32-S3-WROOM-1","U1","ESP32-S3-WROOM-1-N8R8",19,31,90)
setnets(u1,{"1":"GND","2":"+3V3","3":"EN","4":"ASIAIR_SIG","5":"LED_PWM","6":"OPEN_SIG","7":"CLOSED_SIG","8":"STATUS_LED","11":"SERVO_SIG","13":"USB_D-","14":"USB_D+","17":"BUTTON_SIG","27":"BOOT","40":"GND","41":"GND"})

# USB-C native programming, USB2 only. Board is powered from MAIN 12 V; VBUS is sense/ESD only.
j8=load("Connector_USB","USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal","J8","USB-C PROGRAM",16,69,180)
setnets(j8,{"A1":"GND","A4":"USB_VBUS","A5":"CC1","A6":"USB_D+_J","A7":"USB_D-_J","A9":"USB_VBUS","A12":"GND","B1":"GND","B4":"USB_VBUS","B5":"CC2","B6":"USB_D+_J","B7":"USB_D-_J","B9":"USB_VBUS","B12":"GND","SH":"GND"})
smd2("R1","5.1k","CC1","GND",9,65); smd2("R2","5.1k","CC2","GND",25,65)
smd2("R3","22R","USB_D+_J","USB_D+",21,61,angle=90); smd2("R4","22R","USB_D-_J","USB_D-",24,61,angle=90)
u2=load("Package_TO_SOT_SMD","SOT-23-6","U2","USBLC6-2SC6",17,57)
setnets(u2,{"1":"USB_D+_J","2":"GND","3":"USB_D-_J","4":"USB_D-","5":"USB_VBUS","6":"USB_D+"})

# Reset, boot and local manual controls.
smd2("R5","10k","+3V3","EN",30,49); smd2("C1","1uF","EN","GND",35,49,kind="C")
sw1=load("Button_Switch_SMD","SW_Push_1P1T_NO_E-Switch_TL3301NxxxxxG","SW1","RESET",30,55); setnets(sw1,{"1":"EN","2":"GND"})
smd2("R6","10k","+3V3","BOOT",42,49)
sw2=load("Button_Switch_SMD","SW_Push_1P1T_NO_E-Switch_TL3301NxxxxxG","SW2","BOOT",42,55); setnets(sw2,{"1":"BOOT","2":"GND"})
sw3=load("Button_Switch_SMD","SW_Push_1P1T_NO_E-Switch_TL3301NxxxxxG","SW3","MANUAL",54,55); setnets(sw3,{"1":"BUTTON_SIG","2":"GND"})

# Main and ASIAIR barrel jacks along top wall.
j1=load("Connector_BarrelJack","BarrelJack_CUI_PJ-102AH_Horizontal","J1","MAIN 12V DC5521",106,8,180); setnets(j1,{"1":"+12V_RAW","2":"GND","3":"GND"})
j2=load("Connector_BarrelJack","BarrelJack_CUI_PJ-102AH_Horizontal","J2","ASIAIR PWM DC5521",84,8,180); setnets(j2,{"1":"ASIAIR+","2":"ASIAIR-","3":"ASIAIR-"})
f1=load("Fuse","Fuse_1812_4532Metric","F1","3A 16V PTC",98,14); setnets(f1,{"1":"+12V_RAW","2":"+12V_FUSED"})
q1=load("Package_SO","SO-8_3.9x4.9mm_P1.27mm","Q1","AO4407A",90,15)
setnets(q1,{"1":"+12V","2":"+12V","3":"+12V","4":"GND","5":"+12V_FUSED","6":"+12V_FUSED","7":"+12V_FUSED","8":"+12V_FUSED"})
d1=load("Diode_SMD","D_SMB","D1","SMBJ18A",105,21,90); setnets(d1,{"1":"+12V","2":"GND"})
c2=load("Capacitor_SMD","CP_Elec_10x10.5","C2","470uF 25V",70,52); setnets(c2,{"1":"+12V","2":"GND"})

# 6.0 V / 4 A servo supply (forced PWM AP62401), with local high-current bulk.
u3=load("Package_TO_SOT_SMD","TSOT-23-6","U3","AP62401WU-7",75,20)
setnets(u3,{"1":"GND","2":"SW6","3":"+12V","4":"FB6","5":"EN6","6":"BST6"})
smd2("C3","100nF","BST6","SW6",70,17,kind="C")
smd2("C4","10uF 25V","+12V","GND",80,14,kind="C",size="0805")
smd2("R18","100k","+12V","EN6",82,20)
smd2("L1","3.3uH 6.5A","SW6","+6V",66,22,kind="L",size="6.3")
smd2("R7","64.9k 1%","+6V","FB6",72,27); smd2("R8","10k 1%","FB6","GND",78,27)
smd2("C5","22uF 10V","+6V","GND",62,30,kind="C",size="0805"); smd2("C6","22uF 10V","+6V","GND",68,30,kind="C",size="0805")
c7=load("Capacitor_SMD","CP_Elec_8x10.5","C7","470uF 10V",76,36); setnets(c7,{"1":"+6V","2":"GND"})

# 3.3 V / 2 A logic supply (fixed-output AP63203).
u4=load("Package_TO_SOT_SMD","TSOT-23-6","U4","AP63203WU-7",50,20)
setnets(u4,{"1":"GND","2":"SW3","3":"+12V","4":"+3V3","5":"+12V","6":"BST3"})
smd2("C8","100nF","BST3","SW3",45,17,kind="C"); smd2("C9","10uF 25V","+12V","GND",55,14,kind="C",size="0805")
smd2("L2","4.7uH 3A","SW3","+3V3",42,22,kind="L",size="6.3")
smd2("C10","22uF 10V","+3V3","GND",44,30,kind="C",size="0805"); smd2("C11","22uF 10V","+3V3","GND",50,30,kind="C",size="0805")
smd2("C12","10uF","+3V3","GND",35,30,kind="C",size="0805"); smd2("C13","100nF","+3V3","GND",35,35,kind="C")

# Optically isolated ASIAIR control input.
smd2("R9","2.2k","ASIAIR+","ASIAIR_LED",78,10)
u5=load("Package_DIP","SMDIP-4_W7.62mm","U5","LTV-817S",68,9); setnets(u5,{"1":"ASIAIR_LED","2":"ASIAIR-","3":"GND","4":"ASIAIR_SIG"})
d2=load("Diode_SMD","D_SOD-123","D2","1N4148W",59,9); setnets(d2,{"1":"ASIAIR_LED","2":"ASIAIR-"})
smd2("R10","10k","+3V3","ASIAIR_SIG",63,14)

# LED panel low-side driver and external locking connectors.
smd2("R11","100R","LED_PWM","LED_GATE",80,47); smd2("R12","10k","LED_GATE","GND",86,47)
q2=load("Package_TO_SOT_SMD","SOT-23","Q2","AO3400A",92,47); setnets(q2,{"1":"LED_GATE","2":"GND","3":"LED_NEG"})
j4=jst("J4","LED PANEL","+12V","LED_NEG",113,34,90)
j3=load("Connector_PinHeader_2.54mm","PinHeader_1x03_P2.54mm_Vertical","J3","SERVO 6V GND SIG",113,45,90); setnets(j3,{"1":"+6V","2":"GND","3":"SERVO_SIG"})
j5=jst("J5","OPEN LIMIT","OPEN_SIG","GND",113,53,90); j6=jst("J6","CLOSED LIMIT","CLOSED_SIG","GND",113,64,90); j7=jst("J7","EXT MANUAL","BUTTON_SIG","GND",101,68,180)
smd2("R13","10k","+3V3","OPEN_SIG",98,52); smd2("R14","10k","+3V3","CLOSED_SIG",98,57); smd2("R15","10k","+3V3","BUTTON_SIG",89,62)
smd2("R16","1k","STATUS_LED","STATUS_A",36,42)
led=load("LED_SMD","LED_0603_1608Metric","LED1","STATUS BLUE",42,42); setnets(led,{"1":"GND","2":"STATUS_A"})
smd2("R17","1k","+3V3","PWR_LED",96,30)
led2=load("LED_SMD","LED_0603_1608Metric","LED2","POWER GREEN",103,30); setnets(led2,{"1":"GND","2":"PWR_LED"})

# Short local same-net links that should not be sent through the general router.
track("GND",[(19.2,72.68),(20.32,72.105)],0.6,pcbnew.F_Cu)
track("GND",[(12.8,72.68),(11.68,72.105)],0.6,pcbnew.F_Cu)
track("GND",[(11.68,67.925),(20.32,67.925)],0.6,pcbnew.B_Cu)


# Routing is generated from the complete netlist below; the final release widens
# the high-current 12 V / 6 V paths after the autorouter completes them.

# Front silkscreen labels and safety notes.
for text,x,y,size in [("REDCAT 51 II FLAT PANEL - REV B",60,72,1.0),("MAIN 12V",106,10,0.8),("ASIAIR PWM",84,10,0.8),("USB PROGRAM",16,68,0.8),("SERVO",108,45,0.8),("LED",108,34,0.8),("OPEN",108,55,0.7),("CLOSED",108,63,0.7),("12V MAIN REQUIRED FOR USB PROGRAMMING",48,68,0.7)]:
    t=pcbnew.PCB_TEXT(board); t.SetText(text); t.SetPosition(v(x,y)); t.SetLayer(pcbnew.F_SilkS); t.SetTextSize(v(size,size)); t.SetTextThickness(MM(0.15)); board.Add(t)

pcbnew.SaveBoard(str(HERE/"redcat51ii-flat-panel-controller-revb.kicad_pcb"),board)
print(HERE/"redcat51ii-flat-panel-controller-revb.kicad_pcb")
