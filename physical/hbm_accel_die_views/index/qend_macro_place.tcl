# el1011-hbm-idx 2026-10-11 ~19:10: deliberate macro floorplan of hfd_idx_sel_native_qend (1399.66 x 844.56).
# RTLMP (cl4) scattered the 28 SRAMs and parked gm[1].m[1] 0.6 um under the north pin face (macro_edge, 380 pins
# behind it) and four macros on the south face.  Pin faces (native_clock32 contract): N/S pins in x 583..817,
# E/W pins in y 351..493 -> those two centre corridors stay macro-free.  Each lane i (gc[i] 1024x256, gm[i].m[0..2]
# 256x256, gl[i].g_tile[0..2] 128x256 FWFT FIFO) owns one corner quadrant: column A = gc + 3 gm stacked, column B =
# 3 gl stacked, >= 20.16-um channels between macros and to the core edge; origins on the 8.64-um grid (site/track
# common multiple).  Quadrants: lane 0 SW, 1 SE, 2 NW, 3 NE; north/east quadrants mirrored so pins face the centre.
set G 8.64
set block [ord::get_db_block]
set die [$block getDieArea]
set W [ord::dbu_to_microns [$die xMax]]
set H [ord::dbu_to_microns [$die yMax]]
proc idx_of {name tag} { if {[regexp [format {%s\\?\[(\d+)\\?\]} $tag] $name -> i]} { return $i }; return -1 }
# column A: gc at y 3G, gm j at y (14 + 8j)G; column B x 26G: gl j at y (3 + 8j)G
foreach inst [$block getInsts] {
  set m [[$inst getMaster] getName]
  if {![string match ot_sram_* $m]} { continue }
  set n [$inst getName]
  set mw [ord::dbu_to_microns [[$inst getMaster] getWidth]]
  set mh [ord::dbu_to_microns [[$inst getMaster] getHeight]]
  if {[regexp {(^|\.)gc\\?\[} $n]} {
    set q [idx_of $n gc]; set x [expr {3 * $G}]; set y [expr {3 * $G}]
  } elseif {[regexp {(^|\.)gm\\?\[} $n]} {
    set q [idx_of $n gm]; set j -1; regexp {\.m\\?\[(\d+)} $n -> j; set x [expr {3 * $G}]; set y [expr {(14 + 8 * $j) * $G}]
  } elseif {[regexp {(^|\.)gl\\?\[} $n]} {
    set q [idx_of $n gl]; set j [idx_of $n g_tile]; set x [expr {26 * $G}]; set y [expr {(3 + 8 * $j) * $G}]
  } else {
    error "qend_macro_place: unplanned macro $n ($m)"
  }
  if {$q < 0 || $q > 3} { error "qend_macro_place: bad lane index in $n" }
  set east [expr {$q % 2}]; set north [expr {$q / 2}]
  set o R0
  if {$east} { set x [expr {floor(($W - $x - $mw) / $G) * $G}]; set o MY }
  if {$north} { set y [expr {floor(($H - $y - $mh) / $G) * $G}]; set o [expr {$east ? "R180" : "MX"}] }
  place_macro -macro_name $n -location [list $x $y] -orientation $o
}
