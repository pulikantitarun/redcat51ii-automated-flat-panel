"""
RedCat 51 II flat panel controller - Revision C board generator.

WHAT CHANGED FROM REV B
-----------------------
1. COPPER ZONES. Rev B had none - zero zones, zero G36 fills in every gerber.
   GND was 129 individual tracks totalling ~500 mm, on a 4-layer board with two
   switching regulators (one at 4 A). Rev C makes BOTH inner layers solid GND
   and pours GND on F.Cu/B.Cu, so every switching node has an unbroken return
   directly beneath it.

   Why two GND planes instead of GND + a split power plane: the Rev B placement
   interleaves +12V, +6V and +3V3 across the same X range, so no rectangular
   power split is possible without re-placing every part. SIG / GND / GND / SIG
   is the correct stackup for THIS placement, costs nothing, spreads regulator
   heat, and removes any chance of a return path crossing a plane split.

2. THE ASIAIR INPUT IS NOW AN ADC DIVIDER, NOT AN OPTO.
   Deleted: U5 (LTV-817S), D2 (1N4148W), the old R9/R10 opto chain and the
   ASIAIR_LED net. Added a real load resistor, a divider, a filter and a clamp.
   See the block comment at the ASIAIR section for the numbers.

3. J3 servo header re-pinned to the standard GND / V+ / SIG. Rev B had
   6V / GND / SIG, which puts 6 V on the servo's ground wire either way round.

4. USBLC6-2SC6 net assignment fixed. Pins 1 and 6 are the same internal node,
   as are 3 and 4. Rev B straddled R3/R4 across them, shorting out both series
   resistors. Rev C puts all four I/O pins on the connector side.

5. Q1's gate no longer ties straight to GND. Vgs was the full rail; during a
   D1 clamping event it would have exceeded the AO4407A's +/-20 V limit and
   destroyed the FET. Now: 100k to GND + a 10 V zener gate-to-source.

6. D1 SMBJ18A -> SMBJ14A. An 18 V standoff part clamps at ~29 V, which is above
   the AO4407A's 30 V Vds rating with no margin. 14 V standoff clamps at ~23 V.

7. F1 3A -> 4A. A 3 A PTC derates to ~2.4 A hold in a sealed box, below the
   DS3218's 2.7 A stall - it would have nuisance-tripped mid-sequence.

8. Buck input capacitance raised. A 10uF 25V 0805 X5R sitting at 12 V DC bias
   derates to ~4-5 uF; that was the entire input reservoir for a 4 A regulator.
   Now 2x 10uF 1210 (far better bias behaviour) + 100nF per regulator.

STILL REQUIRED BEFORE FABRICATION - DO NOT SKIP
-----------------------------------------------
This script emits placement, nets and copper pours. It does NOT route signals.
The Rev B flow was: this script -> export_dsn.py -> freerouting -> import_ses.py,
then manual widening of the +12V/+6V paths. That flow still applies, EXCEPT that
GND must NOT be handed to the autorouter any more - it lives on the planes and
is stitched by vias.

And the thing Rev B never had: there is still no schematic, so there has still
been no ERC. A DRC pass against a hand-typed netlist only proves the geometry
matches what was typed - it cannot tell you the netlist itself is wrong. That is
precisely how the USBLC6 short and the servo header pinout survived Rev B's
"0 DRC violations". Draw the schematic before you spend money on this.
"""

from pathlib import Path
import os
import sys
import pcbnew

HERE = Path(__file__).resolve().parent
MM = pcbnew.FromMM


# --------------------------------------------------------------------------
# Footprint library location. Rev B hard-coded a Windows KiCad 10 path, so the
# script only ever ran on one machine. Search instead.
# --------------------------------------------------------------------------
def find_footprints():
    env = os.environ.get("KICAD_FOOTPRINT_DIR")
    cands = ([Path(env)] if env else []) + [
        Path(r"C:\Program Files\KiCad\10.0\share\kicad\footprints"),
        Path(os.path.expandvars(r"%LOCALAPPDATA%\Programs\KiCad\10.0\share\kicad\footprints")),
        Path("/usr/share/kicad/footprints"),
        Path("/usr/local/share/kicad/footprints"),
        Path("/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"),
    ]
    for c in cands:
        try:
            if c.is_dir() and (c / "Resistor_SMD.pretty").is_dir():
                return c
        except OSError:
            pass
    raise RuntimeError(
        "Cannot find the KiCad footprint libraries. Set KICAD_FOOTPRINT_DIR.")


KICAD_FP = find_footprints()
KIVER = int(pcbnew.Version().split(".")[0])
print(f"KiCad {pcbnew.Version()}  footprints: {KICAD_FP}")

board = pcbnew.BOARD()
board.SetCopperLayerCount(4)
ds = board.GetDesignSettings()
ds.m_TrackMinWidth = MM(0.20)
ds.m_MinClearance = MM(0.20)
ds.m_MinThroughDrill = MM(0.30)      # was 0.20 - every fab surcharges below 0.3
ds.m_CopperEdgeClearance = MM(0.30)
ds.m_HoleClearance = MM(0.20)


def v(x, y):
    return pcbnew.VECTOR2I(MM(x), MM(y))


net_names = [
    "GND", "+12V_RAW", "+12V_FUSED", "+12V", "+6V", "+3V3", "USB_VBUS",
    "USB_D+_J", "USB_D-_J", "USB_D+", "USB_D-", "CC1", "CC2", "EN", "BOOT",
    "ASIAIR+", "ASIAIR-", "ASIAIR_SIG", "LED_PWM", "LED_GATE", "LED_NEG",
    "GATE12",
    "SERVO_SIG", "OPEN_SIG", "CLOSED_SIG", "BUTTON_SIG", "STATUS_LED",
    "STATUS_A", "PWR_LED", "SW6", "BST6", "FB6", "EN6", "SW3", "BST3",
]
nets = {}
for name in net_names:
    n = pcbnew.NETINFO_ITEM(board, name)
    board.Add(n)
    nets[name] = n

# Netclasses: KiCad 8 added SetNetclassPatternAssignment; 7 has no equivalent.
try:
    nsettings = board.GetDesignSettings().GetNetSettings()
    if hasattr(nsettings, "SetNetclassPatternAssignment"):
        for nm in ["+12V_RAW", "+12V_FUSED", "+12V"]:
            nsettings.SetNetclassPatternAssignment(nm, "Power12")
        for nm in ["+6V", "SW6"]:
            nsettings.SetNetclassPatternAssignment(nm, "Servo6")
        for nm in ["+3V3", "SW3"]:
            nsettings.SetNetclassPatternAssignment(nm, "LogicPower")
except Exception as e:  # noqa: BLE001
    print(f"  (netclass assignment skipped: {e})")

BOARD_OUTLINE = [(3, 0), (117, 0), (120, 3), (120, 72), (117, 75),
                 (3, 75), (0, 72), (0, 3)]


def line(parent, x1, y1, x2, y2, layer, width=0.15):
    s = pcbnew.PCB_SHAPE(parent)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(v(x1, y1))
    s.SetEnd(v(x2, y2))
    s.SetLayer(layer)
    s.SetWidth(MM(width))
    parent.Add(s)


for a, b in zip(BOARD_OUTLINE, BOARD_OUTLINE[1:] + BOARD_OUTLINE[:1]):
    line(board, *a, *b, pcbnew.Edge_Cuts, 0.1)


def load(lib, name, ref, value, x, y, angle=0):
    """`name` may be a single name or a tuple of acceptable alternatives - the
    KiCad footprint libraries rename and add parts between major versions, and
    Rev B's hard-coded single names meant the script only ran on one machine
    with one KiCad install."""
    names = (name,) if isinstance(name, str) else tuple(name)
    fp = None
    for n in names:
        fp = pcbnew.FootprintLoad(str(KICAD_FP / f"{lib}.pretty"), n)
        if fp is not None:
            if n != names[0]:
                print(f"  note: {ref} using fallback footprint {lib}:{n}")
            break
    if fp is None:
        raise RuntimeError(f"Missing footprint {lib}:{names}")
    fp.SetReference(ref)
    fp.SetValue(value)
    fp.SetPosition(v(x, y))
    fp.SetOrientationDegrees(angle)
    fp.Reference().SetVisible(True)
    fp.Value().SetVisible(False)
    board.Add(fp)
    return fp


def setnets(fp, mapping, optional=()):
    """Assign nets to pads by pad number, and REFUSE to silently ignore a pad
    name the footprint does not have. Rev B mapped nets onto pads that did not
    exist and onto pads that were internally common, and nothing complained.

    `optional` lists pad numbers that legitimately vary between KiCad library
    versions (e.g. the USB-C shield is "S1" in KiCad 7 and "SH" in some others).
    At least one optional pad must still match, or the shield ends up floating.
    """
    seen = set()
    for p in fp.Pads():
        num = p.GetNumber()
        if num in mapping:
            p.SetNet(nets[mapping[num]])
            seen.add(num)
    missing = set(mapping) - seen - set(optional)
    if missing:
        raise RuntimeError(
            f"{fp.GetReference()}: netlist names pads {sorted(missing)} that the "
            f"footprint does not have. This is the class of error that killed Rev B.")
    if optional and not (set(optional) & seen):
        raise RuntimeError(
            f"{fp.GetReference()}: none of the optional pads {sorted(optional)} "
            f"exist - the shield would be left floating.")
    return fp


def smd2(ref, value, net1, net2, x, y, kind="R", size="0603", angle=0):
    if kind == "R":
        lib = "Resistor_SMD"
        name = {"0603": "R_0603_1608Metric", "0805": "R_0805_2012Metric",
                "1206": "R_1206_3216Metric", "2512": "R_2512_6332Metric"}[size]
    elif kind == "C":
        lib = "Capacitor_SMD"
        name = {"0603": "C_0603_1608Metric", "0805": "C_0805_2012Metric",
                "1206": "C_1206_3216Metric", "1210": "C_1210_3225Metric"}[size]
    else:
        lib = "Inductor_SMD"
        name = "L_6.3x6.3_H3" if size == "6.3" else "L_4.0x4.0_H2.0"
    fp = load(lib, name, ref, value, x, y, angle)
    setnets(fp, {"1": net1, "2": net2})
    return fp


def diode(ref, value, cathode, anode, x, y, angle=0, pkg="D_SOD-123"):
    """KiCad D_SOD-123 / D_SMB: pad 1 = cathode, pad 2 = anode."""
    fp = load("Diode_SMD", pkg, ref, value, x, y, angle)
    setnets(fp, {"1": cathode, "2": anode})
    return fp


def jst(ref, value, n1, n2, x, y, angle=0):
    fp = load("Connector_JST", "JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical",
              ref, value, x, y, angle)
    setnets(fp, {"1": n1, "2": n2})
    return fp


def via(net, x, y, drill=0.4, width=0.8):
    q = pcbnew.PCB_VIA(board)
    q.SetPosition(v(x, y))
    q.SetNet(nets[net])
    q.SetWidth(MM(width))
    q.SetDrill(MM(drill))
    q.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    board.Add(q)
    return q


def track(net, pts, width=0.25, layer=pcbnew.F_Cu):
    for a, b in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(v(*a))
        t.SetEnd(v(*b))
        t.SetWidth(MM(width))
        t.SetLayer(layer)
        t.SetNet(nets[net])
        board.Add(t)


# --------------------------------------------------------------------------
# Mounting holes: 112 x 67 mm rectangle. The mechanical CAD derives the
# enclosure standoffs from these exact coordinates - do not move them without
# re-running mechanical/generate_parts.py.
# --------------------------------------------------------------------------
for i, (x, y) in enumerate([(40, 4), (116, 4), (40, 71), (116, 71)], 1):
    load("MountingHole", "MountingHole_3.2mm_M3", f"H{i}", "M3", x, y)

# --------------------------------------------------------------------------
# ESP32-S3-WROOM-1. Pin mapping verified against the Espressif datasheet and
# against the firmware - this was already correct in Rev B and is unchanged.
# GPIO4 is ADC1_CH3, which is what makes the new ASIAIR front end possible.
# --------------------------------------------------------------------------
u1 = load("RF_Module", "ESP32-S3-WROOM-1", "U1", "ESP32-S3-WROOM-1-N8R8", 19, 31, 90)
setnets(u1, {"1": "GND", "2": "+3V3", "3": "EN", "4": "ASIAIR_SIG", "5": "LED_PWM",
             "6": "OPEN_SIG", "7": "CLOSED_SIG", "8": "STATUS_LED", "11": "SERVO_SIG",
             "13": "USB_D-", "14": "USB_D+", "17": "BUTTON_SIG", "27": "BOOT",
             "40": "GND", "41": "GND"})

# --------------------------------------------------------------------------
# USB-C, USB2 only. Board is powered from MAIN 12 V; VBUS is sense/ESD only.
# --------------------------------------------------------------------------
j8 = load("Connector_USB", "USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal",
          "J8", "USB-C PROGRAM", 16, 69, 180)
setnets(j8, {"A1": "GND", "A4": "USB_VBUS", "A5": "CC1", "A6": "USB_D+_J",
             "A7": "USB_D-_J", "A9": "USB_VBUS", "A12": "GND", "B1": "GND",
             "B4": "USB_VBUS", "B5": "CC2", "B6": "USB_D+_J", "B7": "USB_D-_J",
             "B9": "USB_VBUS", "B12": "GND", "SH": "GND", "S1": "GND"},
        optional=("SH", "S1"))
smd2("R1", "5.1k", "CC1", "GND", 9, 65)
smd2("R2", "5.1k", "CC2", "GND", 25, 65)
smd2("R3", "22R", "USB_D+_J", "USB_D+", 21, 61, angle=90)
smd2("R4", "22R", "USB_D-_J", "USB_D-", 24, 61, angle=90)

# USBLC6-2SC6: pins 1+6 are ONE node (I/O1), pins 3+4 are ONE node (I/O2).
# Both I/O nodes belong on the CONNECTOR side of the series resistors.
u2 = load("Package_TO_SOT_SMD", "SOT-23-6", "U2", "USBLC6-2SC6", 17, 57)
setnets(u2, {"1": "USB_D+_J", "2": "GND", "3": "USB_D-_J",
             "4": "USB_D-_J", "5": "USB_VBUS", "6": "USB_D+_J"})

# --------------------------------------------------------------------------
# Reset, boot, manual button
# --------------------------------------------------------------------------
smd2("R5", "10k", "+3V3", "EN", 30, 49)
smd2("C1", "1uF", "EN", "GND", 35, 49, kind="C")
setnets(load("Button_Switch_SMD", ("SW_Push_1P1T_NO_E-Switch_TL3301NxxxxxG", "SW_Push_1P1T_NO_CK_KMR2"),
             "SW1", "RESET", 30, 55), {"1": "EN", "2": "GND"})
smd2("R6", "10k", "+3V3", "BOOT", 42, 49)
setnets(load("Button_Switch_SMD", ("SW_Push_1P1T_NO_E-Switch_TL3301NxxxxxG", "SW_Push_1P1T_NO_CK_KMR2"),
             "SW2", "BOOT", 42, 55), {"1": "BOOT", "2": "GND"})
setnets(load("Button_Switch_SMD", ("SW_Push_1P1T_NO_E-Switch_TL3301NxxxxxG", "SW_Push_1P1T_NO_CK_KMR2"),
             "SW3", "MANUAL", 54, 55), {"1": "BUTTON_SIG", "2": "GND"})

# --------------------------------------------------------------------------
# Power input, reverse-polarity FET, TVS
# --------------------------------------------------------------------------
j1 = load("Connector_BarrelJack", "BarrelJack_CUI_PJ-102AH_Horizontal",
          "J1", "MAIN 12V DC5521", 106, 8, 180)
setnets(j1, {"1": "+12V_RAW", "2": "GND", "3": "GND"})
setnets(load("Fuse", "Fuse_1812_4532Metric", "F1", "4A 16V PTC", 98, 14),
        {"1": "+12V_RAW", "2": "+12V_FUSED"})
smd2("C17", "100nF", "+12V_RAW", "GND", 101, 19, kind="C")

# Q1 AO4407A P-channel reverse-polarity switch.
#   SO-8 MOSFET: pins 1-3 = Source, 4 = Gate, 5-8 = Drain.
#   Source = +12V (load side), Drain = +12V_FUSED (input side).
# Rev B tied the gate straight to GND, so Vgs = -Vin. At a 12 V rail that is
# survivable; while D1 clamps a surge it is not. R21 + D3 fix it.
q1 = load("Package_SO", "SO-8_3.9x4.9mm_P1.27mm", "Q1", "AO4407A", 90, 15)
setnets(q1, {"1": "+12V", "2": "+12V", "3": "+12V", "4": "GATE12",
             "5": "+12V_FUSED", "6": "+12V_FUSED", "7": "+12V_FUSED",
             "8": "+12V_FUSED"})
smd2("R21", "100k", "GATE12", "GND", 90, 22)
diode("D3", "MMSZ5240B 10V", "+12V", "GATE12", 84, 22)   # clamps Vgs to -10 V
diode("D1", "SMBJ14A", "+12V", "GND", 105, 21, angle=90, pkg="D_SMB")
setnets(load("Capacitor_SMD", "CP_Elec_10x10.5", "C2", "470uF 25V", 70, 52),
        {"1": "+12V", "2": "GND"})

# --------------------------------------------------------------------------
# 6.0 V / 4 A servo supply (AP62401, forced PWM)
# --------------------------------------------------------------------------
u3 = load("Package_TO_SOT_SMD", "TSOT-23-6", "U3", "AP62401WU-7", 75, 20)
setnets(u3, {"1": "GND", "2": "SW6", "3": "+12V", "4": "FB6", "5": "EN6", "6": "BST6"})
smd2("C3", "100nF", "BST6", "SW6", 70, 17, kind="C")
smd2("C4", "10uF 25V", "+12V", "GND", 80, 14, kind="C", size="1210")
smd2("C4B", "10uF 25V", "+12V", "GND", 84, 27, kind="C", size="1210")
smd2("C15", "100nF", "+12V", "GND", 80, 24, kind="C")
smd2("R18", "100k", "+12V", "EN6", 82, 20)
smd2("L1", "3.3uH 6.5A", "SW6", "+6V", 66, 22, kind="L", size="6.3")
smd2("R7", "64.9k 1%", "+6V", "FB6", 72, 27)
smd2("R8", "10k 1%", "FB6", "GND", 78, 27)
smd2("C5", "22uF 10V", "+6V", "GND", 62, 30, kind="C", size="0805")
smd2("C6", "22uF 10V", "+6V", "GND", 68, 30, kind="C", size="0805")
setnets(load("Capacitor_SMD", "CP_Elec_8x10.5", "C7", "470uF 10V", 76, 36),
        {"1": "+6V", "2": "GND"})

# --------------------------------------------------------------------------
# 3.3 V / 2 A logic supply (AP63203)
# --------------------------------------------------------------------------
u4 = load("Package_TO_SOT_SMD", "TSOT-23-6", "U4", "AP63203WU-7", 50, 20)
setnets(u4, {"1": "GND", "2": "SW3", "3": "+12V", "4": "+3V3", "5": "+12V", "6": "BST3"})
smd2("C8", "100nF", "BST3", "SW3", 45, 17, kind="C")
smd2("C9", "10uF 25V", "+12V", "GND", 55, 14, kind="C", size="1210")
smd2("C16", "100nF", "+12V", "GND", 55, 24, kind="C")
smd2("L2", "4.7uH 3A", "SW3", "+3V3", 42, 22, kind="L", size="6.3")
smd2("C10", "22uF 10V", "+3V3", "GND", 44, 30, kind="C", size="0805")
smd2("C11", "22uF 10V", "+3V3", "GND", 50, 30, kind="C", size="0805")
smd2("C12", "10uF", "+3V3", "GND", 35, 30, kind="C", size="0805")
smd2("C13", "100nF", "+3V3", "GND", 35, 35, kind="C")

# ==========================================================================
# ASIAIR SENSING - the heart of the Rev C change
# ==========================================================================
# The ASIAIR Plus capacitively filters its power outputs. Rev B's opto drew
# ~4.9 mA through a 2.2k resistor, which is nowhere near enough to discharge
# that filter inside a 20 ms period, so the port never left 12 V and every
# slider position looked like 100 %.
#
# Rev C stops fighting the filter and uses it. Measure the AVERAGE instead:
#
#   R9  = 470R 1W    bleeder across the port. A reported measurement puts the
#                    port's filter at ~15 uF (220R discharges it in ~10 ms), so
#                    470R gives tau ~= 7 ms against a 20 ms period: the average
#                    tracks the slider monotonically. 12V/470R = 25.5 mA,
#                    306 mW - hence a 1 W 2512, not an 0603.
#   R19 = 0R         bonds ASIAIR- to board GND, and can be lifted if the
#                    measurement below says the port is low-side switched.
#   R10/R20 = 10k/3k3 divider: 12 V -> 2.977 V, inside ADC1's ~3.1 V full scale.
#   C14 = 10uF       with the divider's 2.48k source impedance this is a 25 ms
#                    time constant - it turns the residual 20 ms ripple into DC.
#   D2  = 3.3V zener clamp. If R20 ever goes open-circuit the ADC pin sees the
#                    full 12 V and the ESP32 dies. It costs 2 cents.
#
# >>> MEASURE THIS BEFORE BUILDING <<<
# This front end assumes the ASIAIR switches the HIGH side, i.e. that the dew
# port's negative terminal is common with the ASIAIR's 12 V input negative.
# Every piece of indirect evidence says it does (people run grounded buck
# converters off these ports without shorting anything), but I have not put a
# meter on one. Check continuity between the dew port's barrel SLEEVE and the
# ASIAIR's power input NEGATIVE. Near 0 ohms: common ground, build as drawn.
# Anything else: STOP - do not fit R19, and this front end needs rethinking.
# ==========================================================================
j2 = load("Connector_BarrelJack", "BarrelJack_CUI_PJ-102AH_Horizontal",
          "J2", "ASIAIR PWM DC5521", 84, 8, 180)
setnets(j2, {"1": "ASIAIR+", "2": "ASIAIR-", "3": "ASIAIR-"})
smd2("R9", "470R 1W", "ASIAIR+", "ASIAIR-", 74, 9, kind="R", size="2512")
smd2("R19", "0R", "ASIAIR-", "GND", 66, 13, kind="R", size="1206")
smd2("R10", "10k", "ASIAIR+", "ASIAIR_SIG", 63, 9)
smd2("R20", "3k3", "ASIAIR_SIG", "GND", 59, 13)
smd2("C14", "10uF", "ASIAIR_SIG", "GND", 59, 9, kind="C", size="0805")
diode("D2", "MMSZ5226B 3V3", "ASIAIR_SIG", "GND", 55, 9)

# --------------------------------------------------------------------------
# LED panel low-side driver and field connectors
# --------------------------------------------------------------------------
smd2("R11", "100R", "LED_PWM", "LED_GATE", 80, 47)
smd2("R12", "10k", "LED_GATE", "GND", 86, 47)
setnets(load("Package_TO_SOT_SMD", "SOT-23", "Q2", "AO3400A", 92, 47),
        {"1": "LED_GATE", "2": "GND", "3": "LED_NEG"})
jst("J4", "LED PANEL", "+12V", "LED_NEG", 113, 34, 90)

# J3: standard hobby-servo lead order is GND / V+ / SIG, brown/red/orange.
# Rev B wired 6V / GND / SIG, which lands 6 V on the servo's black wire.
j3 = load("Connector_PinHeader_2.54mm", "PinHeader_1x03_P2.54mm_Vertical",
          "J3", "SERVO GND 6V SIG", 113, 45, 90)
setnets(j3, {"1": "GND", "2": "+6V", "3": "SERVO_SIG"})

jst("J5", "OPEN LIMIT", "OPEN_SIG", "GND", 113, 53, 90)
jst("J6", "CLOSED LIMIT", "CLOSED_SIG", "GND", 113, 64, 90)
jst("J7", "EXT MANUAL", "BUTTON_SIG", "GND", 101, 68, 180)
smd2("R13", "10k", "+3V3", "OPEN_SIG", 98, 52)
smd2("R14", "10k", "+3V3", "CLOSED_SIG", 98, 57)
smd2("R15", "10k", "+3V3", "BUTTON_SIG", 89, 62)
smd2("R16", "1k", "STATUS_LED", "STATUS_A", 36, 42)
setnets(load("LED_SMD", "LED_0603_1608Metric", "LED1", "STATUS BLUE", 42, 42),
        {"1": "GND", "2": "STATUS_A"})
smd2("R17", "1k", "+3V3", "PWR_LED", 96, 30)
setnets(load("LED_SMD", "LED_0603_1608Metric", "LED2", "POWER GREEN", 103, 30),
        {"1": "GND", "2": "PWR_LED"})


# ==========================================================================
# COPPER ZONES - the single biggest Rev B defect
# ==========================================================================
def add_zone(net, layers, outline, priority=0, inset=0.4):
    z = pcbnew.ZONE(board)
    ls = pcbnew.LSET()
    for L in layers:
        ls.addLayer(L)
    z.SetLayerSet(ls)
    z.SetNet(nets[net])
    # KiCad renamed this between versions; support both.
    if hasattr(z, "SetAssignedPriority"):
        z.SetAssignedPriority(priority)
    else:
        z.SetPriority(priority)
    z.SetLocalClearance(MM(0.25))
    z.SetMinThickness(MM(0.20))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetThermalReliefGap(MM(0.3))
    z.SetThermalReliefSpokeWidth(MM(0.4))
    pts = pcbnew.VECTOR_VECTOR2I()
    cx = sum(p[0] for p in outline) / len(outline)
    cy = sum(p[1] for p in outline) / len(outline)
    for (x, y) in outline:
        dx, dy = x - cx, y - cy
        m = max((dx * dx + dy * dy) ** 0.5, 1e-6)
        pts.append(v(x - inset * dx / m, y - inset * dy / m))
    z.AddPolygon(pts)
    board.Add(z)
    return z


# In1 and In2: solid, uninterrupted GND. Every switching node - SW6, SW3, the
# 470uF bulk loops, the servo return - now has a return path directly beneath it
# instead of a hand-routed track taking the scenic route.
gnd_in1 = add_zone("GND", [pcbnew.In1_Cu], BOARD_OUTLINE, priority=0)
gnd_in2 = add_zone("GND", [pcbnew.In2_Cu], BOARD_OUTLINE, priority=0)
# F/B: GND pour around the signal routing.
gnd_f = add_zone("GND", [pcbnew.F_Cu], BOARD_OUTLINE, priority=0)
gnd_b = add_zone("GND", [pcbnew.B_Cu], BOARD_OUTLINE, priority=0)


# --------------------------------------------------------------------------
# GND stitching vias. Without these the planes are decorative: F.Cu pours and
# the inner planes would only meet wherever the autorouter happened to drop a
# via. Grid them, but skip anything that lands on an existing pad, hole or the
# board edge.
# --------------------------------------------------------------------------
def pad_keepouts():
    boxes = []
    for fp in board.GetFootprints():
        for p in fp.Pads():
            bb = p.GetBoundingBox()
            boxes.append((bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom()))
        bb = fp.GetBoundingBox(False, False)
        if fp.GetReference() in ("U1", "J8", "J1", "J2", "C2", "C7"):
            boxes.append((bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom()))
    return boxes


def inside_outline(x, y, margin=2.0):
    # the octagon, conservatively: rectangle minus the four corner triangles
    if not (margin <= x <= 120 - margin and margin <= y <= 75 - margin):
        return False
    for (cx, cy) in ((0, 0), (120, 0), (0, 75), (120, 75)):
        if abs(x - cx) + abs(y - cy) < 3 + margin:
            return False
    return True


keepouts = pad_keepouts()
CLR = MM(0.8)
stitch_count = 0
for gx in range(4, 118, 6):
    for gy in range(4, 74, 6):
        if not inside_outline(gx, gy):
            continue
        px, py = MM(gx), MM(gy)
        blocked = any(px > l - CLR and px < r + CLR and py > t - CLR and py < b + CLR
                      for (l, t, r, b) in keepouts)
        if blocked:
            continue
        via("GND", gx, gy)
        stitch_count += 1

# Fill the zones.
#
# NOTE: pcbnew's ZONE_FILLER segfaults when driven from standalone Python on
# some builds (KiCad 7 does, reliably, even under a wx app and a virtual X
# display). That is a limitation of the scripting host, not of this design - the
# zones themselves are defined, netted and layered correctly in the saved file.
#
# >>> CONSEQUENCE YOU MUST NOT IGNORE <<<
# KiCad plots gerbers from the STORED fill. If the zones are unfilled in the
# file, the gerbers contain no plane copper - which would look exactly like the
# Rev B failure even though the design is right. Open the board in pcbnew, press
# B to fill all zones, THEN plot.
board.BuildConnectivity()
zones_filled = False
ATTEMPT_FILL = KIVER >= 8 and os.environ.get("SKIP_ZONE_FILL") != "1"
if ATTEMPT_FILL:
    # A segfault is not an exception - try/except cannot save you here. This is
    # gated on version instead, and left to the GUI if it goes wrong.
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    zones_filled = all(z.IsFilled() for z in board.Zones())
else:
    print("  zone fill NOT attempted on this KiCad build - press B in pcbnew")

for text, x, y, size in [
    ("REDCAT 51 II FLAT PANEL - REV C", 60, 72, 1.0),
    ("MAIN 12V", 106, 10, 0.8), ("ASIAIR PWM", 84, 10, 0.8),
    ("USB PROGRAM", 16, 68, 0.8), ("SERVO GND-6V-SIG", 108, 45, 0.7),
    ("LED", 108, 34, 0.8), ("OPEN", 108, 55, 0.7), ("CLOSED", 108, 63, 0.7),
    ("12V MAIN REQUIRED FOR USB PROGRAMMING", 48, 68, 0.7),
]:
    t = pcbnew.PCB_TEXT(board)
    t.SetText(text)
    t.SetPosition(v(x, y))
    t.SetLayer(pcbnew.F_SilkS)
    t.SetTextSize(v(size, size))
    t.SetTextThickness(MM(0.15))
    board.Add(t)

out = HERE / "redcat51ii-flat-panel-controller-revc.kicad_pcb"
pcbnew.SaveBoard(str(out), board)

# --------------------------------------------------------------------------
# Report. If these numbers are not what you expect, the board is not ready.
# --------------------------------------------------------------------------
print(f"\nfootprints      : {len(board.GetFootprints())}")
print(f"nets            : {len(net_names)}")
print(f"stitching vias  : {stitch_count}")
print("copper zones    :")
for z, nm in ((gnd_f, "F.Cu  "), (gnd_in1, "In1.Cu"), (gnd_in2, "In2.Cu"), (gnd_b, "B.Cu  ")):
    z.CalculateOutlineArea()                       # GetOutlineArea() is a cache
    outline_mm2 = z.GetOutlineArea() / 1e12        # KiCad areas are nm^2
    filled_mm2 = z.GetFilledArea() / 1e12
    print(f"  {nm}  net={z.GetNetname():4s} outline={outline_mm2:7.1f} mm^2  "
          f"filled={filled_mm2:7.1f} mm^2  ({'FILLED' if z.IsFilled() else 'NOT FILLED - press B in pcbnew'})")
print(f"\nsaved: {out}")
if not zones_filled:
    print("\n*** Zones are defined but NOT filled in this file. Open it in pcbnew,")
    print("*** press B, run DRC, and only then plot gerbers. Plotting now would")
    print("*** produce planeless gerbers - the exact Rev B failure.")
