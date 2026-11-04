# Optional violator-only DRV repair. Existing dont-touch state (especially clocks)
# survives; temporary data-net guards are restored even when repair reports error.
# DIE-S81-54/ECO 11-04 (class fix, residual slew after the late ECO; bk_g, xrt1, half, bfr):
#  (1) names: STA gives u.ra_n[101], ODB holds u.ra_n\[101\], so a bracketed violator never matched its own net and was
#      GUARDED: repair could not touch it (bk_g wl100: 174 selected, 10 left, all bracketed) -> compare unescaped.
#  (2) OT_PRD_TARGET_SLEW_PS (default off): select at this design max_transition (session selection only, restored
#      before repair; sign-off limits unchanged), since DRT re-routes move near-limit nets over 320.
#  (3) a selected net driven by a tie cell is split, one tie per load except the nearest: resizer cannot buffer a tie
#      net (half: TIELOx1 -> 5 ICG/SE over 230 um, slew 352). Constant value unchanged. OT_PRD_TIE_SPLIT=0 = off.
proc ot_prd_net_key {name} { return [string map {\\ {}} $name] }
proc ot_prd_tie_split {keepvar} {
  upvar 1 $keepvar keep
  set block [ord::get_db_block]
  set split 0; set made 0
  foreach net [$block getNets] {
    set key [ot_prd_net_key [$net getName]]
    if {![dict exists $keep $key] || [$net getSigType] ne "SIGNAL"} continue
    set drv {}; set loads {}
    foreach it [$net getITerms] {
      if {[$it isOutputSignal]} { lappend drv $it } elseif {[$it isInputSignal]} { lappend loads $it }
    }
    if {[llength $drv] != 1} continue
    set dinst [[lindex $drv 0] getInst]
    set master [$dinst getMaster]
    if {![string match TIE* [$master getName]]} continue
    dict unset keep $key
    if {[llength $loads] < 2} continue
    lassign [$dinst getLocation] dx dy
    set best {}; set bestd -1
    foreach l $loads {
      lassign [[$l getInst] getLocation] x y
      set d [expr {abs($x - $dx) + abs($y - $dy)}]
      if {$bestd < 0 || $d < $bestd} { set best $l; set bestd $d }
    }
    set out [[[lindex $drv 0] getMTerm] getName]
    foreach l $loads {
      if {$l eq $best} continue
      set n 0
      while {[$block findInst ot_prd_tie_$n] ne "NULL"} { incr n }
      set ti [odb::dbInst_create $block $master ot_prd_tie_$n]
      set nn [odb::dbNet_create $block ot_prd_tie_${n}_n]
      lassign [[$l getInst] getLocation] x y
      $ti setLocation $x $y
      $ti setPlacementStatus PLACED
      [$ti findITerm $out] connect $nn
      # a gated-clock cell load is dont_touch: its data pin moves, the cell stays LOCKED
      set li [$l getInst]; set ldt [$li isDoNotTouch]
      $li setDoNotTouch 0
      $l disconnect
      $l connect $nn
      $li setDoNotTouch $ldt
      incr made
    }
    incr split
  }
  puts "OT_PRD_TARGETED tie nets split $split, tie cells added $made"
}
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
  if {![info exists ::env(OT_PRD_TIE_SPLIT)] || $::env(OT_PRD_TIE_SPLIT) ne "0"} { ot_prd_tie_split keep }
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
