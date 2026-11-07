# Existing face_flops.tcl API, no tiny inclusive GPL regions.
# Caller sets hm_targets = { {exact_normalized_inst x0 y0 x1 y1} ... } (um), hm_expected and hm_macro_halo_um.
uplevel #0 {
foreach v {ff_blk ff_dbu ff_cpitch ff_rh hm_targets hm_expected hm_macro_halo_um} {if {![info exists $v]} {error "HOP_FIRM missing $v"}}
if {![llength [info commands ff_put_near]] || ![llength [info commands ff_reserve_explicit]]} {error "HOP_FIRM requires existing face placement APIs"}
set hm_map [dict create]
foreach i [$ff_blk getInsts] {dict set hm_map [string map {\\ {}} [$i getName]] $i}
set hm_owned [dict create]
foreach row $hm_targets {dict set hm_owned [lindex $row 0] 1}
# Reserve native fixed footprints and explicit macro halo before the existing grid allocator runs.
foreach i [$ff_blk getInsts] {
  if {[dict exists $hm_owned [string map {\\ {}} [$i getName]]]} continue
  set m [$i getMaster]
  if {[$m isBlock] || [$i getPlacementStatus] in {FIRM FIXED LOCKED COVER}} {
    set b [$i getBBox];set grow [expr {[$m isBlock] ? round($hm_macro_halo_um*$ff_dbu) : 0}]
    ff_reserve_explicit [expr {[$b xMin]-$grow}] [expr {[$b yMin]-$grow}] [expr {[$b xMax]-[$b xMin]+2*$grow}] [expr {[$b yMax]-[$b yMin]+2*$grow}]
  }
}
foreach b [$ff_blk getBlockages] {
  if {[$b isSoft] || [$b getMaxDensity]>0} continue
  set bb [$b getBBox]
  ff_reserve_explicit [$bb xMin] [$bb yMin] [expr {[$bb xMax]-[$bb xMin]}] [expr {[$bb yMax]-[$bb yMin]}]
}
set hm_n 0
set hm_out [open $::env(RESULTS_DIR)/ot_face_flops.txt a]
foreach row $hm_targets {
  lassign $row name x0 y0 x1 y1
  if {![dict exists $hm_map $name]} {error "HOP_FIRM missing actual $name"}
  set i [dict get $hm_map $name];set m [$i getMaster]
  if {![ff_is_ff $i] || [$m getWidth]>$ff_cpitch || [$m getHeight]>$ff_rh} {error "HOP_FIRM unexpected FF footprint $name"}
  set px [expr {round(($x0+$x1)*0.5*$ff_dbu-[$m getWidth]*0.5)}]
  set py [expr {round(($y0+$y1)*0.5*$ff_dbu-[$m getHeight]*0.5)}]
  set got [ff_put_near $i $px $py]
  if {$got eq ""} {error "HOP_FIRM no free legal grid site $name"}
  lassign $got x y
  if {$x<$x0*$ff_dbu-1 || $y<$y0*$ff_dbu-1 || $x+[$m getWidth]>$x1*$ff_dbu+1 || $y+[$m getHeight]>$y1*$ff_dbu+1} {error "HOP_FIRM site escaped checked reach box $name"}
  ff_reserve_explicit $x $y [$m getWidth] [$m getHeight]
  puts $hm_out "[$i getName]\thop_mid\t[expr {$x/double($ff_dbu)}]\t[expr {$y/double($ff_dbu)}]\tchecked405"
  incr hm_n
}
close $hm_out
if {$hm_n!=$hm_expected} {error "HOP_FIRM expected $hm_expected placed $hm_n"}
puts "HOP_FIRM placed $hm_n on existing grid; FIRM during GPL; default face release before DPL; PIN_CYCLES 0"
}
