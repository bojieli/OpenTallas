
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef

read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz

read_db /work/results/asap7/opentallas_ot_v41_pqc_spine_screen_asap7_dsfs13_c1r16_ek/base/6_final.odb
read_sdc /work/results/asap7/opentallas_ot_v41_pqc_spine_screen_asap7_dsfs13_c1r16_ek/base/6_final.sdc
read_spef /work/results/asap7/opentallas_ot_v41_pqc_spine_screen_asap7_dsfs13_c1r16_ek/base/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /src/physical/dsrom_field_spine/signoff_r16.sdc
set count 0
foreach p [get_pins -hierarchical */D] {
 set name [get_full_name $p]
 if {[regexp {(^|/)(q_rv|q_re|q_row|q_pos|q_f32|q_bf)} $name]} {
 incr count
 puts "PQ_SLACK\t$name\t[get_property $p slack_min]"
 }
}
puts "PQ_COUNT $count"
exit
