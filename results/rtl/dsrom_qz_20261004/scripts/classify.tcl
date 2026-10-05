# Detailed path dump for classification: top N endpoints, full clock expanded.
set C $::env(CORNER)
set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach f [list asap7sc7p5t_AO_RVT_${C}_nldm_211120.lib.gz asap7sc7p5t_INVBUF_RVT_${C}_nldm_220122.lib.gz asap7sc7p5t_OA_RVT_${C}_nldm_211120.lib.gz asap7sc7p5t_SIMPLE_RVT_${C}_nldm_211120.lib.gz] { read_liberty $L/$f }
read_liberty [lindex [glob $L/asap7sc7p5t_SEQ_RVT_${C}_nldm_*.lib*] 0]
read_liberty /src/physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8_[string tolower $C].lib
read_db $::env(ODB)
read_sdc $::env(SDC)
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
if {[info exists ::env(SPEF)] && $::env(SPEF) ne ""} { read_spef $::env(SPEF) } else { estimate_parasitics -placement }
set_propagated_clock [all_clocks]
set kind [expr {$C eq "FF" ? "min" : "max"}]
set N $::env(NPATH)
report_checks -path_delay $kind -path_group core_clk -group_path_count $N -endpoint_path_count 1 -format full_clock_expanded -fields {fanout} -digits 1 > $::env(OUT).all.paths
report_checks -path_delay $kind -path_group core_clk -to [all_registers -data_pins] -group_path_count $N -endpoint_path_count 1 -format full_clock_expanded -fields {fanout} -digits 1 > $::env(OUT).reg.paths
report_clock_skew > $::env(OUT).skew
report_clock_min_period > $::env(OUT).minper
report_checks -path_delay $kind -path_group asynchronous -group_path_count $N -endpoint_path_count 1 -format full_clock_expanded -fields {fanout} -digits 1 > $::env(OUT).async.paths
foreach icg [get_cells -hierarchical *u_icg*] { puts "ICG [get_full_name $icg]" }
report_checks -path_delay $kind -to [get_pins -hierarchical *u_icg/ENA] -group_path_count 5 -format full_clock_expanded -digits 1 > $::env(OUT).icg.paths
