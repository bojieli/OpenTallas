# Optional violator-only DRV repair. Existing dont-touch state (especially clocks)
# survives; temporary data-net guards are restored even when repair reports error.
# DIE-S81-54/ECO 11-04 (class fix, residual slew after the late ECO; bk_g, xrt1, half, bfr):
#  (1) names: STA gives u.ra_n[101], ODB holds u.ra_n\[101\], so a bracketed violator never matched its own net and was
#      GUARDED: repair could not touch it (bk_g wl100: 174 selected, 10 left, all bracketed) -> compare unescaped.
#  (2) OT_PRD_TARGET_SLEW_PS (default off): select at this design max_transition (session selection only, restored
#      before repair; sign-off limits unchanged), since DRT re-routes move near-limit nets over 320.
#  (3) long tie nets: see prd_tiesplit.tcl, which runs before the SPEF read.
proc ot_prd_net_key {name} { return [string map {\\ {}} $name] }
proc ot_prd_repair_targeted {drv_args} {
  set report [file join $::env(REPORTS_DIR) ot_prd_targeted.rpt]
  set _sel [expr {[info exists ::env(OT_PRD_TARGET_SLEW_PS)] ? $::env(OT_PRD_TARGET_SLEW_PS) : 0}]
  if {$_sel > 0} { set_max_transition $_sel [current_design] }
  report_check_types -max_slew -max_capacitance -max_fanout -violators -max_count 100000 > $report
  if {$_sel > 0} { set_max_transition 1e6 [current_design] }
  set f [open $report]; set text [read $f]; close $f
  set keep [dict create]
  foreach line [split $text "\n"] {
    if {![regexp {^\s*(\S+)\s+[-+0-9.eE]+\s+[-+0-9.eE]+\s+-[0-9.eE+]+\s+\(VIOLATED\)} $line -> pin]} continue
    set objects [get_pins -quiet $pin]
    if {![llength $objects]} {set objects [get_ports -quiet $pin]}
    if {![llength $objects]} continue
    foreach net [get_nets -quiet -of_objects $objects] {dict set keep [ot_prd_net_key [get_full_name $net]] 1}
  }
  set guards {}
  foreach net [[ord::get_db_block] getNets] {
    if {[$net getSigType] ne "SIGNAL" || [$net isDoNotTouch] || [dict exists $keep [ot_prd_net_key [$net getName]]]} continue
    $net setDoNotTouch 1
    lappend guards $net
  }
  puts "OT_PRD_TARGETED repair nets [dict size $keep] guards [llength $guards]: [lrange [dict keys $keep] 0 199]"
  try {repair_design {*}$drv_args} finally {
    foreach net $guards {$net setDoNotTouch 0}
  }
}
