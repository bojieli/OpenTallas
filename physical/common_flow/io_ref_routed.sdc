# FLOW-IOREF 2026-10-08: sign-off IO reference from the ROUTE'S OWN clock tree (rule H1 "mean FF insertion").
# Read LAST (after 6_final.sdc, SPEF, set_propagated_clock and every post-SDC) in a single-corner sign-off / hold-ECO
# session.  Every VIRTUAL clock (vclk, vclki, ot_lb_v_<clk>, nbr_clk, ...) is moved to the mean propagated clock
# arrival, IN THIS SESSION'S CORNER, at the boundary registers of its real clock (registers fed by a data input or
# feeding a data output -- ck_insertion.py's definition); IO delays and the H1 uncertainties (+50 sender / 25
# receiver) are untouched.  Why: the die clock plan aligns every block's nominal insertion, so the routed tree is the
# truth; the calibrate run's CTS (or an assumed) insertion is not (hbm_pkt_ii1r: vclk FF 363 from calibrate vs the
# routed FF mean ~307 -> output-port-only hold -43).  Only the insertion-reference virtual clocks (vclk*, ot_lb_v_*,
# nbr_clk) move; window clocks with explicit min/max source latency (io_clk, io_ci/io_co) are kept.  Virtual clock -> real clock: ot_lb_v_<name> / a name match, else
# the only real clock with register sinks, else core_clk for vclk*, else the dominant one (>= 4x the register sinks of any other); otherwise left unchanged (OT_IOREF skip).  Prints one OT_IOREF line per clock.
# MMFF-INSERTION 2026-10-08: in a MULTI-SCENE session (orfs_hold_mm.tcl: WC = TT/SS libs + BC = FF libs in one STA)
# `get_property <pin> arrival_max_rise` is the max over ALL scenes = the TT/SS arrival, not this mode's corner: the
# route-time FF scene set vclk 1.2x too late (hbm_vm8_nws_s2_hm25 4_1_cts: mm 455.7 = TT-only 455.7, FF-only 380.2 =
# calibrate 380) -> FF output hold over-repaired / input hold under-repaired by ~75 ps on every mm route.  The caller
# names its scene in ::ot_ioref_scene (ot_mm_sync: BC); arrivals are then read with report_arrival -scene (the max of
# the rise arrivals, = arrival_max_rise of a single-corner session).  A single-scene session is unchanged.
proc ot_ir_multi {} { expr {![catch {sta::multi_scene} m] && $m} }
# STRUCT-CLOSE 2026-10-09 (PROPOSED, flow owner to adopt): the insertion of a sink is its ACTIVE-edge arrival.  A sink
# behind an odd number of inversions (ot_fwd_link_stage on fck = ~ck, negedge flops: every common-clock station) has its
# pin RISE driven by the source FALL edge, so arrival_max_rise = T/2 + tree: dsfd_hstnh_515 read "vclk mean 603.1" for a
# ~190 ps tree and its CTS hold repair chased FF -384.7 on all 515 outputs (RSZ-0060).  The smaller of the max-rise and
# max-fall arrivals is the tree delay for both senses (a non-inverted sink's fall is >= T/2 later, so it is unchanged).
proc ot_ir_minrf {r f} {
  set ok {}
  foreach v [list $r $f] { if {$v ne "" && [string is double -strict $v]} { lappend ok $v } }
  if {![llength $ok]} { return "" }
  return [lindex [lsort -real $ok] 0]
}
proc ot_ir_arr {p} {
  if {![ot_ir_multi]} { return [ot_ir_minrf [get_property $p arrival_max_rise] [get_property $p arrival_max_fall]] }
  set sc [expr {[info exists ::ot_ioref_scene] ? [list -scene $::ot_ioref_scene] : {}}]
  sta::redirect_string_begin
  catch {report_arrival {*}$sc -digits 4 $p}
  set r [sta::redirect_string_end]
  set vr ""; set vf ""
  foreach {- x} [regexp -all -inline {\sr\s+\S+:(\S+)} $r] { if {[string is double -strict $x] && ($vr eq "" || $x > $vr)} { set vr $x } }
  foreach {- x} [regexp -all -inline {\sf\s+\S+:(\S+)} $r] { if {[string is double -strict $x] && ($vf eq "" || $x > $vf)} { set vf $x } }
  return [ot_ir_minrf $vr $vf]
}
if {[ot_ir_multi] && ![info exists ::ot_ioref_scene]} {
  # a run whose own orfs_hold_mm.tcl predates ::ot_ioref_scene: its hold scene is named BC (orfs_hold_mm) or ff (hold_eco)
  foreach ot_ir_n {BC ff} { if {![catch {sta::find_scene $ot_ir_n} ot_ir_o] && $ot_ir_o ne "" && $ot_ir_o ne "NULL"} { set ::ot_ioref_scene $ot_ir_n; break } }
}
if {[ot_ir_multi]} {
  if {[info exists ::ot_ioref_scene]} { puts "OT_IOREF multi-scene session: arrivals of scene $::ot_ioref_scene" } else {
    puts "OT_IOREF WARNING: multi-scene session without ::ot_ioref_scene: arrivals of the command scene" }
}
set ot_ir_real {}
foreach c [all_clocks] { if {[llength [get_property $c sources]]} { lappend ot_ir_real [get_full_name $c] } }
# S81-TAIL 2026-10-08: a data input delay on a REAL clock's source port (route SDCs that budget every non-core input,
# e.g. s81ph dsfd_ctrl_pc: set_input_delay 316.7 -clock vclk on ckh[0] = hbm_clk) makes the register clock pins of
# that clock carry a DATA arrival (vclk latency + input delay + tree), and arrival_max_rise below returns it instead
# of the clock arrival: hbm_clk measured 796 TT / 752 FF vs the real tree 226 / 188 -> fake i2r TT -556 / out FF -487.
# A clock source port times no data, so its input delays are dropped before the measurement.
foreach cn $ot_ir_real {
  foreach s [get_property [get_clocks $cn] sources] {
    set sn [get_full_name $s]
    if {![llength [get_ports -quiet $sn]]} continue
    # unset_input_delay without -clock only drops clock-less delays: one call per reference clock and edge
    foreach ot_ir_c [all_clocks] {
      unset_input_delay -clock $ot_ir_c [get_ports $sn]; unset_input_delay -clock $ot_ir_c -clock_fall [get_ports $sn]
    }
    unset_input_delay [get_ports $sn]
    puts "OT_IOREF clock-port $sn ($cn): data input delays dropped"
  }
}
set ot_ir_bnd [dict create]
set ot_ir_din [all_inputs -no_clocks]
if {[llength $ot_ir_din]} {
  foreach pe [find_timing_paths -path_delay max -from $ot_ir_din -to [all_registers -data_pins] -group_path_count 200000 -endpoint_path_count 1] {
    dict set ot_ir_bnd [regsub {/[^/]+$} [get_full_name [get_property $pe endpoint]] {}] 1 }
}
if {[llength [all_outputs]]} {
  foreach pe [find_timing_paths -path_delay max -from [all_registers -clock_pins] -to [all_outputs] -group_path_count 200000 -endpoint_path_count 100000] {
    dict set ot_ir_bnd [regsub {/[^/]+$} [get_full_name [get_property $pe startpoint]] {}] 1 }
}
set ot_ir_ins [dict create]
set ot_ir_nreg [dict create]
foreach cn $ot_ir_real {
  set b {}; set a {}
  foreach p [all_registers -clock_pins -clock [get_clocks $cn]] {
    set v [ot_ir_arr $p]
    if {$v eq "" || $v eq "INF" || $v eq "-INF"} continue
    lappend a $v
    if {[dict exists $ot_ir_bnd [regsub {/[^/]+$} [get_full_name $p] {}]]} { lappend b $v }
  }
  set use [expr {[llength $b] ? $b : $a}]
  if {![llength $use]} continue
  set s 0.0; foreach v $use { set s [expr {$s + $v}] }
  set u [lsort -real $use]
  dict set ot_ir_ins $cn [list [expr {$s / [llength $use]}] [lindex $u 0] [lindex $u end] [llength $use] [expr {[llength $b] ? "boundary" : "all"}]]
  dict set ot_ir_nreg $cn [llength $a]
}
foreach c [all_clocks] {
  if {[llength [get_property $c sources]]} continue
  set vn [get_full_name $c]; set rc ""
  if {![regexp {^(vclk[A-Za-z0-9_]*|ot_lb_v_.*|nbr_clk)$} $vn]} { puts "OT_IOREF keep $vn (not an insertion-reference clock)"; continue }
  foreach cn [dict keys $ot_ir_ins] { if {$vn eq "ot_lb_v_$cn"} { set rc $cn } }
  if {$rc eq ""} { foreach cn [dict keys $ot_ir_ins] { if {[string first $cn $vn] >= 0} { set rc $cn } } }
  if {$rc eq "" && [dict size $ot_ir_ins] == 1} { set rc [lindex [dict keys $ot_ir_ins] 0] }
  # DRIVE-1113 2026-10-08: several real clocks (e.g. hfd_svc_SW_s3: core_clk + forwarded input clocks fq4 / fe that only
  # write two-clock FIFOs) -> the insertion reference is the DOMINANT real clock: the one with >= 4x the register sinks
  # of every other (the forwarded clocks clock a few hundred FIFO flops).  Before this every such block skipped vclk.
  # FWDCLK-SWEEP 2026-10-08: the budget SDC convention makes vclk / vclki the IO reference of core_clk (forwarded input
  # clocks are declared asynchronous to {core_clk vclk}); hfd_index_q_b0 (core_clk + fk0 / fk1 key-capture clocks) is
  # below the 4x dominance ratio and was skipped.  A vclk* clock resolves to core_clk when that real clock exists.
  # DRIVE-1243 2026-10-08: a vclk_<x> whose PERIOD equals exactly one real clock's is that clock's reference (s81ph
  # dsfd_capt_grp: vclk_s = ser_clk period 4/3 core, IO of the ser domain; the core_clk fallback below moved it to the
  # core_clk FF mean 244 instead of the ser_clk 229).  Checked before the vclk* -> core_clk fallback.
  if {$rc eq "" && [string match vclk* $vn]} {
    set ot_ir_pm {}
    foreach cn [dict keys $ot_ir_ins] { if {abs([get_property [get_clocks $cn] period] - [get_property $c period]) < 0.001} { lappend ot_ir_pm $cn } }
    if {[llength $ot_ir_pm] == 1} { set rc [lindex $ot_ir_pm 0] }
  }
  if {$rc eq "" && [string match vclk* $vn] && [dict exists $ot_ir_ins core_clk]} { set rc core_clk }
  if {$rc eq "" && [dict size $ot_ir_nreg] > 1} {
    set ot_ir_srt [lsort -stride 2 -index 1 -integer -decreasing $ot_ir_nreg]
    if {[lindex $ot_ir_srt 1] >= 4 * [lindex $ot_ir_srt 3]} { set rc [lindex $ot_ir_srt 0] }
  }
  if {$rc eq ""} { puts "OT_IOREF skip $vn (no unique real clock)"; continue }
  lassign [dict get $ot_ir_ins $rc] L lo hi n kind
  set_clock_latency -source 0 [get_clocks $vn]
  set_clock_latency $L [get_clocks $vn]
  puts [format "OT_IOREF %s %s mean %.1f min %.1f max %.1f n %d %s" $vn $rc $L $lo $hi $n $kind]
}
