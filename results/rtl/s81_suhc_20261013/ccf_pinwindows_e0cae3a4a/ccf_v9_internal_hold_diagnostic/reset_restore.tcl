
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_FF*] { read_liberty $l }
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_LVT_FF_* /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_SLVT_FF_*] { if {![string match *FAKE* $l]} { read_liberty $l } }
read_liberty /src/physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2_ff.lib
read_db /diag/internal_hold_candidate.odb
read_sdc /base/4_cts.sdc
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
estimate_parasitics -placement
set_propagated_clock [all_clocks]

write_sdc /diag/semantic_before.sdc
set ports [all_inputs -no_clocks]
set_false_path -hold -from $ports
unset_path_exceptions -hold -from $ports
write_sdc /diag/semantic_after.sdc
puts "RESET_PATH_RESTORED"
exit
