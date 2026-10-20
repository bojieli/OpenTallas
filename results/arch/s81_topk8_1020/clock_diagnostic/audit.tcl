set corner $::env(AUDIT_CORNER)
set lc [string tolower $corner]
set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [glob $P/lib/NLDM/asap7sc7p5t_*_RVT_${corner}_nldm_*.lib*] {read_liberty $f}
foreach v {physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2_p192_mir physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1_p192_rc physical/ref_tile/s81dvbk_hist32_b0r3/views/ot_s81ph_native_sel_hist_bank} {
 foreach f [glob /src/$v/*_${lc}.lib] {puts "ACTUAL_LIB $f";read_liberty $f}
}
set B [glob /work/results/asap7/*/base]
read_db $B/3_place.odb
read_sdc $B/3_place.sdc
source $P/setRC.tcl
estimate_parasitics -placement
puts "SCOPE IMMUTABLE_PRE_CTS_3_PLACE_IDEAL_CLOCKS $corner"
report_worst_slack -min
report_worst_slack -max
set fifo [get_pins -hierarchical {*u_fq*wd_in* *u_ofq*wd_in*}]
puts "FIFO_ENDPOINTS [llength $fifo]"
report_checks -to $fifo -path_delay min -group_path_count 5 -endpoint_path_count 1 -format full_clock_expanded -fields {fanout cap slew input_pins nets} -digits 3
report_checks -to $fifo -path_delay max -group_path_count 5 -endpoint_path_count 1 -format full_clock_expanded -fields {fanout cap slew input_pins nets} -digits 3
puts "ALL_WORST_PATHS"
report_checks -path_delay min_max -group_path_count 3 -endpoint_path_count 1 -format full_clock_expanded -fields {fanout cap slew input_pins nets} -digits 3
