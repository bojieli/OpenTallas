# R16 read-only probe (HEAD-CORE-R16 root cause): register CLK rise arrival min/mean/max at OT_CORNER on 4_cts.odb,
# placement parasitics (setRC), propagated clock; plus worst hold slack with vclk at the kit's per-corner value.
set C $::env(OT_CORNER); set c [string tolower $C]
set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach f [lsort [glob $L/asap7sc7p5t_*_RVT_${C}_nldm_*.lib*]] { read_liberty $f }
foreach f [glob -nocomplain /work/macros/*_${c}.lib] { read_liberty $f }
read_db /work/run/results/asap7/$::env(NICK)/base/4_cts.odb
read_sdc /work/constraint.sdc
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
set_propagated_clock [get_clocks clk]
estimate_parasitics -placement
set_clock_latency -source $::env(VCLK) [get_clocks vclk]
set s 0.0; set n 0; set mn 1e9; set mx -1e9
foreach p [all_registers -clock_pins] {
  if {[catch {set a [get_property $p arrival_max_rise]}] || $a eq ""} continue
  set s [expr {$s+$a}]; incr n; if {$a<$mn} {set mn $a}; if {$a>$mx} {set mx $a}
}
puts [format "INSPROBE %s %s vclk %s n %d ck_min %.1f mean %.1f max %.1f hold_wns %.1f hold_viol %d" $::env(NICK) $C $::env(VCLK) $n $mn [expr {$s/$n}] $mx [sta::time_sta_ui [sta::worst_slack_cmd min]] [sta::endpoint_violation_count min]]
exit
