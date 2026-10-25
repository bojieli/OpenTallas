# QC rp1-clock 10-25: independent single-corner GRT-RC measurement (codex measure_tt/ff pattern): fresh global_route
# from the GRT checkpoint, estimate_parasitics -global_routing, then (1) TT setup / FF hold WNS + endpoints on the kit
# SDC, (2) exhaustive related-pair skew with CPPR (pair_skew.tcl, uncertainty zeroed), (3) pin-register clock
# insertion (signoff.py rule: boundary registers, source latency zeroed) -> I.   env: MC (TT|FF) ODB SDC OUT NICK
set C $::env(MC)
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_RVT_${C}_*] {read_liberty $l}
read_liberty /work/macros/ot_sram_1r1w_1024x256_m2_r2c2_[string tolower $C].lib
read_db $::env(ODB)
read_sdc $::env(SDC)
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
source /work/rc_cal.tcl
set_global_routing_layer_adjustment * 0.3
set_routing_layers -signal M2-M5 -clock M2-M5
set_macro_extension 2
global_route -congestion_iterations 30
estimate_parasitics -global_routing
set_propagated_clock [all_clocks]
# QC-PHYS f57: measure-basis (fresh GRT) RCX correction of every tap cell (ctap_corr.tcl ot_ctap_corr_meas)
if {[info exists ::env(OT_CTAP_CORR)] && $::env(OT_CTAP_CORR) ne ""} {
  source $::env(OT_CTAP_CORR)
  puts "OT_CTAP_ASSIGN meas $C [ot_ctap_assign [list [list $ot_ctap_corr_meas [expr {$C eq "FF"}] {} max]]]"
  source /work/pinreg.tcl; ot_vclk_bind OT_VCLK_$C arrival_max_rise "RP1_M $C"
}
puts [format "RP1_M %s setup_wns %.2f setup_ep %d hold_wns %.2f hold_ep %d" $C [expr {[sta::worst_slack_cmd max]*1e12}] [sta::endpoint_violation_count max] [expr {[sta::worst_slack_cmd min]*1e12}] [sta::endpoint_violation_count min]]
report_checks -path_delay min -group_path_count 3 -format end
set ::env(CORNER) ${C}_GRT
set ::ot_ps_lib_only 1
set_propagated_clock [all_clocks]
report_worst_slack -min
report_worst_slack -max
proc leaf {i} { set it [[ord::get_db_block] findInst $i]; return [[[$it findITerm CLK] getNet] getName] }
set eps {}
for {set k 0} {$k < 16} {incr k} { set n "g_cbk\\\[$k\\\].u/q\$_DFF_P_"; lappend eps [get_pins $n/D]
  puts "PRB_CBK $k [leaf $n] dnet [[[[[ord::get_db_block] findInst $n] findITerm D] getNet] getName]" }
lappend eps [get_pins {u_c1w/q$_DFF_P_/D}] [get_pins {u_c1/q$_DFF_P_/D}]
report_checks -path_delay min -to $eps -group_path_count 40 -endpoint_path_count 1 -format end -digits 2
report_checks -path_delay min -to [get_pins {g_cbk\[9\].u/q$_DFF_P_/D}] -format full_clock -digits 2
report_checks -path_delay max -to [get_pins {u_c1w/q$_DFF_P_/D}] -format end -digits 2
