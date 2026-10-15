read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /mv0/ot_sram_1r1w_128x66_m1_r2c2.lef
read_lef /mv1/ot_sram_1r1w_256x34_m2_r2c2.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz
read_liberty /mv0/ot_sram_1r1w_128x66_m1_r2c2_ff.lib
read_liberty /mv1/ot_sram_1r1w_256x34_m2_r2c2_ff.lib
read_db /work/results/asap7/opentallas_dsfd_gth_re_asap7_ref_gate/base/4_cts.odb
read_sdc /work/results/asap7/opentallas_dsfd_gth_re_asap7_ref_gate/base/4_cts.sdc
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
estimate_parasitics -placement
set_propagated_clock [all_clocks]
source /diag/a34_shared_leaf.tcl
s81_a34_shared_leaf
estimate_parasitics -placement
set pp [get_pins -hierarchical *a4_v*/D]
puts "A4_PINS $pp"
report_checks -to $pp -path_delay min -format full_clock_expanded -digits 4 -group_path_count 16
set b [ord::get_db_block];set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
foreach inst [$b getInsts] {
 if {[regexp {a[34]_v.*DFF} [$inst getName]] && [$inst findITerm CLK] ne "NULL"} {puts "A34_LOC [$inst getName] [$inst getLocation] [[$inst findITerm CLK] getNet]"}
}
exit
