
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_FF*] { read_liberty $l }
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_LVT_FF_* /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_SLVT_FF_*] { if {![string match *FAKE* $l]} { read_liberty $l } }
read_liberty /src/physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2_ff.lib
read_db /base/4_1_cts.odb
read_sdc /base/4_cts.sdc
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
estimate_parasitics -placement
set_propagated_clock [all_clocks]

# Diagnostic ODB copy only. Source SDC is unchanged; fresh final STA re-reads it.
set ot_external [all_inputs -no_clocks]
set_false_path -hold -from $ot_external
set_dont_use {*x1p*_ASAP7* *xp*_ASAP7* SDF* ICG*}
unset_dont_use [get_lib_cells {*/HB1xp67_ASAP7_75t_R */HB2xp67_ASAP7_75t_R}]
puts "CCF_INTERNAL_HOLD_BEFORE"
report_checks -path_delay min -group_path_count 4 -fields {slew capacitance fanout input_pin net} -digits 5
repair_timing -hold -hold_margin 15 -max_buffer_percent 10 -max_iterations 1000 -verbose
detailed_placement
estimate_parasitics -placement
puts "CCF_INTERNAL_HOLD_AFTER"
report_checks -path_delay min -group_path_count 4 -fields {slew capacitance fanout input_pin net} -digits 5
write_db /diag/internal_hold_candidate.odb
exit
