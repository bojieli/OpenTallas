# DIE-HEAD-21: classify the DH19 post-GRT repair worst path (u_cland_i ring writer s_d D), GRT RC, no repair.
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_TT*] { read_liberty $l }
foreach l [glob /work/macros/*_tt.lib] { read_liberty $l }
read_db $::env(ODB)
read_sdc /work/constraint.sdc
set_propagated_clock [all_clocks]
source /work/setRC_rcx.tcl
read_spef $::env(SPEF)
report_worst_slack -max
report_tns
foreach ep {u_cland_i/u_ring.s_d\[2\]\[260\]$_DFFE_PP_/D u_cland_i/u_ring.s_d\[1\]\[257\]$_DFFE_PP_/D} {
  report_checks -path_delay max -to [get_pins $ep] -format full_clock_expanded -fields {slew cap fanout input_pin} -digits 1
}
report_checks -path_delay max -group_path_count 5 -endpoint_path_count 1 -format end -digits 1
# endpoint classes: ring writer D pins vs others
set n 0; set nr 0
foreach p [get_pins -hierarchical *s_d*/D] { incr nr }
puts "RINGD_PINS $nr"
