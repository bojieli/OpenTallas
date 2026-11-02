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
    foreach net [get_nets -quiet -of_objects $objects] {dict set keep [get_full_name $net] 1}
  }
  # Private current-PC case: actual187.818um critical INPUT wire is not a slew violator.
  # The immutable routed-input SHA is checked by the host driver before this session.
  set n [[ord::get_db_block] findNet net41987]
  if {$n eq "NULL" || $n eq "" || [$n getSigType] ne "SIGNAL" || [$n isDoNotTouch]} {
    error "PC_GEO80 wrong/clock/protected critical input net41987"
  }
  set observed {}
  foreach it [$n getITerms] {
    lappend observed [list [[$it getInst] getName] [[$it getMTerm] getName] [[[$it getInst] getMaster] getName]]
  }
  set expected [list [list _206161_ B AND3x1_ASAP7_75t_R] [list _217823_ A INVx1_ASAP7_75t_R] [list place25706 A BUFx3_ASAP7_75t_R] [list wire41988 Y BUFx16f_ASAP7_75t_R]]
  if {[lsort $observed] ne [lsort $expected] || [llength [$n getBTerms]]} {
    error "PC_GEO80 changed critical data connectivity/master: $observed"
  }
  dict set keep net41987 1
  puts "PC_GEO80 exact critical input added alongside normal current DRV nets"
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
