# INFRA-FIRST-HEAD-3 PG: worst-case power of a head hard core from its GRT netlist (OpenSTA report_power, TT).
# env: OT_NICK (hd_elemA_rb|hd_elemB_rb), OT_ACT (data toggle activity per cycle, -global), OT_TAG
foreach f [lsort [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_TT_nldm_*.lib*]] { read_liberty $f }
foreach f [glob /work/macros/*_tt.lib] { read_liberty $f }
read_db /work/odb/5_1_grt.odb
read_sdc /work/constraint.sdc
set ::env(OT_RC_CAL) 0.8,0.9
source /work/cf/rc_cal.tcl
estimate_parasitics -global_routing
set_propagated_clock [all_clocks]
set a $::env(OT_ACT)
set_power_activity -global -activity $a -duty 0.5
set_power_activity -input -activity $a -duty 0.5
puts "OT_CELLS [llength [get_cells -hier *]] OT_REGS [llength [all_registers]]"
set da [[ord::get_db_block] getDieArea]
puts "OT_DIE_UM [expr {[$da dx]/1000.0}] [expr {[$da dy]/1000.0}]"
report_power -digits 6 > /work/power_$::env(OT_TAG).rpt
report_power -digits 6
exit
