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
set_propagated_clock [all_clocks]
report_checks -path_delay max -to [all_outputs] -group_path_count 3 -format full_clock -digits 1 > $::env(OUT).out_max.paths
report_checks -path_delay min -to [all_outputs] -group_path_count 3 -format full_clock -digits 1 > $::env(OUT).out_min.paths
report_checks -path_delay min -from [all_inputs] -group_path_count 3 -format full_clock -digits 1 > $::env(OUT).in_min.paths
report_checks -path_delay max -from [all_inputs] -group_path_count 3 -format full_clock -digits 1 > $::env(OUT).in_max.paths
puts "OT_MIN_WNS_REG [sta::worst_slack -min]"
