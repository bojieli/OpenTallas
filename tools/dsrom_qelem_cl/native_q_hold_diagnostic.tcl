# Read-only FF diagnostic of pinned QS5f calibration CTS; original DB/SDC remain immutable.
set plat /OpenROAD-flow-scripts/flow/platforms/asap7
foreach l [glob $plat/lib/NLDM/*RVT_FF*] { read_liberty $l }
foreach l [glob $plat/lib/NLDM/*_LVT_FF_* $plat/lib/NLDM/*_SLVT_FF_*] {
  if {![string match *FAKE* $l]} { read_liberty $l }
}
read_liberty /src/physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8_ff.lib
read_db /base/4_1_cts.odb
read_sdc /base/4_cts.sdc
source $plat/setRC.tcl
estimate_parasitics -placement
set_propagated_clock [all_clocks]
puts "QS5F_ORIGINAL_CTS_FF"
report_checks -path_delay min -from [all_inputs -no_clocks] -group_path_count 10 -format full_clock_expanded -fields {slew cap fanout input_pin net}
read_sdc /src/physical/abi3/gen/dsrom_q_cl_signoff.sdc
read_sdc /src/.ot_mm/io_ref_routed.sdc
puts "QS5F_POST_SDC_FF"
report_checks -path_delay min -from [all_inputs -no_clocks] -group_path_count 20 -format full_clock_expanded -fields {slew cap fanout input_pin net}
puts "QS5F_INTERNAL_FF"
report_checks -path_delay min -from [all_registers -clock_pins] -to [all_registers -data_pins] -group_path_count 5 -format full_clock_expanded -fields {slew cap fanout input_pin net}
exit
