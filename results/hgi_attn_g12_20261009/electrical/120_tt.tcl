
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef

read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz

read_db /work/results/asap7/opentallas_ot_hgi_att_row_sources_p_asap7_qdm_hgi_att_g12_120_187a8471c_tc_cx/base/6_final.odb
read_sdc /work/results/asap7/opentallas_ot_hgi_att_row_sources_p_asap7_qdm_hgi_att_g12_120_187a8471c_tc_cx/base/6_final.sdc
read_spef /work/results/asap7/opentallas_ot_hgi_att_row_sources_p_asap7_qdm_hgi_att_g12_120_187a8471c_tc_cx/base/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /src/physical/qwen_die_masters/signoff/hgi_att_rows_g12_120.sdc
puts "OT_WS_MAX [sta::worst_slack_cmd max] OT_WS_MIN [sta::worst_slack_cmd min]"
report_clock_latency -include_internal_latency

puts OT_ELECTRICAL_BEGIN
report_check_types -max_slew -max_capacitance -max_fanout -violators
puts OT_ELECTRICAL_END
set block [ord::get_db_block]
set max_all 0
set max_clock 0
set count_clock 0
foreach net [$block getNets] {
 set n 0
 foreach term [$net getITerms] {if {[$term getIoType] eq "INPUT"} {incr n}}
 if {$n>$max_all} {set max_all $n}
 if {[$net getSigType] eq "CLOCK"} {
  incr count_clock
  if {$n>$max_clock} {set max_clock $n}
 }
}
puts "OT_DB_FANOUT max_all=$max_all clock_nets=$count_clock max_clock_net_inputs=$max_clock"
puts OT_AUDIT_DONE
exit
