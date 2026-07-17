from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
WORK = HERE.parents[1]
sys.path.insert(0, str(WORK / "python_deps"))
import cadquery as cq
from cadquery import exporters

# Edit this after measuring the RedCat 51 II dew shield with calipers.
SCOPE_DIAMETER = 80.0
LINER_THICKNESS = 0.8
FIT_CLEARANCE = 0.5
CLAMP_ID = SCOPE_DIAMETER + 2 * LINER_THICKNESS + FIT_CLEARANCE

def save(name, solid):
    exporters.export(solid, str(HERE / f"{name}.stl"), tolerance=0.08, angularTolerance=0.15)
    exporters.export(solid, str(HERE / f"{name}.step"))

def ring(outer_d, inner_d, height):
    return cq.Workplane("XY").circle(outer_d/2).circle(inner_d/2).extrude(height)

# 1) A short fit gauge avoids wasting a full clamp print if the real scope diameter differs.
fit_gauge = ring(CLAMP_ID + 7, CLAMP_ID, 8).cut(
    cq.Workplane("XY").box(8, CLAMP_ID + 14, 12).translate((0, CLAMP_ID/2, 4))
)
save("01-diameter-fit-gauge", fit_gauge)

# 2) Split front clamp with M4 compression ears and servo-platform screw holes.
clamp = ring(CLAMP_ID + 12, CLAMP_ID, 24)
clamp = clamp.cut(cq.Workplane("XY").box(6, CLAMP_ID + 20, 30).translate((0, CLAMP_ID/2, 12)))
ear_y = CLAMP_ID/2 + 5
left_ear = cq.Workplane("XY").box(7, 15, 24).translate((-6.5, ear_y, 12))
right_ear = cq.Workplane("XY").box(7, 15, 24).translate((6.5, ear_y, 12))
clamp = clamp.union(left_ear).union(right_ear)
clamp = clamp.cut(cq.Workplane("YZ").workplane(offset=-13).center(ear_y, 12).circle(2.2).extrude(26))
# Tangential platform for the servo plate, with four M3 heat-set insert holes.
platform_x = -(CLAMP_ID/2 + 34)
platform = cq.Workplane("XY").box(58, 38, 5).translate((platform_x, 0, 21.5))
clamp = clamp.union(platform)
for dx in (-23, 23):
    for dy in (-13, 13):
        clamp = clamp.cut(cq.Workplane("XY").workplane(offset=18).center(platform_x+dx, dy).circle(2.1).extrude(8))
save("02-scope-clamp", clamp)

# 3) DS3218 servo plate. Servo pushes through the rectangular opening; stock ears take M3 screws.
servo_plate = cq.Workplane("XY").box(58, 38, 4)
servo_plate = servo_plate.cut(cq.Workplane("XY").box(41.5, 21.5, 8))
for x in (-24.5, 24.5):
    for y in (-5, 5):
        servo_plate = servo_plate.cut(cq.Workplane("XY").center(x, y).circle(1.7).extrude(8, both=True))
for x in (-23, 23):
    for y in (-13, 13):
        servo_plate = servo_plate.cut(cq.Workplane("XY").center(x, y).circle(1.7).extrude(8, both=True))
save("03-ds3218-servo-plate", servo_plate)

# 4) Flat-panel tray. Accepts an 82 mm circular stack: reflector, 3 mm LGP and diffuser.
panel_od = 104
recess_d = 82.4
tray = cq.Workplane("XY").circle(panel_od/2).extrude(14)
tray = tray.cut(cq.Workplane("XY").workplane(offset=3).circle(recess_d/2).extrude(12))
# Arm reaches a pivot 70 mm from the optical centre.
arm = cq.Workplane("XY").box(48, 24, 5).translate((-64, 0, 11.5))
hub = cq.Workplane("XY").center(-72, 0).circle(15).extrude(5).translate((0,0,9))
tray = tray.union(arm).union(hub)
# Four M3 heat-set insert bores for the diffuser retaining ring.
import math
for angle in (45, 135, 225, 315):
    x = 47 * math.cos(math.radians(angle))
    y = 47 * math.sin(math.radians(angle))
    tray = tray.cut(cq.Workplane("XY").workplane(offset=8).center(x,y).circle(2.1).extrude(7))
# Stock 25T metal horn bolts through two adjustable slots.
for y in (-7, 7):
    slot = cq.Workplane("XY").workplane(offset=8).center(-72, y).slot2D(12, 3.4, 0).extrude(8)
    tray = tray.cut(slot)
# LED wire exit.
tray = tray.cut(cq.Workplane("XZ").workplane(offset=0).center(-40, 7).circle(2.5).extrude(60, both=True))
save("04-flat-panel-tray", tray)

# 5) Front retaining ring for the diffuser; four M3 screws into heat-set inserts in the tray rim.
retainer = ring(panel_od, 74, 2.8)
for angle in (45, 135, 225, 315):
    x = 47 * math.cos(math.radians(angle))
    y = 47 * math.sin(math.radians(angle))
    retainer = retainer.cut(cq.Workplane("XY").center(x,y).circle(1.7).extrude(6, both=True))
save("05-diffuser-retaining-ring", retainer)

# 6) Electronics box for the 120 x 75 mm integrated PCBA.
# Board coordinate origin is translated to the box centre (60, 37.5).
outer_x, outer_y, base_h, wall = 130, 85, 29, 2.6
base = cq.Workplane("XY").box(outer_x, outer_y, base_h)
base = base.cut(cq.Workplane("XY").workplane(offset=3).box(outer_x-2*wall, outer_y-2*wall, base_h))
# Two 5.5 mm barrel-jack nose openings on the board's top edge.
for x in (24, 46):
    base = base.cut(cq.Workplane("XZ").workplane(offset=-outer_y/2).center(x, 12).circle(4.6).extrude(8, both=True))
# USB-C service opening on the opposite long wall.
base = base.cut(cq.Workplane("XZ").workplane(offset=outer_y/2).center(-44, 7).rect(12, 7).extrude(8, both=True))
# One generous harness opening for LED, servo, two limits and remote button.
base = base.cut(cq.Workplane("YZ").workplane(offset=outer_x/2).center(11, 12).rect(40, 15).extrude(8, both=True))
# PCB standoffs and M3 holes, exactly matching the integrated-board holes.
for x,y in [(-20,-33.5),(56,-33.5),(-20,33.5),(56,33.5)]:
    post = cq.Workplane("XY").center(x,y).circle(3.8).extrude(7)
    base = base.union(post)
    base = base.cut(cq.Workplane("XY").center(x,y).circle(1.35).extrude(10))
save("06-electronics-enclosure-base", base)

# 7) Friction-fit lid. Four external corner lugs make removal tool-free.
lid = cq.Workplane("XY").box(outer_x, outer_y, 3)
lip = ring(1, 0.5, 1)  # placeholder to start a compound-free lip below
lip = cq.Workplane("XY").box(outer_x-2*wall-0.5, outer_y-2*wall-0.5, 4)
lip = lip.cut(cq.Workplane("XY").box(outer_x-4*wall, outer_y-4*wall, 5))
lid = lid.union(lip.translate((0,0,-2)))
for x in (-outer_x/2+8, outer_x/2-8):
    lid = lid.union(cq.Workplane("XY").center(x,0).box(8,18,2).translate((0,0,1)))
save("07-electronics-enclosure-lid", lid)

# 8) Adjustable KW12-3 microswitch bracket. Print two; stack under servo-plate screws.
switch_bracket = cq.Workplane("XY").box(24, 16, 3)
vertical = cq.Workplane("XZ").box(24, 18, 3).translate((0, 8, 9))
switch_bracket = switch_bracket.union(vertical)
for x in (-7, 7):
    switch_bracket = switch_bracket.cut(cq.Workplane("XY").center(x,0).slot2D(7,3.4,90).extrude(8,both=True))
for x in (-4.75,4.75):
    switch_bracket = switch_bracket.cut(cq.Workplane("XZ").workplane(offset=6.5).center(x,9).circle(1.3).extrude(6,both=True))
save("08-limit-switch-bracket-print-two", switch_bracket)

print(f"Generated parts with SCOPE_DIAMETER={SCOPE_DIAMETER:.2f} mm, CLAMP_ID={CLAMP_ID:.2f} mm")
