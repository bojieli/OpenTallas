# el1013-qwen-kvstrips 2026-10-13: second clock of QKD_CTRL_PC for the REFERENCE TILE FLOW (spec sdc_extra, inlined at the end
# of clock.sdc and signoff.sdc; core_clk on port ck is created by ref_tile and is NOT relaxed here).  Same
# constraint form as the KV write-side CDC leaf (physical/qwen_stream4_cdc/qkd_cdc_wleaf_ref.sdc):
#   two asynchronous roots; NO clock groups and NO false paths on the crossings: every arc between the roots (Gray
#   pointer -> first synchroniser flop, FIFO storage read mux -> capture register) is a datapath budget = core_clk
#   period - setup uncertainty in BOTH directions, hold = non-negative datapath delay; each boundary port 0.2 T outside
#   the block in its OWN domain; after CTS the hclk ports are referenced to the propagated hclk tree exactly as
#   io_ref_skew.sdc does for core_clk (median hclk input pin flop).
create_clock -name hclk -period 1024.000 [get_ports pll_hbm]
set_clock_uncertainty -setup 60 [get_clocks hclk]
set_clock_uncertainty -hold 25 [get_clocks hclk]
set ot_cw_prop 0
catch {set ot_cw_prop [get_property [get_clocks core_clk] is_propagated]}
if {$ot_cw_prop} { set_propagated_clock [get_clocks hclk] }
set ot_cw_x [expr {[get_property [get_clocks core_clk] period] - 60.0}]
set_max_delay -ignore_clock_latency $ot_cw_x -from [get_clocks core_clk] -to [get_clocks hclk]
set_max_delay -ignore_clock_latency $ot_cw_x -from [get_clocks hclk] -to [get_clocks core_clk]
set_min_delay -ignore_clock_latency 0 -from [get_clocks core_clk] -to [get_clocks hclk]
set_min_delay -ignore_clock_latency 0 -from [get_clocks hclk] -to [get_clocks core_clk]
# cfg_stack is captured only by core-clock stack_q, and retains the core boundary.
# STRAP_CDC1 keeps raw pc exclusively on hclk pc_q, with real core CDC captures.
set ot_cw_hi [get_ports {ci[*] pi[*] ki[*] pc[*] fi hrst static_cmd_owner static_cmd[*] reserved_rd reserved_static_col reserved_write_col static_epoch[*] expected_raw_valid}]
set ot_cw_ho [get_ports {co[*] po[*] ko[*] fo corrected_epoch[*] idle_hbm drain_fault_hbm}]
catch {unset_input_delay [get_ports pll_hbm]}
unset_input_delay $ot_cw_hi
unset_output_delay $ot_cw_ho
set ot_cw_b 204.800
set ot_cw_lmax 0.0; set ot_cw_lmin 0.0
set ot_cw_sk 0.0; set ot_cw_hk 0.0; set ot_cw_hki 0.0
if {$ot_cw_prop} {
  set ot_cw_sk  [expr {[info exists ::env(OT_IO_SKEW)] ? $::env(OT_IO_SKEW) : 90}]
  set ot_cw_hk  [expr {[info exists ::env(OT_IO_HOLD_SKEW)] ? $::env(OT_IO_HOLD_SKEW) : 50}]
  set ot_cw_hki [expr {[info exists ::env(OT_IO_IN_HOLD_SKEW)] ? $::env(OT_IO_IN_HOLD_SKEW) : 0}]
  catch {sta::worst_slack_cmd max}
  set ot_cw_ck {}
  if {[llength [info procs ot_pf_clks]]} { set ot_cw_ck [ot_pf_clks $ot_cw_hi] }
  if {![llength $ot_cw_ck]} { set ot_cw_ck [lrange [all_registers -clock hclk -clock_pins] 0 255] }
  set ot_cw_pf {}
  foreach p $ot_cw_ck {
    set a [get_property $p arrival_max_rise]
    if {[string is double -strict $a]} { lappend ot_cw_pf [list $a $p] }
  }
  if {[llength $ot_cw_pf]} {
    set ot_cw_m [lindex [lsort -real -index 0 $ot_cw_pf] [expr {[llength $ot_cw_pf] / 2}]]
    set ot_cw_lmax [lindex $ot_cw_m 0]
    set ot_cw_lmin [get_property [lindex $ot_cw_m 1] arrival_min_rise]
    if {![string is double -strict $ot_cw_lmin]} { set ot_cw_lmin $ot_cw_lmax }
    puts "QKD_CTRL_PC hclk reference [get_full_name [lindex $ot_cw_m 1]] of [llength $ot_cw_pf] pin flops: clock arrival max $ot_cw_lmax min $ot_cw_lmin skew $ot_cw_sk hold $ot_cw_hk"
  } else {
    puts "QKD_CTRL_PC hclk reference: no hclk register arrival (ideal boundary kept)"
  }
  set_input_delay  [expr {$ot_cw_b + $ot_cw_lmax + $ot_cw_sk}] -max -clock hclk $ot_cw_hi
  set_input_delay  [expr {$ot_cw_lmin - $ot_cw_hki}]          -min -clock hclk $ot_cw_hi
  set_output_delay [expr {$ot_cw_b - $ot_cw_lmax + $ot_cw_sk}] -max -clock hclk $ot_cw_ho
  set_output_delay [expr {0.0 - $ot_cw_lmin - $ot_cw_hk}]     -min -clock hclk $ot_cw_ho
} else {
  set_input_delay  $ot_cw_b -clock hclk $ot_cw_hi
  set_output_delay $ot_cw_b -clock hclk $ot_cw_ho
}
