# FLOW-23 (COORD 11-02 23:0x, GEOM-111 class D): SOFT region guides for datapath spread inside one cloud.
# GENERATED into the kit by tools/die_plan/region_guide.py install (opt-in --region-guide); sourced at the END of the
# PRE_GLOBAL_PLACE hook face_flops.tcl.  region_guide.tsv beside this file: "R name x0 y0 x1 y1" (um, die coords) +
# "I name instance" rows (exact ODB instance names of the launch/capture registers of one or more bit slices whose
# AUTO-GEOM r2r exceeded the reach).  Each region becomes an INCLUSIVE dbRegion + dbGroup (the macro_reg_guide.tcl /
# r2a_fences.tcl form) for global placement only; region_guide_release.tcl removes them before detailed placement.
# Never guided: FIRM/LOCKED instances (face_flops.tcl pins face / IO registers FIRM), non-core masters (macros),
# instances already in a group (another guide owns them).  Missing instances are reported and skipped (soft guide);
# a region over 0.80 movable+fixed fill is skipped with a warning; no instance matched at all is an error (the option
# was requested but would do nothing).
set ::rg_dir [file dirname [file normalize [info script]]]
uplevel #0 {
set rg_blk [ord::get_db_block]
set rg_u [[ord::get_db_tech] getDbUnitsPerMicron]
set rg_fh [open [file join $::rg_dir region_guide.tsv] r]
set rg_boxes [dict create]; set rg_members [dict create]; set rg_order {}
foreach rg_ln [split [read $rg_fh] "\n"] {
  if {$rg_ln eq ""} continue
  set rg_f [split $rg_ln "\t"]
  if {[lindex $rg_f 0] eq "R"} {
    dict set rg_boxes [lindex $rg_f 1] [lrange $rg_f 2 5]; lappend rg_order [lindex $rg_f 1]
  } elseif {[lindex $rg_f 0] eq "I"} {
    dict lappend rg_members [lindex $rg_f 1] [lindex $rg_f 2]
  }
}
close $rg_fh
set rg_n 0; set rg_cells 0; set rg_miss 0; set rg_skip 0
foreach rg_nm $rg_order {
  lassign [dict get $rg_boxes $rg_nm] zx0 zy0 zx1 zy1
  set rg_insts {}; set rg_area 0.0
  foreach rg_in [expr {[dict exists $rg_members $rg_nm] ? [dict get $rg_members $rg_nm] : {}}] {
    set i [$rg_blk findInst $rg_in]
    if {$i eq "NULL" || $i eq ""} { incr rg_miss; continue }
    if {![[$i getMaster] isCore] || [$i getPlacementStatus] in {FIRM LOCKED COVER}} { incr rg_skip; continue }
    if {[$i getGroup] ne "NULL" && [$i getGroup] ne ""} { incr rg_skip; continue }
    lappend rg_insts $i
    set rg_area [expr {$rg_area + double([[$i getMaster] getWidth]) * [[$i getMaster] getHeight] / $rg_u / $rg_u}]
  }
  if {[llength $rg_insts] == 0} { puts "OT_REGION_GUIDE $rg_nm: no guidable instance (skipped)"; continue }
  # A GPL region needs enough cells to spread: 2 cells in 64 um2 ended GPL-0307 on leaf t32. A few cells are not a guide anyway.
  if {[llength $rg_insts] < 20} { puts "OT_REGION_GUIDE $rg_nm: [llength $rg_insts] cells < 20 (skipped)"; set rg_small 1; continue }
  set rg_fixed 0.0
  foreach fi [$rg_blk getInsts] {
    if {[$fi getPlacementStatus] ni {FIRM LOCKED}} continue
    set bb [$fi getBBox]
    set ix0 [expr {max($zx0, double([$bb xMin])/$rg_u)}]; set iy0 [expr {max($zy0, double([$bb yMin])/$rg_u)}]
    set ix1 [expr {min($zx1, double([$bb xMax])/$rg_u)}]; set iy1 [expr {min($zy1, double([$bb yMax])/$rg_u)}]
    if {$ix1 > $ix0 && $iy1 > $iy0} { set rg_fixed [expr {$rg_fixed + ($ix1-$ix0)*($iy1-$iy0)}] }
  }
  set rg_fill [expr {($rg_area + $rg_fixed) / (($zx1-$zx0)*($zy1-$zy0))}]
  if {$rg_fill >= 0.80} { puts "OT_REGION_GUIDE_WARN $rg_nm: movable+fixed fill $rg_fill >= 0.80 (skipped)"; continue }
  set reg [odb::dbRegion_create $rg_blk $rg_nm]
  $reg setRegionType INCLUSIVE
  odb::dbBox_create $reg [expr {round($zx0*$rg_u)}] [expr {round($zy0*$rg_u)}] [expr {round($zx1*$rg_u)}] [expr {round($zy1*$rg_u)}]
  set g [odb::dbGroup_create $reg $rg_nm]
  $g setType VOLTAGE_DOMAIN
  foreach i $rg_insts { $g addInst $i }
  puts [format "OT_REGION_GUIDE %s cells %d area %.1f um2 box %.2f %.2f %.2f %.2f fixed %.0f fill %.3f" \
        $rg_nm [llength $rg_insts] $rg_area $zx0 $zy0 $zx1 $zy1 $rg_fixed $rg_fill]
  incr rg_n; incr rg_cells [llength $rg_insts]
}
puts "OT_REGION_GUIDE $rg_n guides $rg_cells cells (missing $rg_miss, fixed/grouped skipped $rg_skip; GPL guide, released before DPL)"
# KW-FIX-23: instances found but all FIRM/grouped (e.g. OT_CLAND band cells) = no-op guide, not stale.
if {$rg_cells == 0 && $rg_skip == 0 && ![info exists rg_small]} { error "OT_REGION_GUIDE: no spec instance matched the design (stale guide)" }
}
