foreach f [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_FF*.lib*] {catch {read_liberty $f}}
foreach f [glob /kit/macros/*_ff.lib] {read_liberty $f}
read_db [glob /kit/run/results/asap7/*/base/4_cts.odb]
read_sdc [glob /kit/run/results/asap7/*/base/4_cts.sdc]
source /kit/vclk_ff.sdc
source /kit/setRC_rcx.tcl
estimate_parasitics -placement
set_propagated_clock [all_clocks]
report_worst_slack -min
report_checks -path_delay min -group_path_count 3 -format full_clock_expanded -fields {fanout cap slew}
