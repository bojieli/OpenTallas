set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [lsort [glob $P/lib/NLDM/*_RVT_SS_*.lib*]] { read_liberty $f }
read_db /route/6_final.odb
read_sdc /route/6_final.sdc
read_spef /route/6_final.spef
set_propagated_clock [all_clocks]
report_worst_slack -max -digits 6
