# Optional violator-only DRV repair. Existing dont-touch state (especially clocks)
# survives; temporary data-net guards are restored even when repair reports error.
proc ot_prd_repair_targeted {drv_args} {
  set report [file join $::env(REPORTS_DIR) ot_prd_targeted.rpt]
  report_check_types -max_slew -max_capacitance -max_fanout -violators -max_count 100000 > $report
  set f [open $report]; set text [read $f]; close $f
  set keep [dict create]
  foreach line [split $text "\n"] {
    if {![regexp {^\s*(\S+)\s+[-+0-9.eE]+\s+[-+0-9.eE]+\s+-[0-9.eE+]+\s+\(VIOLATED\)} $line -> pin]} continue
    set objects [get_pins -quiet $pin]
    if {![llength $objects]} {set objects [get_ports -quiet $pin]}
    if {![llength $objects]} continue
    foreach net [get_nets -quiet -of_objects $objects] {
      # STA display names and OpenDB escaped bus names are not interchangeable.
      # Join through the native object bridge, then use the same DB name on both sides.
      set db_net [sta::sta_to_db_net $net]
      if {$db_net eq "NULL" || $db_net eq ""} {
        error "OT_PRD_TARGETED unmapped violating STA net [get_full_name $net]"
      }
      dict set keep [$db_net getName] 1
    }
  }
  set guards {}
  foreach net [[ord::get_db_block] getNets] {
    if {[$net getSigType] ne "SIGNAL" || [$net isDoNotTouch] || [dict exists $keep [$net getName]]} continue
    $net setDoNotTouch 1
    lappend guards $net
  }
  puts "OT_PRD_TARGETED repair nets [dict size $keep]: [dict keys $keep]; temporary guards [llength $guards]"
  try {repair_design {*}$drv_args} finally {
    foreach net $guards {$net setDoNotTouch 0}
  }
}
