foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_FF*.lib* /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*LVT_FF*.lib*] { read_liberty $l }
read_db $::env(ODB)
read_sdc $::env(SDC)
set_propagated_clock [all_clocks]
if {[file exists /work/setRC_rcx.tcl]} { source /work/setRC_rcx.tcl } else { source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl }
estimate_parasitics -placement
report_checks -path_delay min -to [all_outputs] -group_path_count 100000 -endpoint_path_count 1 -format full_clock_expanded -digits 2 > /probe/$::env(TAG)_out.rpt
