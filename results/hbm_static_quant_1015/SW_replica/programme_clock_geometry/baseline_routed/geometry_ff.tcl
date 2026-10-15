
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /src/physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz
read_liberty /src/physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2_ff.lib
read_db /work/results/asap7/opentallas_ot_hgi_qdq_sw_program_leaf_asap7_ref_gate/base/6_final.odb
set ::ot_ce_corner ff
read_sdc /work/results/asap7/opentallas_ot_hgi_qdq_sw_program_leaf_asap7_ref_gate/base/6_final.sdc
read_spef /work/results/asap7/opentallas_ot_hgi_qdq_sw_program_leaf_asap7_ref_gate/base/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /src/physical/ref_tile/hgi_qdq_program_sw125/signoff.sdc

sta::worst_slack_cmd max
set f [open /work/geometry_ff.tsv w]
set block [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set ot_missing 0
foreach p [all_registers -clock_pins] {
 set n [get_full_name [get_cells -of_objects $p]]
 set i [$block findInst [string map [list {[} {\[} {]} {\]}] $n]]
 if {$i eq "NULL"} {incr ot_missing;if {$ot_missing<=4} {puts "NO_ODB_INSTANCE $n"};continue}
 lassign [$i getLocation] x y
 puts $f "$n	[[$i getMaster] getName]	[expr {double($x)/$dbu}]	[expr {double($y)/$dbu}]	[get_property $p arrival_max_rise]"
}
close $f
foreach p [find_timing_paths -path_delay min -to [get_ports command*] -group_path_count 5000 -endpoint_path_count 1] {
 puts "COMMAND_HOLD [get_full_name [get_property $p endpoint]] [get_property $p slack]"
}
report_checks -path_delay min -to [get_ports command*] -group_path_count 48 -endpoint_path_count 1 -format full_clock_expanded
exit
