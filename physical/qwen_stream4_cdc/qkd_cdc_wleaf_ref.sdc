# q13-cdcw 2026-10-13: controller clock (hclk) of the KV write-side CDC leaf qkd_cdc_wleaf for the REFERENCE TILE FLOW
# (spec sdc_extra, inlined at the end of clock.sdc and signoff.sdc; core_clk = clk is created by ref_tile and is NOT
# relaxed here).  Same constraint form as the closed kit (physical/qwen_stream4_cdc/cdc_pc_die_m.sdc + io_skew.sdc):
#   two asynchronous roots, core clk 833.333 ps and the external periodic controller clock hclk 1,024 ps;
#   NO clock groups and NO false paths on the crossings: every clk <-> hclk arc (Gray pointer -> first synchroniser
#   flop, storage read mux -> capture register) is a datapath budget = core period - setup uncertainty in BOTH
#   directions (stricter than the source-period bound for the hclk-captured arcs), hold = non-negative datapath delay;
#   each boundary port 0.2 T outside the block in its OWN domain; after CTS the hclk ports are referenced to the
#   propagated hclk tree exactly as io_ref_skew.sdc does for core_clk (median hclk input pin flop).
create_clock -name hclk -period 1024.000 [get_ports hclk]
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
set ot_cw_hi [get_ports {h_lv h_lsec[*] h_lrow[*] h_ldata[*] h_hand h_wcon h_av h_atag[*]}]
set ot_cw_ho [get_ports {h_cred[*] h_wv h_wsec[*] h_cv h_csec[*] h_cdata[*] h_ctag[*] h_fault}]
catch {unset_input_delay [get_ports hclk]}
unset_input_delay $ot_cw_hi
unset_output_delay $ot_cw_ho
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
    puts "QKD_CDC_WLEAF hclk reference [get_full_name [lindex $ot_cw_m 1]] of [llength $ot_cw_pf] pin flops: clock arrival max $ot_cw_lmax min $ot_cw_lmin skew $ot_cw_sk hold $ot_cw_hk"
  } else {
    puts "QKD_CDC_WLEAF hclk reference: no hclk register arrival (ideal boundary kept)"
  }
  set_input_delay  [expr {204.8 + $ot_cw_lmax + $ot_cw_sk}] -max -clock hclk $ot_cw_hi
  set_input_delay  [expr {$ot_cw_lmin - $ot_cw_hki}]         -min -clock hclk $ot_cw_hi
  set_output_delay [expr {204.8 - $ot_cw_lmax + $ot_cw_sk}] -max -clock hclk $ot_cw_ho
  set_output_delay [expr {0.0 - $ot_cw_lmin - $ot_cw_hk}]    -min -clock hclk $ot_cw_ho
} else {
  set_input_delay  204.800 -clock hclk $ot_cw_hi
  set_output_delay 204.800 -clock hclk $ot_cw_ho
}
# the raw reset epoch: asynchronous assertion, released through the element's own per-domain synchronisers
set_false_path -from [get_ports {c_arst_n h_arst_n}]
