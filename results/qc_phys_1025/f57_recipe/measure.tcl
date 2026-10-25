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
  puts "OT_CTAP_ASSIGN meas $C [ot_ctap_assign $ot_ctap_corr_meas [expr {$C eq "FF"}] {} max]"
}
puts [format "RP1_M %s setup_wns %.2f setup_ep %d hold_wns %.2f hold_ep %d" $C [expr {[sta::worst_slack_cmd max]*1e12}] [sta::endpoint_violation_count max] [expr {[sta::worst_slack_cmd min]*1e12}] [sta::endpoint_violation_count min]]
report_checks -path_delay min -group_path_count 3 -format end
set ::env(CORNER) ${C}_GRT
set ::ot_ps_lib_only 1
source /work/pair_skew.tcl
unset ::ot_ps_lib_only
ot_ps_zero_unc
set M [ot_ps_measure]
ot_ps_write $M $::env(OUT)_pair.tsv ${C}_GRT
foreach dly {max min} {puts "RP1_PAIR $C $dly [dict get $M $dly]"}
# pin-register insertion (copied from signoff.py SESSION_TCL clock block)
source /work/clock_family.tcl
set so_din [all_inputs -no_clocks]
set so_regs {}
foreach p [all_registers -clock_pins] { dict set so_regs [regsub {/[^/]+$} [get_full_name $p] {}] $p }
set so_bnd {}; set so_data {}; set so_async {}
foreach p [all_registers -async_pins] { dict set so_async [get_full_name $p] 1 }
foreach p [all_registers -data_pins] { set n [get_full_name $p]; if {![dict exists $so_async $n]} { dict set so_data $n 1 } }
foreach p [get_fanout -from $so_din -flat -endpoints_only -trace_arcs all] {
  set n [get_full_name $p]
  if {![dict exists $so_data $n]} continue
  set i [regsub {/[^/]+$} $n {}]
  if {[dict exists $so_regs $i]} { dict set so_bnd $i 1 }
}
foreach p [get_fanin -to [all_outputs] -flat -startpoints_only -trace_arcs all] {
  set i [regsub {/[^/]+$} [get_full_name $p] {}]
  if {[dict exists $so_regs $i]} { dict set so_bnd $i 1 }
}
foreach c [all_clocks] { if {[llength [get_property $c sources]]} { set_clock_latency -source 0 $c } }
catch {ot_cf_refresh}
set nb 0; set sb 0.0; set mn 1e9; set mx -1e9; set na 0; set sa 0.0
dict for {i p} $so_regs {
  set cl [get_property $p clocks]
  if {[llength $cl] != 1} continue
  set a ""; catch {set a [ot_cf_wire $p [lindex $cl 0]]}
  if {$a eq ""} { catch {set a [get_property $p arrival_max_rise]} }
  if {$a eq "" || ![string is double -strict $a]} continue
  incr na; set sa [expr {$sa+$a}]
  if {[dict exists $so_bnd $i]} { incr nb; set sb [expr {$sb+$a}]; set mn [expr {min($mn,$a)}]; set mx [expr {max($mx,$a)}] }
}
puts [format "RP1_INS %s pinflops %d mean %.2f min %.2f max %.2f all %d mean_all %.2f" $C $nb [expr {$sb/max($nb,1)}] $mn $mx $na [expr {$sa/max($na,1)}]]
exit
