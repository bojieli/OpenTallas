foreach f {asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib} { read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/$f }
read_liberty /work/macros/ot_sram_1r1w_128x256_m1_r2c2_tt.lib
read_db /work/run/results/asap7/hbc_ot_hbm_su_static_pgslice_lg__lanes__canon_cf1e77/base/3_place.odb
read_sdc /out/3_place_rstio.sdc
source /work/setRC_rcx.tcl
estimate_parasitics -placement
puts "WNS_ALL [sta::worst_slack_cmd max]"
set mp [get_pins -of_objects [get_cells -filter "ref_name =~ ot_sram*" *] ]
puts "NMACROPINS [llength $mp]"
set ins {}; set outs {}
foreach p $mp { if {[get_property $p direction] == "input"} {lappend ins $p} else {lappend outs $p} }
puts "TO_MACRO"; report_checks -path_delay max -to $ins -format end -group_path_count 1
report_checks -path_delay max -to $ins -fields {cap slew fanout} -digits 1
puts "FROM_MACRO"; report_checks -path_delay max -through $outs -digits 1
puts "REG2REG"; report_checks -path_delay max -from [all_registers] -to [all_registers] -format end
report_tns
puts "WORST_FULL"; report_checks -path_delay max -group_path_count 1 -fields {fanout cap slew} -digits 1
puts "RESET_PATHS"; report_checks -path_delay max -from [get_ports {rst_lane_n* rst_n}] -format end -group_path_count 3
report_checks -path_delay max -from [get_ports {rst_lane_n* rst_n}] -digits 1
puts "M2"; report_checks -path_delay max -to [get_pins -hierarchical *u_m2*s1_rows*/D] -digits 1 -fields {fanout}
puts "HOLD"; report_checks -path_delay min -format end -group_path_count 1
report_tns
report_worst_slack -max
