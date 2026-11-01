
foreach f [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*RVT_FF_nldm_*] { read_liberty $f }
foreach f [glob /work/macros/*_ff.lib] { read_liberty $f }
read_db /work/z$::env(SWAP).odb
read_sdc /work/probe_in.sdc
source /work/vclk_ff.sdc
source /work/setRC_rcx.tcl
set_propagated_clock [all_clocks]
estimate_parasitics -placement
puts "CODEX FF AFTER"
report_worst_slack -min
report_checks -path_delay min -group_path_count 5 -endpoint_path_count 1 -format end
