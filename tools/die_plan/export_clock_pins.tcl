# Source after placement/routing. OT_CLOCK_PINS names the output TSV.
# Alongside write_global_route_segments, this is the complete pin/RC identity
# needed by clock_segments_spef.py; it never asks OpenRCX to export STA estimates.
set ot_cp_f [open $::env(OT_CLOCK_PINS) w]
set ot_cp_blk [ord::get_db_block]
puts $ot_cp_f "DBU\t[[ord::get_db_tech] getDbUnitsPerMicron]"
foreach ot_cp_n [$ot_cp_blk getNets] {
  set ot_cp_rule [$ot_cp_n getNonDefaultRule]
  set ot_cp_rname DEFAULT
  if {$ot_cp_rule ne "NULL"} {set ot_cp_rname [$ot_cp_rule getName]}
  puts $ot_cp_f "NET\t[$ot_cp_n getName]\t$ot_cp_rname"
  foreach ot_cp_it [$ot_cp_n getITerms] {
    set ot_cp_mt [$ot_cp_it getMTerm]
    lassign [$ot_cp_it getAvgXY] ot_cp_ok ot_cp_x ot_cp_y
    if {!$ot_cp_ok} {error "clock pin has no physical location: [$ot_cp_it getName]"}
    set ot_cp_min 100
    foreach ot_cp_mp [$ot_cp_mt getMPins] {
      foreach ot_cp_box [$ot_cp_mp getGeometry] {
        set ot_cp_l [$ot_cp_box getTechLayer]
        if {$ot_cp_l ne "NULL" && [$ot_cp_l getRoutingLevel] > 0} {
          set ot_cp_min [expr {min($ot_cp_min,[$ot_cp_l getRoutingLevel])}]
        }
      }
    }
    if {$ot_cp_min == 100} {error "clock pin has no metal shape"}
    set ot_cp_dir [string index [$ot_cp_mt getIoType] 0]
    puts $ot_cp_f "PIN\t[$ot_cp_n getName]\tI\t[[$ot_cp_it getInst] getName]:[$ot_cp_mt getName]\t$ot_cp_dir\tM$ot_cp_min\t$ot_cp_x\t$ot_cp_y"
  }
  foreach ot_cp_bt [$ot_cp_n getBTerms] {
    set ot_cp_done 0
    foreach ot_cp_bp [$ot_cp_bt getBPins] {
      foreach ot_cp_box [$ot_cp_bp getBoxes] {
        set ot_cp_l [$ot_cp_box getTechLayer]
        set ot_cp_x [expr {([$ot_cp_box xMin]+[$ot_cp_box xMax])/2.0}]
        set ot_cp_y [expr {([$ot_cp_box yMin]+[$ot_cp_box yMax])/2.0}]
        set ot_cp_dir [string index [$ot_cp_bt getIoType] 0]
        puts $ot_cp_f "PIN\t[$ot_cp_n getName]\tP\t[$ot_cp_bt getName]\t$ot_cp_dir\t[$ot_cp_l getName]\t$ot_cp_x\t$ot_cp_y"
        set ot_cp_done 1
        break
      }
      if {$ot_cp_done} {break}
    }
    if {!$ot_cp_done} {error "clock top pin has no placed shape"}
  }
}
close $ot_cp_f
