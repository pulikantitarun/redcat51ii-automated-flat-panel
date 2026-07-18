"""
RedCat 51 II automated flat panel - Revision C mechanical source.

WHAT CHANGED FROM REV B (and why)
---------------------------------
Rev B built every part in its own private coordinate system and never assembled
them.  That is how the following escaped:

  * the enclosure box was built centred on z=0 but every cut-out was placed as if
    the floor were z=0, putting the connector openings ~14 mm too high and
    breaching the top rim;
  * the four PCB standoffs were extruded z=0..7 while the cavity floor sat at
    z=-11.5, so they floated in mid-air (the STL contained 5 disconnected bodies);
  * the tray pivot was placed 72 mm from the optical axis on the assumption that
    the servo output shaft sits at the centre of the servo body.  It does not -
    a standard 40 mm-body servo has its shaft offset ~10 mm from body centre, so
    the closed panel would have sat 7-13 mm off-axis;
  * the servo platform met the clamp with a ~1 mm deep sliver of overlap and no
    gussets or fillets anywhere.

Rev C builds every part in ONE shared scope coordinate frame, asserts the
clearances numerically, and exports an assembly STEP so the next mistake of this
class is visible instead of latent.

COORDINATE FRAME (scope frame)
------------------------------
    origin  = on the optical axis, at the REAR face of the clamp
    +Z      = along the optical axis, toward the sky
    -X      = toward the servo (the 9 o'clock position, viewed from the front)

    Z=0      clamp rear face
    Z=17..25 servo shelf (integral with clamp, carried on two full-depth webs)
    Z=25..29 servo plate (separate part - isolates the shaft-offset unknown)
    Z=30     clamp front face ~ dew shield front lip
    Z=35     servo top face  -> horn at Z=35..38
    Z=35.8   tray rear face  (= 3 mm of clearance in front of the shield rim,
                              plus the 2.8 mm retaining ring at Z=33..35.8)
    Z=38..43 tray arm / hub  (bolts to the horn)

PARTS ARE MODELLED in this frame and exported to STL in a PRINT frame (flat, no
support).  The assembly STEP is exported in the scope frame.

>>> MEASURE THESE FOUR NUMBERS BEFORE PRINTING ANYTHING EXPENSIVE <<<
Everything else is derived.  Each has a cheap coupon to check it against.
"""

from pathlib import Path
import math
import cadquery as cq
from cadquery import exporters

HERE = Path(__file__).resolve().parent
OUT = HERE

# ============================================================================
# MEASURED PARAMETERS  - the only numbers you should ever need to touch
# ============================================================================

# 1. Dew shield outside diameter.  Check with 01-diameter-fit-gauge.
#    William Optics quote the RedCat 51 II as 228 x 80 mm "with the retracted
#    dew shield", so 80.0 is a *plausible* default - it is not a measurement.
SCOPE_DIAMETER = 80.0

# 2. Servo output shaft offset from the centre of the servo body, along the
#    body's long axis.  ~10 mm on a standard 40 mm-body servo (DS3218/MG996R
#    class).  Check with 09-servo-shaft-gauge before printing the plate.
SERVO_SHAFT_OFFSET = 10.0

# 3. Distance from the servo's top face down to the underside of the mounting
#    ears.  Sets the horn height, and therefore the tray height.
SERVO_EAR_TO_TOP = 10.0

# 4. Barrel jack axis height above the PCB top surface.  The PJ-102AH drawing
#    gives body 14.4 x 11.0 x 9.0 mm and a 6.5 mm nose, but does not label the
#    axis height unambiguously, and KiCad ships this footprint's 3D model as
#    VRML only - so it is absent from the board STEP and cannot be measured.
#    The Rev C opening is deliberately oversized (see DC_JACK_OPENING_D) so this
#    number does not have to be exactly right.  Check with 10-connector-coupon.
DC_JACK_AXIS_Z = 4.7

# ============================================================================
# DERIVED / FIXED PARAMETERS
# ============================================================================

LINER_THICKNESS = 0.8
FIT_CLEARANCE = 0.5
CLAMP_ID = SCOPE_DIAMETER + 2 * LINER_THICKNESS + FIT_CLEARANCE   # 82.1
CLAMP_WALL = 6.0
CLAMP_OD = CLAMP_ID + 2 * CLAMP_WALL                              # 94.1
CLAMP_R = CLAMP_OD / 2                                            # 47.05
CLAMP_H = 30.0            # was 24 in Rev B - more grip, more web height

# Servo envelope (standard 40 mm "20 kg" servo: DS3218, MG996R, ...)
SERVO_BODY_L = 40.0
SERVO_BODY_W = 20.0
SERVO_BODY_H = 40.5
SERVO_HOLE_DX = 49.5      # Rev B used 49.0; the standard is 49.5
SERVO_HOLE_DY = 10.0

# Pivot: optical axis -> servo output shaft.
# Lower bound is set by the servo body clearing the clamp; upper bound by the
# swing envelope.  check_clearances() proves the choice.
PIVOT_R = 72.0

# Z stack
SHELF_Z0, SHELF_Z1 = 17.0, 25.0
PLATE_T = 4.0
PLATE_Z0 = SHELF_Z1                       # 25
PLATE_Z1 = PLATE_Z0 + PLATE_T             # 29
SERVO_TOP_Z = PLATE_Z1 + SERVO_EAR_TO_TOP # 39  (ears rest on the plate top)
HORN_T = 3.0
ARM_T = 5.0
ARM_Z0 = SERVO_TOP_Z + HORN_T             # 42
ARM_Z1 = ARM_Z0 + ARM_T                   # 47

# Tray / panel
TRAY_OD = 104.0
TRAY_R = TRAY_OD / 2
RECESS_D = 82.4
TRAY_T = 14.0
FLOOR_T = 3.0
RETAINER_T = 2.8
RETAINER_ID = 74.0
PANEL_CLEARANCE = 3.0                     # closed diffuser -> dew shield rim
RETAINER_Z0 = CLAMP_H + PANEL_CLEARANCE   # 33.0
TRAY_Z0 = RETAINER_Z0 + RETAINER_T        # 35.8  (tray rear face)
TRAY_Z1 = TRAY_Z0 + TRAY_T                # 49.8

# Motion
OPEN_ANGLE_DEG = 104.0

# Enclosure / PCB
PCB_X, PCB_Y, PCB_T = 120.0, 75.0, 1.6
PCB_HOLES = [(40, 4), (116, 4), (40, 71), (116, 71)]   # board coords
STANDOFF_H = 6.0
STANDOFF_OD = 7.6
STANDOFF_PILOT = 2.7                      # M3 thread-forming pilot
WALL = 2.6
FLOOR = 3.0
BOX_CLEAR_X, BOX_CLEAR_Y = 5.0, 5.0
BOX_IN_X = PCB_X + BOX_CLEAR_X
BOX_IN_Y = PCB_Y + BOX_CLEAR_Y
BOX_OUT_X = BOX_IN_X + 2 * WALL
BOX_OUT_Y = BOX_IN_Y + 2 * WALL
BOX_H = 30.0
DC_JACK_OPENING_D = 10.0   # Ø6.5 nose + the plug's moulded body + tolerance on
                           # DC_JACK_AXIS_Z.  Deliberately generous.
MAX_COMPONENT_H = 10.5     # C2/C7 470uF cans, measured from the board STEP

# Lid fixing.  Rev B's lid was a friction fit with pull lugs.  This box lives
# outdoors, upside down, in dew, on a moving mount - it gets screws.  The bosses
# sit on the OUTER corners so they cost no internal volume and cannot foul the
# board; check_clearances() proves the PCB corner clears them.
BOSS_R = 4.5
BOSS_INSET = 0.6           # boss centre, inboard of the outer corner
BOSS_CX = BOX_OUT_X / 2 - BOSS_INSET
BOSS_CY = BOX_OUT_Y / 2 - BOSS_INSET
LID_T = 3.0

# Strap slots.  The box hangs off the dovetail bar or a tripod leg with a
# hook-and-loop strap - NOT off the dew shield, which is a slip joint that will
# happily let go of an 80 mm tube.
STRAP_W = 25.0
STRAP_T = 3.2

M3_INSERT_D = 4.2
M3_INSERT_L = 5.5
M3_CLEAR = 3.4
M4_CLEAR = 4.4

_warnings = []


def save(name, solid):
    exporters.export(solid, str(OUT / f"{name}.stl"), tolerance=0.05,
                     angularTolerance=0.1)
    exporters.export(solid, str(OUT / f"{name}.step"))


def try_fillet(wp, radius, selector=None):
    """Fillet, but never let a fillet failure kill the build."""
    try:
        return (wp.edges(selector).fillet(radius) if selector
                else wp.edges().fillet(radius))
    except Exception as e:
        _warnings.append(f"fillet r={radius} ({selector}) skipped: {type(e).__name__}")
        return wp


def ring(outer_d, inner_d, height):
    return cq.Workplane("XY").circle(outer_d / 2).circle(inner_d / 2).extrude(height)


# ============================================================================
# 01  Diameter fit gauge  - print this FIRST, it costs 8 minutes
# ============================================================================
def make_fit_gauge():
    g = ring(CLAMP_ID + 7, CLAMP_ID, 8).cut(
        cq.Workplane("XY").box(8, CLAMP_ID + 14, 12).translate((0, CLAMP_ID / 2, 4))
    )
    return g


# ============================================================================
# 02  Scope clamp + servo shelf
#     Rev B: platform met the clamp with ~1 mm of overlap, no gussets.
#     Rev C: local saddle thickening + two full-depth vertical webs carrying the
#            shelf.  The webs run to Z=0 so the whole part prints flat with no
#            support, and the shelf is a frame (open in the middle for the servo
#            body) so there is almost no unsupported underside.
# ============================================================================
SADDLE_R = CLAMP_R + 5.0          # 52.05
WEB_T = 6.0
WEB_Y = 16.0                      # web centreline
SHELF_X0 = -(PIVOT_R + 40.0)      # -112
SHELF_X1 = -(CLAMP_R - 2.0)       # -45.05  (2 mm inside the OD -> real fusion)
SHELF_Y = 22.0
SERVO_BODY_CX = -(PIVOT_R + SERVO_SHAFT_OFFSET)   # -82: body centre, shaft at -72
SHELF_WINDOW_X = SERVO_BODY_L + 4.0               # 44
SHELF_WINDOW_Y = SERVO_BODY_W + 4.0               # 24
INSERT_X = (-(PIVOT_R + 32.0), -(PIVOT_R - 12.0))  # -104, -60
INSERT_Y = WEB_Y


def make_clamp():
    c = ring(CLAMP_OD, CLAMP_ID, CLAMP_H)

    # local saddle: thicken the OD on the -X side where the bracket loads it
    saddle = (cq.Workplane("XY").circle(SADDLE_R).circle(CLAMP_ID / 2)
              .extrude(CLAMP_H)
              .intersect(cq.Workplane("XY")
                         .box(2 * SADDLE_R, 2 * SADDLE_R, CLAMP_H)
                         .translate((-SADDLE_R, 0, CLAMP_H / 2))))
    c = c.union(saddle)

    # split for compression, +Y side
    c = c.cut(cq.Workplane("XY").box(6, CLAMP_OD + 20, CLAMP_H + 4)
              .translate((0, CLAMP_ID / 2 + 3, CLAMP_H / 2)))

    # M4 compression ears
    ear_y = CLAMP_ID / 2 + 5
    for dx in (-6.5, 6.5):
        c = c.union(cq.Workplane("XY").box(7, 15, CLAMP_H)
                    .translate((dx, ear_y, CLAMP_H / 2)))
    c = c.cut(cq.Workplane("YZ").workplane(offset=-13)
              .center(ear_y, CLAMP_H / 2).circle(M4_CLEAR / 2).extrude(26))

    # two full-depth webs, Z=0 -> shelf underside
    for sy in (-1, 1):
        web = (cq.Workplane("XY")
               .box(SHELF_X1 - SHELF_X0, WEB_T, SHELF_Z0)
               .translate(((SHELF_X0 + SHELF_X1) / 2, sy * WEB_Y, SHELF_Z0 / 2)))
        c = c.union(web)

    # shelf
    shelf = (cq.Workplane("XY")
             .box(SHELF_X1 - SHELF_X0, 2 * SHELF_Y, SHELF_Z1 - SHELF_Z0)
             .translate(((SHELF_X0 + SHELF_X1) / 2, 0, (SHELF_Z0 + SHELF_Z1) / 2)))
    # window for the servo body to hang through
    shelf = shelf.cut(cq.Workplane("XY")
                      .box(SHELF_WINDOW_X, SHELF_WINDOW_Y, 40)
                      .translate((SERVO_BODY_CX, 0, SHELF_Z1)))
    c = c.union(shelf)

    # chamfer the shelf's outboard overhang so it prints without support
    for sy in (-1, 1):
        cutter = (cq.Workplane("XY")
                  .box(SHELF_X1 - SHELF_X0 + 2, 12, 12)
                  .translate(((SHELF_X0 + SHELF_X1) / 2, sy * (SHELF_Y + 6 - 4.2), SHELF_Z0 - 6 + 4.2))
                  .rotate((0, sy * SHELF_Y, SHELF_Z0), (1, sy * SHELF_Y, SHELF_Z0), 45 * sy))
        c = c.cut(cutter)

    # M3 heat-set inserts for the servo plate, blind from the shelf top
    for ix in INSERT_X:
        for sy in (-1, 1):
            c = c.cut(cq.Workplane("XY").center(ix, sy * INSERT_Y)
                      .circle(M3_INSERT_D / 2)
                      .extrude(-M3_INSERT_L)
                      .translate((0, 0, SHELF_Z1)))

    c = try_fillet(c, 1.5, ">Z")
    return c


# ============================================================================
# 03  Servo plate  - the shaft-offset unknown lives HERE and nowhere else.
#     Local print frame: shaft at local origin, plate flat on the bed.
# ============================================================================
PLATE_X0 = SHELF_X0 + 2.0
PLATE_X1 = SHELF_X1 - 6.0
PLATE_Y = SHELF_Y


def make_servo_plate():
    # built in the scope frame then moved to a print frame at the end
    lx0, lx1 = PLATE_X0, PLATE_X1
    p = (cq.Workplane("XY").box(lx1 - lx0, 2 * PLATE_Y, PLATE_T)
         .translate(((lx0 + lx1) / 2, 0, PLATE_Z0 + PLATE_T / 2)))
    # servo body pass-through
    p = p.cut(cq.Workplane("XY").box(SERVO_BODY_L + 1.5, SERVO_BODY_W + 1.5, 20)
              .translate((SERVO_BODY_CX, 0, PLATE_Z0)))
    # servo ear screws
    for sx in (-1, 1):
        for sy in (-1, 1):
            p = p.cut(cq.Workplane("XY")
                      .center(SERVO_BODY_CX + sx * SERVO_HOLE_DX / 2,
                              sy * SERVO_HOLE_DY / 2)
                      .circle(M3_CLEAR / 2).extrude(20)
                      .translate((0, 0, PLATE_Z0 - 5)))
    # slots to the shelf inserts - X adjustment for shaft-offset error
    for ix in INSERT_X:
        for sy in (-1, 1):
            p = p.cut(cq.Workplane("XY").center(ix, sy * INSERT_Y)
                      .slot2D(M3_CLEAR + 8, M3_CLEAR, 0).extrude(20)
                      .translate((0, 0, PLATE_Z0 - 5)))
    p = try_fillet(p, 1.0, "|Z")
    return p


# ============================================================================
# 04  Flat panel tray
#     Rev C fixes: hub gets a shaft/horn-boss clearance bore (Rev B's solid hub
#     left nowhere for the horn's centre screw); the LED wire exit is blind
#     instead of drilled straight through both rim walls; fillet at the arm root.
# ============================================================================
HUB_R = 15.0
HORN_BOSS_D = 10.0        # clearance for the horn's splined boss + centre screw
ARM_W = 24.0


def make_tray():
    t = cq.Workplane("XY").circle(TRAY_R).extrude(TRAY_T)
    # recess opens toward the scope (local +Z here; flipped in the assembly)
    t = t.cut(cq.Workplane("XY").workplane(offset=FLOOR_T)
              .circle(RECESS_D / 2).extrude(TRAY_T))

    arm_len = PIVOT_R - TRAY_R + HUB_R + 12.0
    arm_cx = -(TRAY_R + arm_len / 2 - 12.0)
    arm = (cq.Workplane("XY").box(arm_len, ARM_W, ARM_T)
           .translate((arm_cx, 0, TRAY_T - ARM_T / 2 - 2.0)))
    hub = (cq.Workplane("XY").center(-PIVOT_R, 0).circle(HUB_R).extrude(ARM_T)
           .translate((0, 0, TRAY_T - ARM_T - 2.0)))
    t = t.union(arm).union(hub)

    # horn boss / centre screw access
    t = t.cut(cq.Workplane("XY").center(-PIVOT_R, 0)
              .circle(HORN_BOSS_D / 2).extrude(30)
              .translate((0, 0, TRAY_T - ARM_T - 2.0)))
    # horn screw slots
    for sy in (-7, 7):
        t = t.cut(cq.Workplane("XY").center(-PIVOT_R, sy)
                  .slot2D(12, M3_CLEAR, 0).extrude(30)
                  .translate((0, 0, TRAY_T - ARM_T - 2.0)))

    # retaining-ring inserts
    for ang in (45, 135, 225, 315):
        x = 47 * math.cos(math.radians(ang))
        y = 47 * math.sin(math.radians(ang))
        # from the tray's REAR face (local z=TRAY_T, the face the retainer bolts
        # to) downward.  Rev C bug caught in review: extruding these UP from the
        # recess floor made them fully enclosed internal voids - a valid,
        # watertight, single SOLID whose MESH was 5 disconnected shells.
        t = t.cut(cq.Workplane("XY").center(x, y).circle(M3_INSERT_D / 2)
                  .extrude(-M3_INSERT_L).translate((0, 0, TRAY_T)))

    # LED wire exit: radial hole through the rim at 12 o'clock, well clear of
    # the arm.  Opens into the recess at r=41.2 and out at r=52, so it is a real
    # through-hole, not an enclosed void.
    wire = (cq.Workplane("XY").circle(2.5).extrude(24)
            .rotate((0, 0, 0), (1, 0, 0), -90)
            .translate((0, 36, FLOOR_T + 5.0)))
    t = t.cut(wire)

    # Fillet ONLY the arm-root edges.  Filleting every |Z edge (Rev C draft did)
    # silently produced self-intersecting garbage where the horn slots pass
    # within 0.3 mm of the boss bore.
    root = cq.selectors.BoxSelector((-58, -16, 0), (-42, 16, TRAY_T))
    try:
        t = t.edges("|Z").edges(root).fillet(2.5)
    except Exception as e:
        _warnings.append(f"tray arm-root fillet skipped: {type(e).__name__}")
    return t


def make_retainer():
    r = ring(TRAY_OD, RETAINER_ID, RETAINER_T)
    for ang in (45, 135, 225, 315):
        x = 47 * math.cos(math.radians(ang))
        y = 47 * math.sin(math.radians(ang))
        r = r.cut(cq.Workplane("XY").center(x, y).circle(M3_CLEAR / 2)
                  .extrude(10, both=True))
    return r


# ============================================================================
# 06/07  Electronics enclosure
#        Rev B: box centred on z=0, cut-outs placed as if the floor were z=0.
#        Rev C: floor at z=0.  Every opening height is DERIVED from the board
#        stack, not typed in.
# ============================================================================
BOARD_BOTTOM_Z = FLOOR + STANDOFF_H            # 9.0
BOARD_TOP_Z = BOARD_BOTTOM_Z + PCB_T           # 10.6


def board_to_box(bx, by):
    """KiCad board coords -> box coords.  Board occupies 0..120 x 0..75."""
    return (bx - PCB_X / 2, by - PCB_Y / 2)


def make_enclosure_base():
    b = (cq.Workplane("XY").box(BOX_OUT_X, BOX_OUT_Y, BOX_H)
         .translate((0, 0, BOX_H / 2)))
    b = b.cut(cq.Workplane("XY").box(BOX_IN_X, BOX_IN_Y, BOX_H)
              .translate((0, 0, FLOOR + BOX_H / 2)))

    # DC jacks: J1 x=106, J2 x=84 (board coords), on the board's y=0 edge
    jack_z = BOARD_TOP_Z + DC_JACK_AXIS_Z
    for bx in (84.0, 106.0):
        cx, _ = board_to_box(bx, 0)
        b = b.cut(cq.Workplane("XY").circle(DC_JACK_OPENING_D / 2).extrude(24)
                  .rotate((0, 0, 0), (1, 0, 0), 90)
                  .translate((cx, -BOX_OUT_Y / 2 - 2, jack_z)))
    # USB-C: J8 x=16, on the board's y=75 edge
    cx, _ = board_to_box(16.0, 0)
    b = b.cut(cq.Workplane("XZ").workplane(offset=BOX_OUT_Y / 2 + 1)
              .center(cx, BOARD_TOP_Z + 3.3 / 2 + 0.5).rect(13, 8)
              .extrude(-(2 * WALL + 4)))
    # field harness: J3..J7 sit at board y = 29..70 -> box y = -8.5..+33.
    # Rev C draft had this centred on y=0 and 46 wide, which missed the top third.
    b = b.cut(cq.Workplane("XY").box(2 * WALL + 8, 50, 15)
              .translate((BOX_OUT_X / 2, 12, BOARD_TOP_Z + 7.5)))
    # centre pillar: halves the lintel bridge to 23 mm, cables pass either side
    b = b.union(cq.Workplane("XY").box(2 * WALL, 4, 15)
                .translate((BOX_OUT_X / 2 - WALL / 2, 12, BOARD_TOP_Z + 7.5)))

    # standoffs - grown FROM the floor, not floating above it
    for bx, by in PCB_HOLES:
        cx, cy = board_to_box(bx, by)
        b = b.union(cq.Workplane("XY").center(cx, cy)
                    .circle(STANDOFF_OD / 2).extrude(BOARD_BOTTOM_Z))
        b = b.cut(cq.Workplane("XY").center(cx, cy)
                  .circle(STANDOFF_PILOT / 2)
                  .extrude(BOARD_BOTTOM_Z + 1))

    # lid bosses on the outer corners, full height, welded into the wall corner
    for sx in (-1, 1):
        for sy in (-1, 1):
            b = b.union(cq.Workplane("XY").center(sx * BOSS_CX, sy * BOSS_CY)
                        .circle(BOSS_R).extrude(BOX_H))
    # ...then bore them, after the union, so the bores survive
    for sx in (-1, 1):
        for sy in (-1, 1):
            b = b.cut(cq.Workplane("XY").workplane(offset=BOX_H)
                      .center(sx * BOSS_CX, sy * BOSS_CY)
                      .circle(M3_INSERT_D / 2).extrude(-(M3_INSERT_L + 1.5)))

    # Strap tabs: flat ears at the bottom of each long face with a vertical
    # through-slot.  Thread the strap down through one ear, under the dovetail
    # bar, up through the other.  The ears interpenetrate the wall by 1 mm - a
    # union of two solids that merely TOUCH is degenerate and exports a
    # non-watertight mesh (this is how Rev B's switch bracket broke).
    for sy in (-1, 1):
        for sx in (-1, 1):
            tab_cy = sy * (BOX_OUT_Y / 2 + 3.0)
            slot_cy = sy * (BOX_OUT_Y / 2 + 3.5)
            b = b.union(cq.Workplane("XY").center(sx * 34.0, tab_cy)
                        .box(STRAP_W + 8, 8.0, 4.0).translate((0, 0, 2.0)))
            b = b.cut(cq.Workplane("XY").center(sx * 34.0, slot_cy)
                      .box(STRAP_W, STRAP_T, 12.0).translate((0, 0, 2.0)))
    return b


def make_enclosure_lid():
    """Screwed, not friction-fit.  Modelled lip-down at z=0..LID_T+4, exported
    as-is: it prints face-down on the bed with the lip in the air, no support."""
    lid = (cq.Workplane("XY").box(BOX_OUT_X, BOX_OUT_Y, LID_T)
           .translate((0, 0, LID_T / 2)))
    # matching corner tabs, so the screws land on the base's bosses
    for sx in (-1, 1):
        for sy in (-1, 1):
            lid = lid.union(cq.Workplane("XY").center(sx * BOSS_CX, sy * BOSS_CY)
                            .circle(BOSS_R).extrude(LID_T))
    # spigot lip, 0.4 mm undersize on the cavity: locates the lid and gives a
    # labyrinth path for dew.  Sits inboard of the corner bosses.
    lip_o = (cq.Workplane("XY")
             .box(BOX_IN_X - 0.4, BOX_IN_Y - 0.4, 4.0)
             .translate((0, 0, LID_T + 2.0)))
    lip_i = (cq.Workplane("XY")
             .box(BOX_IN_X - 0.4 - 4.0, BOX_IN_Y - 0.4 - 4.0, 6.0)
             .translate((0, 0, LID_T + 2.0)))
    lip = lip_o.cut(lip_i)
    # The base's corner bosses eat ~1.7 mm diagonally into each cavity corner,
    # so the lip must be notched around them or the lid will not seat.
    for sx in (-1, 1):
        for sy in (-1, 1):
            lip = lip.cut(cq.Workplane("XY").workplane(offset=LID_T - 0.5)
                          .center(sx * BOSS_CX, sy * BOSS_CY)
                          .circle(BOSS_R + 0.4).extrude(6.0))
    lid = lid.union(lip)
    # M3 clearance, counterbored so the cap head sits flush
    for sx in (-1, 1):
        for sy in (-1, 1):
            lid = lid.cut(cq.Workplane("XY").center(sx * BOSS_CX, sy * BOSS_CY)
                          .circle(M3_CLEAR / 2).extrude(LID_T + 8))
            lid = lid.cut(cq.Workplane("XY").center(sx * BOSS_CX, sy * BOSS_CY)
                          .circle(6.2 / 2).extrude(1.8))
    return lid


# ============================================================================
# 08  Limit switch bracket (print two)
# ============================================================================
def make_switch_bracket():
    # Rev B / Rev C draft bug: base and upright met on a single plane with zero
    # overlap -> a degenerate union that exported a non-watertight mesh.
    # They now interpenetrate by 3 mm.
    s = cq.Workplane("XY").box(24, 16, 3).translate((0, 0, 1.5))
    s = s.union(cq.Workplane("XY").box(24, 3, 20).translate((0, 6.5, 10)))
    for x in (-7, 7):
        s = s.cut(cq.Workplane("XY").center(x, 0).slot2D(7, M3_CLEAR, 90)
                  .extrude(10, both=True))
    for x in (-4.75, 4.75):
        s = s.cut(cq.Workplane("XY").circle(1.3).extrude(20)
                  .rotate((0, 0, 0), (1, 0, 0), -90)
                  .translate((x, -4, 13)))
    return s


# ============================================================================
# 09 / 10  Verification coupons for the two parameters I cannot check for you
# ============================================================================
def make_shaft_gauge():
    """Drops over the servo's ears; the notch marks where the shaft should be.
    If the shaft is not centred in the notch, SERVO_SHAFT_OFFSET is wrong."""
    g = cq.Workplane("XY").box(SERVO_HOLE_DX + 16, 30, 4).translate((0, 0, 2))
    g = g.cut(cq.Workplane("XY").box(SERVO_BODY_L + 1.5, SERVO_BODY_W + 1.5, 10)
              .translate((0, 0, 3)))
    for sx in (-1, 1):
        for sy in (-1, 1):
            g = g.cut(cq.Workplane("XY")
                      .center(sx * SERVO_HOLE_DX / 2, sy * SERVO_HOLE_DY / 2)
                      .circle(M3_CLEAR / 2).extrude(20))
    # witness notch at the nominal shaft position
    g = g.cut(cq.Workplane("XY").center(-SERVO_SHAFT_OFFSET, 12)
              .box(1.2, 8, 10).translate((0, 0, 3)))
    return g


def make_connector_coupon():
    """A 6 mm slice of the connector wall. Offer it up to the assembled PCB
    before committing 6 hours to the full enclosure."""
    c = (cq.Workplane("XY").box(60, WALL, BOX_H)
         .translate((0, 0, BOX_H / 2)))
    jack_z = BOARD_TOP_Z + DC_JACK_AXIS_Z
    for bx in (84.0, 106.0):
        cx, _ = board_to_box(bx, 0)
        c = c.cut(cq.Workplane("XY").circle(DC_JACK_OPENING_D / 2).extrude(24)
                  .rotate((0, 0, 0), (1, 0, 0), 90)
                  .translate((cx - board_to_box(95.0, 0)[0], -12, jack_z)))
    # floor + one standoff, so the coupon sits at the true board height
    c = c.union(cq.Workplane("XY").box(60, 12, FLOOR)
                .translate((0, WALL / 2 + 6, FLOOR / 2)))
    c = c.union(cq.Workplane("XY").center(0, 8).circle(STANDOFF_OD / 2)
                .extrude(BOARD_BOTTOM_Z))
    return c


# ============================================================================
# CLEARANCE CHECKS - the thing Rev B never did
# ============================================================================
def check_clearances():
    ok = True
    msg = []

    def chk(name, value, lo=None, hi=None, unit="mm"):
        nonlocal ok
        good = True
        if lo is not None and value < lo:
            good = False
        if hi is not None and value > hi:
            good = False
        ok = ok and good
        msg.append(f"  [{'PASS' if good else 'FAIL'}] {name:52s} {value:8.2f} {unit}")

    # servo body vs clamp OD
    body_near_x = SERVO_BODY_CX + SERVO_BODY_L / 2
    chk("servo body -> clamp OD clearance", -body_near_x - CLAMP_R, lo=3.0)
    # servo body vs closed tray rim
    chk("servo body -> closed tray rim clearance", -body_near_x - TRAY_R, lo=3.0)
    # hub vs clamp (they are at different Z, but check anyway)
    chk("hub outer -> clamp OD (XY only)", (PIVOT_R - HUB_R) - CLAMP_R, lo=0.0)
    # tray closed: rear face vs dew shield rim
    chk("closed diffuser -> dew shield rim", RETAINER_Z0 - CLAMP_H, lo=2.5)
    # arm sits inside the tray's Z band
    chk("arm bottom above tray rear face", ARM_Z0 - TRAY_Z0, lo=0.0)
    chk("tray front face above arm top", TRAY_Z1 - ARM_Z1, lo=0.0)
    # servo top face is below the tray front
    chk("servo top face -> tray front face", TRAY_Z1 - SERVO_TOP_Z, lo=0.0)
    # open swing: how close does the tray get to the optical axis?
    th = math.radians(OPEN_ANGLE_DEG)
    cx = -PIVOT_R + PIVOT_R * math.cos(th)
    cy = PIVOT_R * math.sin(th)
    d = math.hypot(cx, cy)
    chk("open tray edge -> optical axis", d - TRAY_R, lo=SCOPE_DIAMETER / 2 - 40 + 8.0)
    chk("open tray swept radius from axis", d + TRAY_R, hi=200.0)
    # enclosure
    chk("box internal height above board top", BOX_H - BOARD_TOP_Z, lo=MAX_COMPONENT_H + 2)
    chk("jack opening top vs box height", BOARD_TOP_Z + DC_JACK_AXIS_Z + DC_JACK_OPENING_D / 2,
        hi=BOX_H - 2.0)
    chk("jack opening bottom vs floor", BOARD_TOP_Z + DC_JACK_AXIS_Z - DC_JACK_OPENING_D / 2,
        lo=FLOOR + 0.5)
    chk("board fits box in X", BOX_IN_X - PCB_X, lo=2.0)
    chk("board fits box in Y", BOX_IN_Y - PCB_Y, lo=2.0)
    # the lid bosses sit on the corners and intrude diagonally into the cavity;
    # prove they miss the board corner before trusting them
    board_corner = math.hypot(BOSS_CX - PCB_X / 2, BOSS_CY - PCB_Y / 2)
    chk("corner boss -> PCB corner", board_corner - BOSS_R, lo=1.0)
    chk("boss insert bore -> boss wall", (BOSS_R - M3_INSERT_D / 2), lo=1.5)
    chk("lid screw thread engagement", BOX_H - M3_INSERT_L, lo=5.0)
    # strap ears must not foul the connector openings (they are at z<=4, the
    # openings start at the board top - this is the number that proves it)
    chk("strap ear top -> lowest connector opening",
        (BOARD_TOP_Z + DC_JACK_AXIS_Z - DC_JACK_OPENING_D / 2) - 4.0, lo=1.0)
    # panel optical sanity: emitting disc vs required cone at the shield rim
    half_field = math.radians(3.25)          # ~APS-C on 250 mm
    L = RETAINER_Z0 + 68.0                   # panel -> objective, shield ~68 mm
    need = 51.0 + 2 * L * math.tan(half_field)
    chk("emitting aperture vs required disc", RETAINER_ID - need, lo=0.0)

    print("\n".join(msg))
    return ok


# ============================================================================
# ASSEMBLY  - parts placed in the scope frame
# ============================================================================
def build_assembly(clamp, plate, tray, retainer):
    a = cq.Assembly()
    a.add(clamp, name="clamp", color=cq.Color(0.75, 0.15, 0.15))
    a.add(plate, name="servo_plate", color=cq.Color(0.3, 0.3, 0.35))
    # tray: modelled recess-up, flipped so the recess faces the scope
    tray_placed = (tray.rotate((0, 0, 0), (1, 0, 0), 180)
                   .translate((0, 0, TRAY_Z1)))
    a.add(tray_placed, name="tray", color=cq.Color(0.85, 0.85, 0.85))
    ret_placed = retainer.translate((0, 0, RETAINER_Z0))
    a.add(ret_placed, name="retainer", color=cq.Color(0.2, 0.2, 0.2))
    # servo stand-in so the collision is visible
    servo = (cq.Workplane("XY")
             .box(SERVO_BODY_L, SERVO_BODY_W, SERVO_BODY_H)
             .translate((SERVO_BODY_CX, 0, SERVO_TOP_Z - SERVO_BODY_H / 2)))
    servo = servo.union(cq.Workplane("XY").center(-PIVOT_R, 0).circle(3)
                        .extrude(6).translate((0, 0, SERVO_TOP_Z)))
    a.add(servo, name="servo_envelope", color=cq.Color(0.1, 0.1, 0.1))
    # scope stand-in
    scope = (cq.Workplane("XY").circle(SCOPE_DIAMETER / 2).extrude(CLAMP_H + 6)
             .translate((0, 0, -3)))
    a.add(scope, name="dew_shield_envelope", color=cq.Color(0.5, 0.5, 0.55))
    return a


def main():
    print(f"RedCat 51 II flat panel - Rev C mechanical")
    print(f"  SCOPE_DIAMETER      = {SCOPE_DIAMETER:.2f}  -> CLAMP_ID = {CLAMP_ID:.2f}")
    print(f"  SERVO_SHAFT_OFFSET  = {SERVO_SHAFT_OFFSET:.2f}")
    print(f"  SERVO_EAR_TO_TOP    = {SERVO_EAR_TO_TOP:.2f}  -> horn at Z = {SERVO_TOP_Z:.2f}")
    print(f"  DC_JACK_AXIS_Z      = {DC_JACK_AXIS_Z:.2f}")
    print(f"  PIVOT_R             = {PIVOT_R:.2f}")
    print()

    clamp = make_clamp()
    plate = make_servo_plate()
    tray = make_tray()
    retainer = make_retainer()

    save("01-diameter-fit-gauge", make_fit_gauge())
    save("02-scope-clamp", clamp.translate((0, 0, 0)))
    # plate exported flat on the bed for printing
    save("03-ds3218-servo-plate", plate.translate((-SERVO_BODY_CX, 0, -PLATE_Z0)))
    save("04-flat-panel-tray", tray)
    save("05-diffuser-retaining-ring", retainer)
    save("06-electronics-enclosure-base", make_enclosure_base())
    save("07-electronics-enclosure-lid", make_enclosure_lid())
    save("08-limit-switch-bracket-print-two", make_switch_bracket())
    save("09-servo-shaft-gauge", make_shaft_gauge())
    save("10-connector-wall-coupon", make_connector_coupon())

    print("Clearance checks:")
    ok = check_clearances()

    asm = build_assembly(clamp, plate, tray, retainer)
    asm.save(str(OUT / "00-ASSEMBLY.step"))
    print(f"\nassembly -> 00-ASSEMBLY.step")

    if _warnings:
        print("\nWarnings:")
        for w in _warnings:
            print("  " + w)
    print(f"\nOverall: {'ALL CLEARANCE CHECKS PASS' if ok else '*** CLEARANCE CHECK FAILED ***'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
