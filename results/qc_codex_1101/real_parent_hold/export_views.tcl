set C $::env(OT_CORNER)
set c [string tolower $C]
set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach f [lsort [glob $L/asap7sc7p5t_*_RVT_${C}_nldm_*.lib*]] { read_liberty $f }
set base /work/run/results/asap7/$::env(TOP)/base
read_db $base/6_final.odb
read_sdc $base/6_final.sdc
read_spef $base/6_final.spef
set_propagated_clock [get_clocks clk]
set_clock_latency -source 0 [all_clocks]
write_timing_model /work/views/$::env(TOP)_${c}.lib
puts "ACTUAL_ROUTED_ETM $::env(TOP) $C"

write_abstract_lef /work/views/$::env(TOP)_raw.lef
