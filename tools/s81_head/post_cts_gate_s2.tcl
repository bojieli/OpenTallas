# post_cts_gate_s2.tcl -- S81-HEAD head element rebuild s2 (HEAD-ELEM2 2026-10-25), POST_CTS_TCL with
# SKIP_CTS_REPAIR_TIMING=1.  GEOM-REVIEW 04:49/04:50 PASS-COND [S81-HEAD/HEAD-ELEM 04:48] condition (4): route only if
# the RCX-calibrated FF hold estimate is >= 0 and related-pair skew <= 80 ps at TT and FF; (1) elemB: t_r -> w_r
# Manhattan median <= 20 um and none > 100 um.  The parasitic basis is the kit's LAYER_PARASITICS_FILE (rc_fit.tcl fitted setRC).
#  step 1 (S81/HEAD3 COORD 00:46 structural stop, unchanged): FF hold WNS < -100 or > 2000 endpoints before repair.
#  step 2: unchanged ORFS CTS repair (repair_timing_helper at HOLD_SLACK_MARGIN) + legalise.
#  step 3 (new): route gate -> /work/route_gate.json; on FAIL also /work/FAIL_POSTCTS (autopilot: STRUCTURAL
#  post-cts-hold) + 4_1_cts_gate.odb, and the run stops before GRT.  The gate never changes the design.
estimate_parasitics -placement
proc ot_g_corner {names what} {
  foreach n $names { if {![catch {find_timing_paths -corner $n -path_delay min -group_path_count 1}]} { return $n } }
  error "OT_CTS_GATE: no $what corner"
}
proc ot_g_ff {} { return [ot_g_corner {bc ff BC FF} "FF / bc"] }
proc ot_g_tt {} { return [ot_g_corner {tc tt TC TT} "TT / tc"] }
set ot_ff [ot_g_ff]; set ot_tt [ot_g_tt]
proc ot_g_hold {corner} {
  set ps [find_timing_paths -corner $corner -path_delay min -group_path_count 100000 -endpoint_path_count 1 -slack_max 0]
  set w 0.0; foreach p $ps { set s [get_property $p slack]; if {$s < $w} { set w $s } }
  return [list $w [llength $ps] $ps]
}
set ot_sw [expr {[sta::worst_slack_cmd max] * 1e12}]
lassign [ot_g_hold $ot_ff] ot_hw ot_hn ot_ps
set fh [open /work/cts_gate.json w]
puts $fh [format "{\"corner\": \"%s\", \"ff_hold_wns_ps\": %.2f, \"ff_hold_viol\": %d, \"setup_wns_ps\": %.2f, \"limit_wns_ps\": -100, \"limit_viol\": 2000}" $ot_ff $ot_hw $ot_hn $ot_sw]
close $fh
puts "OT_CTS_GATE corner $ot_ff ff_hold_wns $ot_hw ff_hold_viol $ot_hn setup_wns $ot_sw"
proc ot_g_stop {why} {
  set fh [open /work/FAIL_POSTCTS w]; puts $fh $why; close $fh
  report_checks -corner [ot_g_ff] -path_delay min -group_path_count 5 -slack_max 0 -format full_clock_expanded > /work/cts_gate_min.rpt
  orfs_write_db $::env(RESULTS_DIR)/4_1_cts_gate.odb
  error "OT_CTS_GATE STOP: $why"
}
if {$ot_hw < -100.0 || $ot_hn > 2000} {
  set fh [open /work/cts_gate_ends.tsv w]
  foreach p $ot_ps { puts $fh [format "%.2f\t%s\t%s" [get_property $p slack] [get_full_name [get_property $p startpoint]] [get_full_name [get_property $p endpoint]]] }
  close $fh
  ot_g_stop "structural FF hold before repair (WNS $ot_hw ps, $ot_hn endpoints)"
}
unset ot_ps
repair_timing_helper
detailed_placement
check_placement -verbose
estimate_parasitics -placement

# ---- step 3: route gate --------------------------------------------------------------------------------------------
proc ot_g_pairs {corner dly} {
  # reg->reg worst path per endpoint at one corner -> worst related-pair skew damage with CPPR credit (pair_skew.tcl
  # ot_ps_pairs decomposition: setup damage = clk_skew, hold damage = -clk_skew - 2 crpr), uncertainty excluded.
  set pes [find_timing_paths -corner $corner -from [all_registers -clock_pins] -to [all_registers -data_pins] \
             -path_delay $dly -group_path_count 200000 -endpoint_path_count 1 -unique_paths_to_endpoint]
  set worst -1e9; set wl ""; set n 0
  foreach pe $pes {
    if {![$pe is_check] || [$pe is_gated_clock] || [$pe is_latch_check]} continue
    set role [$pe check_role]
    if {$role ne "setup" && $role ne "hold"} continue
    set tp [$pe target_clk_path]
    if {$tp eq "NULL" || $tp eq ""} continue
    set per [expr {[get_property [$pe target_clk] period] * 1e-12}]
    set sk [$pe clk_skew]; set req [$pe data_required_time]; set tarr [$tp arrival]; set mg [$pe margin]
    set et [[$pe target_clk_edge] time]
    if {$role eq "setup"} {
      set x [expr {$req - $tarr + $mg - $et}]; set dmg [expr {$sk}]
    } else {
      set x [expr {$req - $tarr - $mg - $et}]
      set crpr [expr {-($x - $per * round($x / $per))}]
      set dmg [expr {-$sk - 2.0 * $crpr}]
    }
    incr n
    if {$dmg > $worst} { set worst $dmg; set wl "[get_full_name [get_property $pe startpoint]] -> [get_full_name [get_property $pe endpoint]]" }
  }
  return [list [expr {$worst * 1e12}] $n $wl]
}
# exact pair arithmetic needs zero uncertainty; the kit SDC's uncertainty lines are re-applied right after
set ot_unc {}
set fh [open $::env(SDC_FILE)]; while {[gets $fh l] >= 0} { if {[string match "set_clock_uncertainty *" $l]} { lappend ot_unc $l } }; close $fh
foreach c [all_clocks] { set_clock_uncertainty 0 -setup $c; set_clock_uncertainty 0 -hold $c }
foreach a [all_clocks] { foreach b [all_clocks] { catch {set_clock_uncertainty -from $a -to $b -setup 0}; catch {set_clock_uncertainty -from $a -to $b -hold 0} } }
set ot_pair {}
foreach c [list $ot_tt $ot_ff] { foreach d {max min} { lassign [ot_g_pairs $c $d] w n wl; dict set ot_pair "${c}_$d" [list $w $n $wl]; puts "OT_ROUTE_GATE pair $c $d worst [format %.2f $w] n $n $wl" } }
foreach l $ot_unc { eval $l }
set ot_pw -1e9; dict for {k v} $ot_pair { if {[lindex $v 0] > $ot_pw} { set ot_pw [lindex $v 0] } }
lassign [ot_g_hold $ot_ff] ot_hw2 ot_hn2 ot_ps2
unset ot_ps2
# elemB lane transport (GEOM cond 1): u_m.t_r[i] -> u_m.w_r[i] Manhattan, um
set ot_trw {}
set blk [ord::get_db_block]; set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
array set ot_t {}; array set ot_w {}
foreach i [$blk getInsts] {
  set nm [$i getName]
  if {[regexp {^u_m\.([tw])_r\[(\d+)\]} $nm -> k b]} { lassign [$i getLocation] x y; set ot_${k}($b) [list [expr {double($x)/$dbu}] [expr {double($y)/$dbu}]] }
}
foreach b [array names ot_w] { if {[info exists ot_t($b)]} { lassign $ot_t($b) x1 y1; lassign $ot_w($b) x2 y2; lappend ot_trw [expr {abs($x1-$x2)+abs($y1-$y2)}] } }
set ot_trw [lsort -real $ot_trw]; set ot_tn [llength $ot_trw]
set ot_tmed [expr {$ot_tn ? [lindex $ot_trw [expr {$ot_tn / 2}]] : 0}]
set ot_tmax [expr {$ot_tn ? [lindex $ot_trw end] : 0}]
set ot_t100 0; foreach v $ot_trw { if {$v > 100.0} { incr ot_t100 } }
set ot_trw_gate [expr {[info exists ::env(OT_GATE_TRW)] && $::env(OT_GATE_TRW)}]
set why {}
if {$ot_hw2 < 0.0} { lappend why "FF hold estimate after CTS repair [format %.2f $ot_hw2] ps < 0 ($ot_hn2 endpoints)" }
if {$ot_pw > 80.0} { lappend why "related-pair skew [format %.2f $ot_pw] ps > 80" }
if {$ot_trw_gate && ($ot_tmed > 20.0 || $ot_t100 > 0)} { lappend why "t_r->w_r median [format %.1f $ot_tmed] um / $ot_t100 > 100 um" }
set fh [open /work/route_gate.json w]
puts $fh [format "{\"basis\": \"LAYER_PARASITICS_FILE %s, placement parasitics after CTS repair\", \"ff_hold_wns_ps\": %.2f, \"ff_hold_viol\": %d, \"pair_skew_worst_ps\": %.2f, \"pair\": {%s}, \"t_r_w_r_um\": {\"n\": %d, \"median\": %.2f, \"max\": %.2f, \"over_100\": %d, \"gated\": %d}, \"verdict\": \"%s\", \"why\": \"%s\"}" \
  [expr {[info exists ::env(LAYER_PARASITICS_FILE)] ? $::env(LAYER_PARASITICS_FILE) : "platform setRC.tcl"}] $ot_hw2 $ot_hn2 $ot_pw \
  [join [lmap {k v} $ot_pair {format "\"%s\": %.2f" $k [lindex $v 0]}] ", "] $ot_tn $ot_tmed $ot_tmax $ot_t100 $ot_trw_gate \
  [expr {[llength $why] ? "STOP" : "ROUTE"}] [join $why "; "]]
close $fh
puts "OT_ROUTE_GATE ff_hold [format %.2f $ot_hw2] ($ot_hn2) pair [format %.2f $ot_pw] t_r->w_r med [format %.1f $ot_tmed] max [format %.1f $ot_tmax] >100 $ot_t100 -> [expr {[llength $why] ? "STOP" : "ROUTE"}]"
if {[llength $why]} { ot_g_stop [join $why "; "] }
