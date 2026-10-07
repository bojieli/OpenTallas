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
report_parasitic_annotation -report_unannotated
set block [ord::get_db_block]
set f [open /out/unannotated_net_kinds.tsv w]
foreach n [$block getNets] {
 set drivers {}
 foreach it [$n getITerms] {if {[$it getIoType] eq "OUTPUT"} {lappend drivers "[[$it getInst] getName]/[[$it getMTerm] getName]:[[[$it getInst] getMaster] getName]"}}
 puts $f "[$n getName]\t[$n getSigType]\t[join $drivers ,]"
}
close $f
set box [$block getDieArea]
puts "OT_DIE_DBU [$box xMin] [$box yMin] [$box xMax] [$box yMax] [$block getDbUnitsPerMicron]"
puts "OT_DIAGNOSTIC_DONE"
exit
