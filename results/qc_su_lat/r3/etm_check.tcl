# etm_check.tcl -- QC-SU-LAT-R3: does the extracted timing model keep the pushdown ft clock-through / reset-through arcs?
# env: P_ODB P_SDC P_LIBS P_CORNER P_RC P_OUT (lib path).  Read-only on the kit.
set c $::env(P_CORNER)
set pat [expr {$c eq "TT" ? "*_RVT_TT_*" : "*_RVT_FF_*"}]
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/$pat] {read_liberty $l}
foreach l $::env(P_LIBS) {read_liberty $l}
read_db $::env(P_ODB)
read_sdc $::env(P_SDC)
source $::env(P_RC)
estimate_parasitics -placement
set_propagated_clock [all_clocks]
foreach p {ft_ck_i ft_rst_i} { foreach q {ft_ck_o ft_rst_o} { catch { report_checks -unconstrained -from [get_ports $p] -to [get_ports $q] -format end } r; } }
puts "ETMCHK path ft_ck_i->ft_ck_o:"; report_checks -unconstrained -from [get_ports ft_ck_i] -to [get_ports ft_ck_o] -fields {slew cap}
puts "ETMCHK path ft_rst_i->ft_rst_o:"; report_checks -unconstrained -from [get_ports ft_rst_i] -to [get_ports ft_rst_o]
write_timing_model -library_name r3_etm_$c $::env(P_OUT)
puts "ETMCHK wrote $::env(P_OUT)"
exit
