source /src/physical/ref_tile/s81sl_lepnhwd_r4f/candidate_birth_bind.tcl
# S81-RTLFIX 10-20 (s81sl_lepnhwd_r4f): ONE full-width std-cell band y 259.2..291.6 (x 2.16..473.04, 120 rows) between TX banks 2 and 3.
# Rows outside the band are removed before tapcell (place.tcl tail, ot_lep_trim_rows); here (PRE_GLOBAL_PLACE[_SKIP_IO] /
# PRE_DETAIL_PLACE) every movable std cell is owned by one INCLUSIVE native region on the band (main native_cell_fence.tcl),
# cells born later (repair / timing-driven buffers) are adopted at each later hook, and DPL can only legalise into band rows.
# No source, net, clock, supply or timing constraint is changed.
source /src/physical/dscoll_cx/native_cell_fence.tcl
set ::ot_lep_band {2.16 259.2 473.04 291.6}
# r4f: region boxes (W face column, central band, E face column)
set ::ot_lep_boxes {{2.16 2.16 32.4 559.44} {2.16 259.2 473.04 291.6} {451.44 2.16 473.04 559.44}}
proc ot_lep_movable {} {
  set names {}
  foreach i [[ord::get_db_block] getInsts] {
    if {[[$i getMaster] isBlock]} continue
    if {[ot_candidate_physical_only $i]} continue
    if {[$i getPlacementStatus] in {FIRM LOCKED COVER}} {error "LEP_BAND fixed functional cell [$i getName]"}
    if {[$i getGroup] ne "NULL"} continue
    lappend names [$i getName]
  }
  return $names
}
proc ot_lep_adopt_after_birth {stage} {
 if {![info exists ::env(RESULTS_DIR)]} {error "LEP_SOURCE missing RESULTS_DIR"}
 set source_netlist [file join $::env(RESULTS_DIR) 1_2_yosys.v]
 if {![file isfile $source_netlist] || [lindex [exec sha256sum $source_netlist] 0] ne "d183623e348e9275484e993b32cc18cf361ae854ed2a4f351e21cf99547c28ce"} {error "LEP_SOURCE mapped source identity changed"}
 ot_candidate_pg_ready $stage
set ot_lep_b [ord::get_db_block]
if {[$ot_lep_b findGroup ot_lep_band] eq "NULL"} {
  # INCLUSIVE (gate 053145: with only band rows, an EXCLUSIVE fence leaves GPL's top-level region all-fixed and the tie
  # cells -- which GPL keeps top-level -- at 'Utilization inf'; INCLUSIVE + band-only rows: every cell lands in the band)
  set ot_lep_u [[ord::get_db_tech] getDbUnitsPerMicron]
  set ot_lep_r [odb::dbRegion_create $ot_lep_b ot_lep_band]
  $ot_lep_r setRegionType INCLUSIVE
  foreach bx $::ot_lep_boxes {lassign $bx x0 y0 x1 y1; odb::dbBox_create $ot_lep_r [expr {round($x0*$ot_lep_u)}] [expr {round($y0*$ot_lep_u)}] [expr {round($x1*$ot_lep_u)}] [expr {round($y1*$ot_lep_u)}]}
  set ot_lep_g [odb::dbGroup_create $ot_lep_r ot_lep_band]
  $ot_lep_g setType VOLTAGE_DOMAIN
  set ot_lep_n 0
  foreach nm [ot_lep_movable] { $ot_lep_g addInst [$ot_lep_b findInst $nm]; incr ot_lep_n }
  puts "LEP_BAND_CREATED INCLUSIVE cells=$ot_lep_n box=$::ot_lep_band"
} else {
  set ot_lep_new [ot_lep_movable]
  foreach nm $ot_lep_new {
    set master [[[$ot_lep_b findInst $nm] getMaster] getName]
    if {[catch {ot_candidate_birth_role [$ot_lep_b findInst $nm]} detail]} {error "LEP_BIRTH unmodelled functional cell $nm $master: $detail"}
  }
  if {[llength $ot_lep_new]} { ot_native_cell_fence_add ot_lep_band $ot_lep_new }
  if {$stage in {DPL_CALL GPL_POST} && [llength $ot_lep_new]} {ot_candidate_seed_new ot_lep_band $::ot_lep_band $ot_lep_new}
  puts "LEP_BAND adopted=[llength $ot_lep_new]"
}

}

if {![llength [info commands ::ot_lep_global_placement_orig]]} {
 rename global_placement ::ot_lep_global_placement_orig
 proc global_placement {args} {
  ot_lep_adopt_after_birth GPL_CALL
  set result [uplevel 1 [list ::ot_lep_global_placement_orig {*}$args]]
  # S81-TILES-C: GPL timing-driven repair births buffers (place*) inside the call; adopt + seed them into the band
  # (same birth-role model as DPL_CALL) before the band check (lepnhwd_r3 08:31: 'unowned functional cell place49380')
  ot_lep_adopt_after_birth GPL_POST
  ot_lep_band_check GPL
  return $result
 }
 rename detailed_placement ::ot_lep_detailed_placement_orig
 proc detailed_placement {args} {
  ot_lep_adopt_after_birth DPL_CALL
  set result [uplevel 1 [list ::ot_lep_detailed_placement_orig {*}$args]]
  ot_lep_band_check DP
  return $result
 }
}

proc ot_lep_band_check {stage} {
 set b [ord::get_db_block];set u [[ord::get_db_tech] getDbUnitsPerMicron]
 set n [llength $::ot_lep_boxes]; set count 0
 for {set k 0} {$k < $n} {incr k} {set area($k) 0.0}
 foreach i [$b getInsts] {
  if {[[$i getMaster] isBlock] || [ot_candidate_physical_only $i]} continue
  set g [$i getGroup]
  if {$g eq "NULL" || [$g getName] ne "ot_lep_band"} {error "LEP_BAND unowned functional cell [$i getName]"}
  set bb [$i getBBox]; set hit -1
  for {set k 0} {$k < $n} {incr k} {
   lassign [lindex $::ot_lep_boxes $k] x0 y0 x1 y1
   if {[$bb xMin]>=round($x0*$u) && [$bb xMax]<=round($x1*$u) && [$bb yMin]>=round($y0*$u) && [$bb yMax]<=round($y1*$u)} {set hit $k; break}
  }
  if {$hit < 0} {error "LEP_BAND outside functional cell [$i getName] stage=$stage"}
  set area($hit) [expr {$area($hit)+double([[$i getMaster] getWidth])*[[$i getMaster] getHeight]/$u/$u}]
  incr count
 }
 set msg ""
 for {set k 0} {$k < $n} {incr k} {
  lassign [lindex $::ot_lep_boxes $k] x0 y0 x1 y1
  set d [expr {$area($k)/(($x1-$x0)*($y1-$y0))}]
  append msg " box$k=[format %.1f $area($k)]um2/[format %.3f $d]"
  if {$d > 0.65} {error "LEP_BAND box$k overfull density=$d stage=$stage"}
 }
 puts "LEP_BAND_ACTUAL_PASS stage=$stage cells=$count$msg"
}
