uplevel #0 {source /work/mscts_core.tcl; ot_ms_balance cts}
uplevel #0 {source /work/leaf_affinity.tcl}
detailed_placement
check_placement -verbose
estimate_parasitics -placement
source /work/cts_gate.tcl
