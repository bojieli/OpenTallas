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
# SENSITIVITY ONLY (not sign-off): the output hold budget re-derived per corner.  The run SDC's -0.56 ns is the SS clock
# insertion of a receiving q element; here it is replaced by OMIN, in library time units (ps), = -(the FF clock
# insertion of this block's free-clock boundary registers, measured: 321.8 ps on R_cap0).
puts "OT_SENS_OMIN $::env(OMIN)"
set_output_delay -min $::env(OMIN) -clock core_clk [all_outputs]
puts "OT_SENS_MIN_WNS_ALL [sta::worst_slack -min]"
report_checks -path_delay min -to [all_outputs] -group_path_count 3 -format full_clock -digits 1 > $::env(OUT).out_min_sens.paths
report_checks -path_delay min -to [all_registers -data_pins] -group_path_count 3 -format full_clock -digits 1 > $::env(OUT).reg_min.paths
report_checks -path_delay min -to [all_outputs] -group_path_count 1 -format end > $::env(OUT).out_min_sens.end
