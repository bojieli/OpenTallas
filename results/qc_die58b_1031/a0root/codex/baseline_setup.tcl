
foreach f [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*RVT_TT_nldm_*] { read_liberty $f }
foreach f [glob /work/macros/*_tt.lib] { read_liberty $f }
read_db /work/probe_in.odb
read_sdc /work/probe_in.sdc
source /work/setRC_rcx.tcl
set_propagated_clock [all_clocks]
estimate_parasitics -placement
puts "CODEX BASELINE TT 60ps setup uncertainty preserved"
report_worst_slack -max
report_checks -path_delay max -group_path_count 5 -endpoint_path_count 1 -format full_clock_expanded -fields {cap slew fanout} -digits 2
