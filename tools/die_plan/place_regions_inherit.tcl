# place_regions_inherit.tcl -- PRE_DETAIL_PLACE (FLOW-NOADV-R3 11-20, FABLE-PD-S81-1840): buffers / inverters the place-stage repair added
# inherit the PLACE-REGION of the cells around them.  A repair buffer created after place_regions.tcl built the groups is in no group, so the
# legaliser may put it outside the region box (or a non-member inside it): a buffer whose signal neighbours (driver of its input, loads of its
# output) are all members of ONE region group joins that group.  Chains of buffers resolve in up to 4 passes.  One line per region:
# OT_PLACE_REGION_INHERIT.  Sourced from face_flops_release.tcl when the kit has place_regions_data.tcl.
uplevel #0 {
if {[info exists ::ot_place_regions]} {
  set pri_blk [ord::get_db_block]
  array unset pri_grp_of
  foreach pri_r [$pri_blk getRegions] {
    foreach pri_g [$pri_r getGroups] { foreach pri_i [$pri_g getInsts] { set pri_grp_of($pri_i) $pri_g } }
  }
  proc ot_pri_nbrs {i} {
    set out {}
    foreach it [$i getITerms] {
      set net [$it getNet]
      if {$net eq "NULL" || [$net getSigType] ne "SIGNAL" || [llength [$net getITerms]] > 256} continue
      foreach t [$net getITerms] { set o [$t getInst]; if {$o ne $i} { lappend out $o } }
    }
    return $out
  }
  array unset pri_added
  for {set pri_pass 0} {$pri_pass < 4} {incr pri_pass} {
    set pri_n 0
    foreach pri_i [$pri_blk getInsts] {
      if {[info exists pri_grp_of($pri_i)]} continue
      set pri_m [$pri_i getMaster]
      if {[$pri_m isBlock] || [$pri_i getPlacementStatus] in {FIRM LOCKED COVER}} continue
      if {![regexp -nocase {^(BUF|INV|HB|DLY)} [$pri_m getName]]} continue
      set pri_gs {}
      foreach pri_o [ot_pri_nbrs $pri_i] { if {[info exists pri_grp_of($pri_o)]} { lappend pri_gs $pri_grp_of($pri_o) } else { set pri_gs {}; break } }
      if {![llength $pri_gs] || [llength [lsort -unique $pri_gs]] != 1} continue
      set pri_g [lindex $pri_gs 0]
      $pri_g addInst $pri_i
      set pri_grp_of($pri_i) $pri_g
      incr pri_n
      set pri_gn [$pri_g getName]
      if {[info exists pri_added($pri_gn)]} { incr pri_added($pri_gn) } else { set pri_added($pri_gn) 1 }
    }
    if {!$pri_n} break
  }
  foreach pri_gn [array names pri_added] { puts "OT_PLACE_REGION_INHERIT $pri_gn: $pri_added($pri_gn) repair buffers / inverters joined the region group" }
}
}
