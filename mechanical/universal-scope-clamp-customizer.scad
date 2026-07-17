/* Universal flat-panel scope clamp - OpenSCAD Customizer source.
   Measure the actual tube/dew-shield OD with calipers before printing. */

scope_diameter = 80.0;      // [45:0.1:180]
liner_thickness = 0.8;      // [0:0.1:3]
fit_clearance = 0.5;        // [0.2:0.1:1.5]
clamp_width = 24;           // [16:1:35]
wall_thickness = 6;         // [4:0.5:10]
platform_width = 58;
platform_depth = 38;
platform_thickness = 5;
insert_hole = 4.2;          // M3 heat-set insert pilot

$fn = 128;
clamp_id = scope_diameter + 2*liner_thickness + fit_clearance;
clamp_od = clamp_id + 2*wall_thickness;
platform_x = -(clamp_id/2 + 34);

module split_clamp() {
    difference() {
        union() {
            difference() {
                cylinder(d=clamp_od, h=clamp_width);
                translate([0,0,-1]) cylinder(d=clamp_id, h=clamp_width+2);
                translate([-3,clamp_id/2,-1]) cube([6,wall_thickness+12,clamp_width+2]);
            }
            translate([-10,clamp_id/2+1,0]) cube([7,15,clamp_width]);
            translate([3,clamp_id/2+1,0]) cube([7,15,clamp_width]);
            translate([platform_x-platform_width/2,-platform_depth/2,clamp_width-5])
                cube([platform_width,platform_depth,platform_thickness]);
            // tether eye
            translate([platform_x-30,14,clamp_width-5])
                difference(){ cylinder(d=14,h=5); translate([0,0,-1]) cylinder(d=6,h=7); }
        }
        // M4 clamp bolt
        translate([-20,clamp_id/2+8,clamp_width/2]) rotate([0,90,0]) cylinder(d=4.4,h=40);
        // servo-platform inserts
        for (x=[-23,23], y=[-13,13])
            translate([platform_x+x,y,clamp_width-7]) cylinder(d=insert_hole,h=9);
    }
}

split_clamp();
