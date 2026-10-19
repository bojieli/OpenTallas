# COLL only: OpenDB stores the full physical core separately from the pruned
# standard-cell rows. GPL must solve the actual row envelope, then restore the
# physical core before metrics, IO, PDN/CTS/DRT or export. No row/region/blockage,
# macro location, paid outline, timing constraint or density target changes here.
if {[llength [info commands ::ot_coll_gpl_physical_core_orig]] == 0} {
  rename global_placement ::ot_coll_gpl_physical_core_orig
  proc global_placement {args} {
    set b [ord::get_db_block]
    set physical [$b getCoreAreaPolygon]
    set pb [$physical getEnclosingRect]
    set physical_box [list [$pb xMin] [$pb yMin] [$pb xMax] [$pb yMax]]
    set row_polygon [$b computeCoreArea]
    set rb [$row_polygon getEnclosingRect]
    set row_box [list [$rb xMin] [$rb yMin] [$rb xMax] [$rb yMax]]
    set die [$b getDieArea]
    set die_box [list [$die xMin] [$die yMin] [$die xMax] [$die yMax]]
    set macros {}
    foreach i [$b getInsts] {
      if {[[$i getMaster] isBlock]} {
        lappend macros [list [$i getName] [$i getOrient] [$i getLocation] [$i getPlacementStatus]]
      }
    }
    if {[llength [$b getRows]] == 0 || [llength $macros] != 15} {
      error "COLL_GPL_ROW_ENVELOPE requires actual rows and fifteen SRAM macros"
    }
    puts "COLL_GPL_ROW_ENVELOPE physical=$physical_box standard_rows=$row_box paid_die=$die_box"
    $b setCoreArea $row_polygon
    try {
      uplevel 1 [list ::ot_coll_gpl_physical_core_orig {*}$args]
    } finally {
      $b setCoreArea $physical
      set restored [$b getCoreArea]
      if {[list [$restored xMin] [$restored yMin] [$restored xMax] [$restored yMax]] ne $physical_box} {
        error "COLL_GPL_ROW_ENVELOPE failed to restore physical core"
      }
      foreach m $macros {
        lassign $m name orient location status
        set i [$b findInst $name]
        if {[$i getOrient] ne $orient || [$i getLocation] ne $location || [$i getPlacementStatus] ne $status} {
          error "COLL_GPL_ROW_ENVELOPE changed fixed macro $name"
        }
      }
      set after [$b getDieArea]
      if {[list [$after xMin] [$after yMin] [$after xMax] [$after yMax]] ne $die_box} {
        error "COLL_GPL_ROW_ENVELOPE changed paid die outline"
      }
      puts "COLL_GPL_ROW_ENVELOPE_RESTORED physical=$physical_box paid_die=$die_box fixed_macros=[llength $macros]"
    }
  }
}
