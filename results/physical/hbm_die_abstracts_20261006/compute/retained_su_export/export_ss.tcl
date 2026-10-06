read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz
read_db /base/6_final.odb
read_sdc /out/interface.sdc
read_spef /base/6_final.spef
set_propagated_clock [all_clocks]
report_units
report_clock_properties [all_clocks]
write_timing_model -library_name ot_su12_full_ss /out/ot_su12_full_ss.lib
write_abstract_lef /out/ot_su12_full.lef
set fp [open /out/pins.tsv w]
puts $fp "pin	direction	signal_type	layer	xmin_um	ymin_um	xmax_um	ymax_um"
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
puts "OT_DBU $dbu"
foreach bt [$block getBTerms] {
  foreach bp [$bt getBPins] {
    foreach box [$bp getBoxes] {
      puts $fp [join [list [$bt getName] [$bt getIoType] [$bt getSigType] [[$box getTechLayer] getName] [expr {double([$box xMin])/$dbu}] [expr {double([$box yMin])/$dbu}] [expr {double([$box xMax])/$dbu}] [expr {double([$box yMax])/$dbu}]] "\t"]
    }
  }
}
close $fp
puts "OT_EXPORT_DONE"
exit
