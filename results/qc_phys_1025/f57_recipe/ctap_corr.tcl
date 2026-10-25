# QC-PHYS f57 pass-2 correction tables from the routed f56c (6_final.spef RCX vs estimate; tap = mean register clock
# arrival of the tap, macro = its clock pin; probe epyc1:/srv/opentallas-scratch2/claude/qc-phys/rp1_f56c_routed).
# ot_ctap_corr (flow basis = rp1_grt.tcl incremental GRT, rc_cal kR0.8/kC0.9, f56c run_route.log itfinal TT; FF = TT x
#   the per-tap FF/TT ratio of the measure basis).  Macros now hang on their W region tap (OT_CTAP_MACRO_TAPOUT) -> host tap.
set ot_ctap_corr     { SE {-27.6 -23.3} E0 {-19.8 -16.8} E1 {-25.0 -21.2} SW {-19.7 -16.7} W0 {-16.8 -14.2} W1 {4.1 3.3} }
set ot_ctap_corr_mac { g_crb*0*.u_m {-16.8 -14.2} g_crb*1*.u_m {4.1 3.3} }
# ot_ctap_corr_meas (measure.tcl basis = fresh global_route, same RC; grt_taps_{TT,FF}.log itfinal), exact per corner.
set ot_ctap_corr_meas { SE {-46.5 -39.3} E0 {-30.5 -25.9} E1 {-46.0 -38.9} SW {-37.1 -31.5} W0 {-30.8 -26.0} W1 {-19.2 -15.5} }
# time every tap at estimate + correction: the correction is spread over the tap's PRIVATE input arcs (trunk wire into
# the tap = net arc driver -> tap/A, then the tap cell A -> Y), never below 1 ps; arrival of all its sinks (registers and
# the macro leaf on the tap output net) moves by the correction; any part that does not fit is printed as residual.
# All arc delays are read BEFORE any assignment (a corner's assigned value would leak into the min/max-over-corners
# edge properties).  set_assigned_delay takes USER time units (ps) -- never scale by 1e-12 (vmr_s5 pass-2 bug 10-25).
#   specs: list of {tbl idx corner dm}: tbl dict TAP {tt ff}; idx 0 tt / 1 ff; corner ORFS corner or "" ; dm max|min
proc ot_ctap_assign {specs} {
  set arcs {}
  foreach sp $specs {
    lassign $sp tbl idx corner dm
    # a tap arc is ~15-20 ps, smaller than the negative corrections: shift the table so its most negative entry is 0
    # (all corrections >= 0, always realisable).  Only differences between taps matter for balance; the common offset
    # moves every register and macro leaf alike and is absorbed by I (bound from this same corrected measurement).
    set cmin 1e9; dict for {r v} $tbl { set cmin [expr {min($cmin, [lindex $v $idx])}] }
    puts [format "OT_CTAP_ASSIGN shift %s idx %d by %+.1f (common offset, I absorbs it)" $corner $idx [expr {-$cmin}]]
    dict for {r v} $tbl {
      set v [lreplace $v $idx $idx [expr {[lindex $v $idx] - $cmin}]]
      if {![llength [get_cells -quiet ot_ctap_$r]]} { puts "OT_CTAP_ASSIGN no tap $r"; continue }
      set a [get_pins ot_ctap_$r/A]; set y [get_pins ot_ctap_$r/Y]
      set drv [get_pins -of_objects [get_nets -of_objects $a] -filter "direction==output"]
      set en [get_timing_edges -from $drv -to $a]; set ec [get_timing_edges -from $a -to $y]
      foreach rf {rise fall} { dict set arcs "$r,$idx,$rf" [list [get_property $en delay_${dm}_$rf] [get_property $ec delay_${dm}_$rf] $drv $a $y [lindex $v $idx] $corner] }
    }
  }
  set n 0
  dict for {k v} $arcs {
    lassign [split $k ,] r idx rf
    lassign $v dn dc drv a y c corner
    set nn $dn; set nc $dc
    if {$c < 0} { set nn [expr {max(1.0, $dn + $c)}]; set rem [expr {$c - ($nn - $dn)}]; set nc [expr {max(1.0, $dc + $rem)}] } else { set nc [expr {$dc + $c}] }
    set res [expr {$c - (($nn - $dn) + ($nc - $dc))}]
    set co [expr {$corner ne "" ? [list -corner $corner] : {}}]
    set_assigned_delay -net {*}$co -$rf -from $drv -to $a $nn
    set_assigned_delay -cell {*}$co -$rf -from $a -to $y $nc
    if {$rf eq "rise"} { puts [format "OT_CTAP_ASSIGN %s %s corner '%s' corr %+.1f net %.2f->%.2f cell %.2f->%.2f residual %+.1f" $r [lindex {tt ff} $idx] $corner $c $dn $nn $dc $nc $res] }
    incr n
  }
  return $n
}
