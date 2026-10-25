# QC-PHYS f57 pass-2 correction tables from the routed f56c (6_final.spef RCX vs estimate; tap = mean register clock
# arrival of the tap, macro = its clock pin; probe epyc1:/srv/opentallas-scratch2/claude/qc-phys/rp1_f56c_routed).
# ot_ctap_corr (flow basis = rp1_grt.tcl incremental GRT, rc_cal kR0.8/kC0.9, f56c run_route.log itfinal TT; FF = TT x
#   the per-tap FF/TT ratio of the measure basis).  Macros now hang on their W region tap (OT_CTAP_MACRO_TAPOUT) -> host tap.
set ot_ctap_corr     { SE {-27.6 -23.3} E0 {-19.8 -16.8} E1 {-25.0 -21.2} SW {-19.7 -16.7} W0 {-16.8 -14.2} W1 {4.1 3.3} }
set ot_ctap_corr_mac { g_crb*0*.u_m {-16.8 -14.2} g_crb*1*.u_m {4.1 3.3} }
# ot_ctap_corr_meas (measure.tcl basis = fresh global_route, same RC; grt_taps_{TT,FF}.log itfinal), exact per corner.
set ot_ctap_corr_meas { SE {-46.5 -39.3} E0 {-30.5 -25.9} E1 {-46.0 -38.9} SW {-37.1 -31.5} W0 {-30.8 -26.0} W1 {-19.2 -15.5} }
# time every tap cell arc at estimate + correction: arrival of all its sinks (registers and the macro leaf) moves by
# the correction.  set_assigned_delay takes USER time units (ps) -- never scale by 1e-12 (vmr_s5 pass-2 bug 10-25).
#   tbl: dict TAP {tt ff}; idx 0 = tt, 1 = ff; corner: ORFS corner name or "" (single-corner session); dm: max|min
proc ot_ctap_assign {tbl idx corner dm} {
  set n 0
  dict for {r v} $tbl {
    set c [lindex $v $idx]
    set cell [get_cells -quiet ot_ctap_$r]; if {![llength $cell]} { puts "OT_CTAP_ASSIGN no tap $r"; continue }
    set a [get_pins ot_ctap_$r/A]; set y [get_pins ot_ctap_$r/Y]
    set e [get_timing_edges -from $a -to $y]
    foreach rf {rise fall} {
      set d [get_property $e delay_${dm}_$rf]
      set v [expr {$d + $c}]; if {$v < 1.0} { set v 1.0 }
      if {$corner ne ""} { set_assigned_delay -cell -corner $corner -$rf -from $a -to $y $v } else { set_assigned_delay -cell -$rf -from $a -to $y $v }
      if {$rf eq "rise"} { puts [format "OT_CTAP_ASSIGN %s %s corner %s arc %.2f -> %.2f ps" $r [lindex {tt ff} $idx] $corner $d $v] }
    }
    incr n
  }
  return $n
}
