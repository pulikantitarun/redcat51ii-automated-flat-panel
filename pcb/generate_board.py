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
    "GND", "+12V_RAW", "+12V_FUSED", "+12V", "+12V_LED", "+6V", "+6V_FUSED", "+6V_SERVO", "+3V3", "LOGIC_VIN", "USB_VBUS",
    "USB_D+_J", "USB_D-_J", "USB_D+", "USB_D-", "CC1", "CC2", "EN", "BOOT",
    "ASIAIR+", "ASIAIR-", "ASIAIR_LED", "ASIAIR_SIG", "LED_PWM", "LED_GATE", "LED_NEG",
    "SERVO_SIG", "SERVO_PWR_EN", "SERVO_GATE", "SERVO_BASE", "OPEN_RAW", "OPEN_SIG", "CLOSED_RAW", "CLOSED_SIG", "BUTTON_RAW", "BUTTON_SIG", "PWR_SENSE", "UART_TX", "UART_RX", "STATUS_LED", "STATUS_A", "PWR_LED",
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
for name in ["+12V_RAW","+12V_FUSED","+12V","+12V_LED"]: net_settings.SetNetclassPatternAssignment(name,"Power12")
for name in ["+6V","+6V_FUSED","+6V_SERVO","SW6"]: net_settings.SetNetclassPatternAssignment(name,"Servo6")
for name in ["GND","LOGIC_VIN","+3V3","SW3"]: net_settings.SetNetclassPatternAssignment(name,"LogicPower")
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

def testpad(ref, value, net, x, y):
    fp=load("TestPoint", "TestPoint_Pad_D1.0mm", ref, value, x, y)
    setnets(fp,{"1":net}); return fp

def via(net,x,y):
    q=pcbnew.PCB_VIA(board); q.SetPosition(v(x,y)); q.SetNet(nets[net]); q.SetWidth(MM(0.9)); q.SetDrill(MM(0.45)); q.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu); board.Add(q)

def track(net, pts, width=0.25, layer=pcbnew.F_Cu):
    for a,b in zip(pts,pts[1:]):
        t=pcbnew.PCB_TRACK(board); t.SetStart(v(*a)); t.SetEnd(v(*b)); t.SetWidth(MM(width)); t.SetLayer(layer); t.SetNet(nets[net]); board.Add(t)

# Mounting holes: 112 x 67 mm rectangle, referenced by enclosure CAD.
for i,(x,y) in enumerate([(40,4),(116,4),(40,71),(116,71)],1): load("MountingHole", "MountingHole_3.2mm_M3", f"H{i}", "M3", x,y)

# ESP32-S3 module at the left edge, antenna end facing outside board. Pin mapping is Espressif WROOM-1.
u1=load("RF_Module","ESP32-S3-WROOM-1","U1","ESP32-S3-WROOM-1-N8",19,31,90)
setnets(u1,{"1":"GND","2":"+3V3","3":"EN","4":"ASIAIR_SIG","5":"LED_PWM","6":"OPEN_SIG","7":"CLOSED_SIG","8":"STATUS_LED","11":"SERVO_SIG","12":"SERVO_PWR_EN","13":"USB_D-","14":"USB_D+","17":"BUTTON_SIG","18":"PWR_SENSE","27":"BOOT","36":"UART_RX","37":"UART_TX","40":"GND","41":"GND"})

# USB-C native programming, USB2 only. USB VBUS can power logic for safe bench flashing;
# LED and servo branches still require MAIN 12 V.
j8=load("Connector_USB","USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal","J8","USB-C PROGRAM",16,69,180)
setnets(j8,{"A1":"GND","A4":"USB_VBUS","A5":"CC1","A6":"USB_D+_J","A7":"USB_D-_J","A9":"USB_VBUS","A12":"GND","B1":"GND","B4":"USB_VBUS","B5":"CC2","B6":"USB_D+_J","B7":"USB_D-_J","B9":"USB_VBUS","B12":"GND","SH":"GND"})
smd2("R1","5.1k","CC1","GND",9,65); smd2("R2","5.1k","CC2","GND",25,65)
smd2("R3","22R","USB_D+_J","USB_D+",25,55,angle=90); smd2("R4","22R","USB_D-_J","USB_D-",18,55,angle=90)
u2=load("Package_TO_SOT_SMD","SOT-23-6","U2","USBLC6-2SC6",22,48,270)
setnets(u2,{"1":"USB_D+_J","2":"GND","3":"USB_D-_J","4":"USB_D-","5":"USB_VBUS","6":"USB_D+"})

# Reset, boot and local manual controls.
smd2("R5","10k","+3V3","EN",30,49); smd2("C1","1uF","EN","GND",35,49,kind="C")
sw1=load("Button_Switch_SMD","SW_Push_1P1T_NO_E-Switch_TL3301NxxxxxG","SW1","RESET",35,62); setnets(sw1,{"1":"EN","2":"GND"})
smd2("R6","10k","+3V3","BOOT",42,49)
sw2=load("Button_Switch_SMD","SW_Push_1P1T_NO_E-Switch_TL3301NxxxxxG","SW2","BOOT",42,55); setnets(sw2,{"1":"BOOT","2":"GND"})
sw3=load("Button_Switch_SMD","SW_Push_1P1T_NO_E-Switch_TL3301NxxxxxG","SW3","MANUAL",54,55); setnets(sw3,{"1":"BUTTON_SIG","2":"GND"})

# Main and ASIAIR barrel jacks along top wall.
j1=load("Connector_BarrelJack","BarrelJack_CUI_PJ-102AH_Horizontal","J1","MAIN 12V DC5521",106,8,180); setnets(j1,{"1":"+12V_RAW","2":"GND","3":"GND"})
j2=load("Connector_BarrelJack","BarrelJack_CUI_PJ-102AH_Horizontal","J2","ASIAIR PWM DC5521",84,8,180); setnets(j2,{"1":"ASIAIR+","2":"ASIAIR-","3":"ASIAIR-"})
f1=load("Fuse","Fuse_1812_4532Metric","F1","MF-MSMF200/16X 2A 16V PTC",98,14); setnets(f1,{"1":"+12V_RAW","2":"+12V_FUSED"})
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

# 3.3 V / 2 A logic supply (fixed-output AP63203). Schottky ORing permits
# USB-only firmware loading without energising the 12 V actuator branches.
d6=load("Diode_SMD","D_SMA","D6","SS14 12V LOGIC OR",57,18); setnets(d6,{"1":"LOGIC_VIN","2":"+12V"})
d7=load("Diode_SMD","D_SMA","D7","SS14 USB LOGIC OR",57,23); setnets(d7,{"1":"LOGIC_VIN","2":"USB_VBUS"})
u4=load("Package_TO_SOT_SMD","TSOT-23-6","U4","AP63203WU-7",50,20)
setnets(u4,{"1":"GND","2":"SW3","3":"LOGIC_VIN","4":"+3V3","5":"LOGIC_VIN","6":"BST3"})
smd2("C8","100nF","BST3","SW3",45,17,kind="C"); smd2("C9","10uF 25V","LOGIC_VIN","GND",54,27,kind="C",size="0805")
smd2("L2","4.7uH 3A","SW3","+3V3",42,22,kind="L",size="6.3")
smd2("C10","22uF 10V","+3V3","GND",44,30,kind="C",size="0805"); smd2("C11","22uF 10V","+3V3","GND",50,30,kind="C",size="0805")
smd2("C12","10uF","+3V3","GND",35,30,kind="C",size="0805"); smd2("C13","100nF","+3V3","GND",35,35,kind="C")

# Main-supply sense. 100k/22k keeps a 16 V input below 2.9 V; firmware uses
# the calibrated ADC reading only as a presence/interlock signal.
smd2("R19","100k","+12V","PWR_SENSE",35,16)
smd2("R20","22k","PWR_SENSE","GND",35,21)
smd2("C14","100nF","PWR_SENSE","GND",35,25,kind="C")

# Optically isolated ASIAIR control input.
smd2("R9","2.2k","ASIAIR+","ASIAIR_LED",78,10)
u5=load("Package_DIP","SMDIP-4_W7.62mm","U5","LTV-817S",68,9); setnets(u5,{"1":"ASIAIR_LED","2":"ASIAIR-","3":"GND","4":"ASIAIR_SIG"})
d2=load("Diode_SMD","D_SOD-123","D2","1N4148W",59,9); setnets(d2,{"1":"ASIAIR_LED","2":"ASIAIR-"})
smd2("R10","10k","+3V3","ASIAIR_SIG",63,14)

# LED panel low-side driver with independent branch protection.
smd2("R11","100R","LED_PWM","LED_GATE",80,47); smd2("R12","10k","LED_GATE","GND",86,47)
q2=load("Package_TO_SOT_SMD","SOT-23","Q2","AO3400A",92,47); setnets(q2,{"1":"LED_GATE","2":"GND","3":"LED_NEG"})
f2=load("Fuse","Fuse_1812_4532Metric","F2","MF-MSMF110/16X LED 1.1A",115,24); setnets(f2,{"1":"+12V","2":"+12V_LED"})
j4=jst("J4","LED PANEL","+12V_LED","LED_NEG",113,32,90)

# Servo branch: resettable fuse plus MCU-controlled high-side switch. The
# default-off gate network removes servo power after every move or fault.
f3=load("Fuse","Fuse_1812_4532Metric","F3","MF-MSMF260/8X SERVO 2.6A",104,41,90); setnets(f3,{"1":"+6V","2":"+6V_FUSED"})
q3=load("Package_SO","SO-8_3.9x4.9mm_P1.27mm","Q3","AO4407A SERVO SWITCH",95,39)
setnets(q3,{"1":"+6V_FUSED","2":"+6V_FUSED","3":"+6V_FUSED","4":"SERVO_GATE","5":"+6V_SERVO","6":"+6V_SERVO","7":"+6V_SERVO","8":"+6V_SERVO"})
q4=load("Package_TO_SOT_SMD","SOT-23","Q4","MMBT3904",86,38); setnets(q4,{"1":"SERVO_BASE","2":"GND","3":"SERVO_GATE"})
smd2("R21","4.7k","SERVO_PWR_EN","SERVO_BASE",82,31)
smd2("R22","100k","SERVO_BASE","GND",84,33)
smd2("R23","100k","+6V_FUSED","SERVO_GATE",88,31)
j3=load("Connector_JST","JST_XH_B3B-XH-A_1x03_P2.50mm_Vertical","J3","KEYED SERVO 6V GND SIG",113,44,90); setnets(j3,{"1":"+6V_SERVO","2":"GND","3":"SERVO_SIG"})

# Fail-safe NC limit wiring. During travel both switch circuits are closed to
# ground; an endpoint or broken wire reads HIGH. Each cable gets RC filtering
# and a low-capacitance ESD clamp at the connector.
j5=jst("J5","OPEN LIMIT NC","OPEN_RAW","GND",113,54,90); j6=jst("J6","CLOSED LIMIT NC","CLOSED_RAW","GND",113,64,90); j7=jst("J7","EXT MANUAL","BUTTON_RAW","GND",101,68,180)
smd2("R13","10k","+3V3","OPEN_SIG",96,50); smd2("R14","10k","+3V3","CLOSED_SIG",96,57); smd2("R15","10k","+3V3","BUTTON_SIG",88,62)
smd2("R24","1k","OPEN_RAW","OPEN_SIG",102,52); smd2("R25","1k","CLOSED_RAW","CLOSED_SIG",102,59); smd2("R26","1k","BUTTON_RAW","BUTTON_SIG",94,65)
smd2("C15","100nF","OPEN_SIG","GND",96,53,kind="C"); smd2("C16","100nF","CLOSED_SIG","GND",96,60,kind="C"); smd2("C17","100nF","BUTTON_SIG","GND",88,65,kind="C")
for ref,raw,x,y in [("D3","OPEN_RAW",107,51),("D4","CLOSED_RAW",107,61),("D5","BUTTON_RAW",95,63)]:
    d=load("Diode_SMD","D_SOD-923",ref,"ESD9B3.3ST5G",x,y); setnets(d,{"1":raw,"2":"GND"})

# Service pads and a compact UART/recovery header for first-article test.
for ref,value,net,x in [("TP1","12V","+12V",48),("TP2","6V","+6V",52),("TP3","6V_SW","+6V_SERVO",56),("TP4","3V3","+3V3",60),("TP5","GND","GND",64),("TP6","ASIAIR","ASIAIR_SIG",68),("TP7","LED_GATE","LED_GATE",72),("TP8","SERVO_SIG","SERVO_SIG",76)]:
    testpad(ref,value,net,x,43)
j9=load("Connector_PinHeader_2.54mm","PinHeader_2x03_P2.54mm_Vertical","J9","UART RECOVERY",70,65)
setnets(j9,{"1":"+3V3","2":"GND","3":"UART_TX","4":"UART_RX","5":"EN","6":"BOOT"})
smd2("R16","1k","STATUS_LED","STATUS_A",36,42)
led=load("LED_SMD","LED_0603_1608Metric","LED1","STATUS BLUE",42,42); setnets(led,{"1":"GND","2":"STATUS_A"})
smd2("R17","1k","+3V3","PWR_LED",96,30)
led2=load("LED_SMD","LED_0603_1608Metric","LED2","POWER GREEN",103,30); setnets(led2,{"1":"GND","2":"PWR_LED"})

# Short local same-net links that should not be sent through the general router.
track("GND",[(19.2,72.68),(20.32,72.105)],0.6,pcbnew.F_Cu)
track("GND",[(12.8,72.68),(11.68,72.105)],0.6,pcbnew.F_Cu)

# Pre-routed local links and ground-plane fan-outs. These prevent tiny same-net
# component connections from being left as unreachable autorouter stubs.
track("LOGIC_VIN",[(51.1375,20.0),(54.0,20.0),(54.0,27.0),(53.05,27.0)],0.5,pcbnew.F_Cu)
track("LOGIC_VIN",[(48.8625,20.95),(48.8625,23.0),(54.0,23.0)],0.5,pcbnew.F_Cu)
track("LOGIC_VIN",[(54.0,20.0),(55.0,18.0)],0.5,pcbnew.F_Cu)
track("+3V3",[(51.1375,20.95),(52.5,22.0)],0.4,pcbnew.F_Cu); via("+3V3",52.5,22.0)
track("+3V3",[(44.75,22.0),(44.75,24.0)],0.5,pcbnew.F_Cu); via("+3V3",44.75,24.0)
track("+3V3",[(52.5,22.0),(44.75,24.0)],0.5,pcbnew.In2_Cu)
track("SW6",[(70.775,17.0),(72.0,17.0),(72.0,20.0),(73.8625,20.0)],0.9,pcbnew.F_Cu)
track("SW6",[(63.25,22.0),(67.0,22.0),(67.0,20.0),(72.0,20.0)],0.9,pcbnew.F_Cu)
# 12 V feed to U3 on In2.Cu, clear of the dense switch node on F.Cu.
track("+12V",[(73.8625,20.95),(74.0,23.5)],0.4,pcbnew.F_Cu); via("+12V",74.0,23.5)
track("+12V",[(79.05,14.0),(79.05,12.5)],0.8,pcbnew.F_Cu); via("+12V",79.05,12.5)
track("+12V",[(74.0,23.5),(79.05,12.5)],0.8,pcbnew.In2_Cu)
track("+12V",[(81.175,20.0),(80.0,21.5)],0.4,pcbnew.F_Cu); via("+12V",80.0,21.5)
track("+12V",[(80.0,21.5),(79.05,12.5)],0.6,pcbnew.In2_Cu)
# Native USB protected pair, kept entirely on F.Cu over the ground reference.
track("USB_D+",[(30.25,39.75),(30.25,42.0),(24.5,47.0),(24.5,49.1375),(22.95,49.1375)],0.25,pcbnew.F_Cu)
track("USB_D-",[(28.98,39.75),(28.98,42.0),(18.0,42.0),(18.0,49.1375),(21.05,49.1375)],0.25,pcbnew.F_Cu)
track("USB_D-",[(18.0,54.175),(18.0,49.1375)],0.25,pcbnew.F_Cu)
track("USB_D+",[(25.0,54.175),(25.0,51.0),(24.5,49.1375)],0.25,pcbnew.F_Cu)
# USB VBUS and CC1 service routing on B.Cu, away from the protected data pair.
track("USB_VBUS",[(22.0,49.1375),(22.0,51.0)],0.5,pcbnew.F_Cu); via("USB_VBUS",22.0,51.0)
track("USB_VBUS",[(59.0,23.0),(61.0,23.0)],0.5,pcbnew.F_Cu); via("USB_VBUS",61.0,23.0)
track("USB_VBUS",[(18.4,72.68),(18.4,74.0)],0.5,pcbnew.F_Cu); via("USB_VBUS",18.4,74.0)
track("USB_VBUS",[(18.4,74.0),(24.0,74.0),(24.0,60.0),(22.0,51.0)],0.5,pcbnew.In2_Cu)
track("USB_VBUS",[(10.0,74.0),(10.0,60.0),(22.0,51.0)],0.5,pcbnew.In2_Cu)
track("USB_VBUS",[(22.0,51.0),(61.0,23.0)],0.5,pcbnew.In2_Cu)
via("USB_VBUS",10.0,74.0); track("USB_VBUS",[(13.6,72.68),(13.6,74.0),(10.0,74.0)],0.4,pcbnew.F_Cu)
track("CC1",[(17.25,72.68),(17.25,74.0)],0.2,pcbnew.F_Cu); via("CC1",17.25,74.0)
track("CC1",[(8.175,65.0),(6.5,65.0)],0.2,pcbnew.F_Cu); via("CC1",6.5,65.0)
track("CC1",[(6.5,65.0),(17.25,65.0),(17.25,74.0)],0.2,pcbnew.B_Cu)
track("GND",[(87.425,16.905),(85.8,16.905)],0.55,pcbnew.F_Cu); via("GND",85.8,16.905)
track("GND",[(105.0,18.85),(103.5,18.85)],0.55,pcbnew.F_Cu); via("GND",103.5,18.85)


# Routing is generated from the complete netlist below; the final release widens
# the high-current 12 V / 6 V paths after the autorouter completes them.

# Front silkscreen labels and safety notes.
for text,x,y,size in [("REDCAT 51 II FLAT PANEL CONTROLLER REV C",60,72,1.0),("MAIN 12V 2A MAX",104,10,0.8),("ASIAIR PWM",84,10,0.8),("USB-C PROGRAM + ASCOM",20,68,0.8),("KEYED SERVO",108,45,0.7),("LED",108,34,0.8),("OPEN NC",108,55,0.65),("CLOSED NC",108,63,0.65),("USB POWERS LOGIC ONLY",47,68,0.7)]:
    t=pcbnew.PCB_TEXT(board); t.SetText(text); t.SetPosition(v(x,y)); t.SetLayer(pcbnew.F_SilkS); t.SetTextSize(v(size,size)); t.SetTextThickness(MM(0.15)); board.Add(t)

pcbnew.SaveBoard(str(HERE/"redcat51ii-flat-panel-revc.kicad_pcb"),board)
print(HERE/"redcat51ii-flat-panel-revc.kicad_pcb")
