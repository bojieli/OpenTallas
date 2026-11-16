# serdes_lanes_release.tcl (HARD-S81-SERDES-1; PRE_DETAIL_PLACE, sourced from face_flops_release.tcl): remove the GPL-only
# placement blockages of serdes_lanes.tcl so repair buffers, CTS cells and DPL may use the whole lot.
uplevel #0 {
set slr_f $::env(RESULTS_DIR)/ot_serdes_lane_blocks.txt
if {[file exists $slr_f]} {
  set slr_want {}; set fh [open $slr_f r]; foreach l [split [read $fh] "\n"] { if {$l ne ""} { dict set slr_want $l 1 } }; close $fh
  set slr_n 0
  foreach k [[ord::get_db_block] getBlockages] {
    set bb [$k getBBox]
    if {[dict exists $slr_want "[$bb xMin],[$bb yMin],[$bb xMax],[$bb yMax]"]} { odb::dbBlockage_destroy $k; incr slr_n }
  }
  puts "OT_SERDES_LANES released $slr_n placement blockages"
}
}

# HARD-S81-SERDES-1 G3: optional GPL-only fences. Opendp leaves inserted,
# ungrouped buffers at region.xMax-1 DBU despite exact site-grid boundaries.
# The existing G3 failed-ODB fixture passes DPL after this narrow release:
# all clock nets unchanged, 5/6 groups entirely retained, syn max excursion .216um.
# Defaults keep existing hard fences. The calling form must opt in explicitly,
# then review actual final member locality; this is not a clock/placement waiver.
uplevel #0 {
if {[info exists sl_cfg] && [dict exists $sl_cfg release_regions_before_dpl]
    && [dict get $sl_cfg release_regions_before_dpl]} {
  set slr_b [ord::get_db_block]
  set slr_receipt [open $::env(RESULTS_DIR)/ot_serdes_released_groups.tsv w]
  puts $slr_receipt "region\tboxes_dbu\tmembers"
  set slr_ng 0
  foreach slr_r [$slr_b getRegions] {
    if {![string match sl_* [$slr_r getName]]} continue
    set slr_boxes {}
    foreach slr_box [$slr_r getBoundaries] {
      lappend slr_boxes [list [$slr_box xMin] [$slr_box yMin] [$slr_box xMax] [$slr_box yMax]]
    }
    set slr_members {}
    foreach slr_g [$slr_r getGroups] {
      foreach slr_i [$slr_g getInsts] {lappend slr_members [$slr_i getName]}
      foreach slr_i [$slr_g getInsts] {$slr_g removeInst $slr_i}
      odb::dbGroup_destroy $slr_g
    }
    puts $slr_receipt "[$slr_r getName]\t$slr_boxes\t$slr_members"
    odb::dbRegion_destroy $slr_r
    incr slr_ng
  }
  close $slr_receipt
  puts "OT_SERDES_LANES released $slr_ng GPL-only region fences; original membership/bounds recorded"
}
}
