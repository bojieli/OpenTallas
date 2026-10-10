# struct-close 2026-10-09 ("-cl"): TA15 production body (ot_hbm_production_clock_digital_body_cl.sv).  ASAP7 unit: ps.
# = the owner's production_body.sdc (five clocks, provisional AON entry / exit obligations, NO waiver) plus the bounded-
# window idiom of the CLOSED collar (physical/strip_protect/ta15_collars_rs.sdc) on the only cells that take a
# cross-domain or asynchronous signal, all of them synchroniser stage flops:
#   collars *sync_q*      (async clear from the AON intents / por_n / pll_lock: deassert recovery bounded 500 / 0 ps)
#   rel_sync_q0           (AON stage 1 of each destination reset: data from 4 destination clocks, bounded 500 / 0 ps)
#   status_meta           (reset_seq AON stage 1 of the asynchronous readiness inputs, bounded 500 / 0 ps)
# Everything after a synchroniser stage is synchronous and timed with no exception.
# ---- production_body.sdc (owner), inlined ----
# Full digital boot body, separately from the analog PLL. ASAP7 time unit: ps.
unset_input_delay [all_inputs]
unset_output_delay [all_outputs]
delete_clock [all_clocks]
create_clock -name aon -period 3000 [get_ports aon_clk]
create_clock -name stream -period 833.333333 [get_ports clk_stream]
create_clock -name serial -period 1111.111111 [get_ports clk_serial]
create_clock -name hbm -period 1024 [get_ports clk_hbm]
create_clock -name link -period 833.333333 [get_ports clk_link]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
# Provisional AON entry obligations; no asynchronous exceptions and no reset
# recovery/removal waiver. Actual POR/lock/readiness providers remain unbound.
set_input_delay -min 25 -clock aon [get_ports {por_n power_good pll_lock phy_ready* links_ready* bist_done bist_pass fatal_error requalify}]
set_input_delay -max 100 -clock aon [get_ports {por_n power_good pll_lock phy_ready* links_ready* bist_done bist_pass fatal_error requalify}]
set_output_delay -min 25 -clock aon [get_ports {pll_reset_n ready state*}]
set_output_delay -max 100 -clock aon [get_ports {pll_reset_n ready state*}]
set_output_delay -min 25 -clock hbm [get_ports phy_reset_n*]
set_output_delay -max 100 -clock hbm [get_ports phy_reset_n*]
set_output_delay -min 25 -clock link [get_ports link_reset_n*]
set_output_delay -max 100 -clock link [get_ports link_reset_n*]
set_output_delay -min 25 -clock stream [get_ports {coll_reset_stream_n cmd_reset_stream_n}]
set_output_delay -max 100 -clock stream [get_ports {coll_reset_stream_n cmd_reset_stream_n}]
set_output_delay -min 25 -clock serial [get_ports {coll_reset_serial_n cmd_reset_serial_n}]
set_output_delay -max 100 -clock serial [get_ports {coll_reset_serial_n cmd_reset_serial_n}]
# ---- struct-close additions ----
set ot_cs {}; set ot_r0 {}; set ot_sm {}
foreach c [get_cells -hierarchical -quiet *sync_q*] {
  set n [get_full_name $c]
  if {[string match *rel_sync_q0* $n]} { lappend ot_r0 $c } elseif {![string match *rel_sync_q1* $n]} { lappend ot_cs $c }
}
set ot_sm [get_cells -hierarchical -quiet *status_meta*]
puts "OT_TA15_CL: collar sync [llength $ot_cs], ready stage-1 [llength $ot_r0], status stage-1 [llength $ot_sm]"
if {![llength $ot_cs] || ![llength $ot_r0] || ![llength $ot_sm]} { error "OT_TA15_CL: synchroniser cells not found" }
set ot_ain [get_ports {por_n power_good pll_lock phy_ready* links_ready* bist_done bist_pass}]
# collar synchronisers: raw asynchronous reset from AON logic and the async inputs
set_max_delay 500 -ignore_clock_latency -from [get_clocks aon] -to $ot_cs
set_min_delay 0   -ignore_clock_latency -from [get_clocks aon] -to $ot_cs
set_max_delay 500 -ignore_clock_latency -from $ot_ain -to $ot_cs
set_min_delay 0   -ignore_clock_latency -from $ot_ain -to $ot_cs
# destination resets into the AON readiness synchroniser
set_max_delay 500 -ignore_clock_latency -from [get_clocks {stream serial hbm link}] -to $ot_r0
set_min_delay 0   -ignore_clock_latency -from [get_clocks {stream serial hbm link}] -to $ot_r0
# asynchronous readiness inputs into the reset sequencer's AON synchroniser
set_max_delay 500 -ignore_clock_latency -from $ot_ain -to $ot_sm
set_min_delay 0   -ignore_clock_latency -from $ot_ain -to $ot_sm
