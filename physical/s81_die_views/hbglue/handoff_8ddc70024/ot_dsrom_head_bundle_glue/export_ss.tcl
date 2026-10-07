read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz
read_db /inputs/6_final.odb
read_sdc /inputs/6_final.sdc
read_spef /inputs/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /inputs/post.sdc
if {[llength [all_clocks]] != 1 || [get_full_name [lindex [all_clocks] 0]] ne "core_clk"} {error "clock mismatch"}
puts "OT_CLOCK [get_full_name [lindex [all_clocks] 0]] [get_property [lindex [all_clocks] 0] period]"
puts "OT_WS [sta::worst_slack_cmd max]"
report_checks -path_delay min_max -group_path_count 1 -format full_clock_expanded
check_setup -verbose
report_parasitic_annotation
write_sdc /out/effective_ss.sdc
set f [open /out/ports_ss.tsv w]
set block [ord::get_db_block]
puts $f "# die_area [$block getDieArea]"
foreach p [$block getBTerms] {puts $f "[$p getName]	[$p getIoType]	[$p getSigType]	[llength [$p getBPins]]"}
close $f
set f [open /out/output_slack_ss.tsv w]
foreach p [all_outputs] {puts $f "[get_full_name $p]	[get_property $p slack_min]	[get_property $p slack_max]"}
close $f
write_timing_model -library_name ot_dsrom_head_bundle_glue_ss /out/ot_dsrom_head_bundle_glue_ss.lib
write_abstract_lef /out/ot_dsrom_head_bundle_glue.lef
puts "OT_EXPORT_DONE"
exit
