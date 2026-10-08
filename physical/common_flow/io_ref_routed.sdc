# FLOW-IOREF 2026-10-08: sign-off IO reference from the ROUTE'S OWN clock tree (rule H1 "mean FF insertion").
# Read LAST (after 6_final.sdc, SPEF, set_propagated_clock and every post-SDC) in a single-corner sign-off / hold-ECO
# session.  Every VIRTUAL clock (vclk, vclki, ot_lb_v_<clk>, nbr_clk, ...) is moved to the mean propagated clock
# arrival, IN THIS SESSION'S CORNER, at the boundary registers of its real clock (registers fed by a data input or
# feeding a data output -- ck_insertion.py's definition); IO delays and the H1 uncertainties (+50 sender / 25
# receiver) are untouched.  Why: the die clock plan aligns every block's nominal insertion, so the routed tree is the
# truth; the calibrate run's CTS (or an assumed) insertion is not (hbm_pkt_ii1r: vclk FF 363 from calibrate vs the
# routed FF mean ~307 -> output-port-only hold -43).  Only the insertion-reference virtual clocks (vclk*, ot_lb_v_*,
# nbr_clk) move; window clocks with explicit min/max source latency (io_clk, io_ci/io_co) are kept.  Virtual clock -> real clock: ot_lb_v_<name> / a name match, else
# the only real clock with register sinks, else the dominant one (>= 4x the register sinks of any other); otherwise left unchanged (OT_IOREF skip).  Prints one OT_IOREF line per clock.
set ot_ir_real {}
foreach c [all_clocks] { if {[llength [get_property $c sources]]} { lappend ot_ir_real [get_full_name $c] } }
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
    set v [get_property $p arrival_max_rise]
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
