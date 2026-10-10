
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /src/physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz
read_liberty /src/physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8_tt.lib
read_db /work/results/asap7/opentallas_ot_dsrom_markov_embed_localcapture_pair_asap7_md6_lookup_localcapture_statussep_b8c3158d8_tc/base/6_final.odb
read_sdc /work/results/asap7/opentallas_ot_dsrom_markov_embed_localcapture_pair_asap7_md6_lookup_localcapture_statussep_b8c3158d8_tc/base/6_final.sdc
read_spef /work/results/asap7/opentallas_ot_dsrom_markov_embed_localcapture_pair_asap7_md6_lookup_localcapture_statussep_b8c3158d8_tc/base/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /src/physical/dsrom_markov_lookup_localcapture/gen/signoff_pair.sdc
puts "OT_CORNER tt"
puts "OT_WS [sta::worst_slack_cmd max]"
puts "OT_TNS [sta::total_negative_slack_cmd max]"
report_checks -path_delay max -group_path_count 1 -format full_clock_expanded
set n 0; set wd 1e9
foreach p [get_pins -hierarchical */D] { set s [get_property $p slack_max]; if {$s ne "INF"} { if {$s < 0} { incr n }; if {$s < $wd} { set wd $s } } }
puts "OT_VIOL_D_PINS $n"
puts "OT_WS_REG_D $wd"
set wo 1e9
foreach p [all_outputs] { set s [get_property $p slack_max]; if {$s ne "INF" && $s < $wo} { set wo $s } }
puts "OT_WS_OUT $wo"
set pr [find_timing_paths -path_delay max -from [all_registers -clock_pins] -to [all_registers -data_pins] -group_path_count 1]
# find_timing_paths returns one worst path PER GROUP. Select the minimum
# across groups; index 0 can be asynchronous even when core_clk is worse.
set ot_worst INF
foreach ot_path $pr {
    set ot_slack [get_property $ot_path slack]
    if {$ot_worst eq "INF" || $ot_slack < $ot_worst} { set ot_worst $ot_slack }
}
puts "OT_WS_R2R $ot_worst"
set pi [find_timing_paths -path_delay max -from [all_inputs] -to [all_registers -data_pins] -group_path_count 1]
# find_timing_paths returns one worst path PER GROUP. Select the minimum
# across groups; index 0 can be asynchronous even when core_clk is worse.
set ot_worst INF
foreach ot_path $pi {
    set ot_slack [get_property $ot_path slack]
    if {$ot_worst eq "INF" || $ot_slack < $ot_worst} { set ot_worst $ot_slack }
}
puts "OT_WS_I2R $ot_worst"

foreach ot_port [all_outputs] {puts "OT_I16_OUTPUT [get_full_name $ot_port]"}
write_sdc /receipt/effective.sdc
puts OT_I16_ELECTRICAL_BEGIN
report_check_types -max_slew -max_cap -max_fanout -violators
puts OT_I16_ELECTRICAL_END
set ot_block [ord::get_db_block]
set ot_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set ot_captures 0;set ot_max_distance 0.0
set ot_row_mismatch 0
foreach ot_macro [$ot_block getInsts] {
 if {[[$ot_macro getMaster] getName] ne "ot_rom_4096x274_m8"} {continue}
 foreach ot_q [$ot_macro getITerms] {
  set ot_pn [[$ot_q getMTerm] getName]
  if {![regexp {^rd_out\[([0-9]+)\]$} $ot_pn -> ot_bit] || $ot_bit>=256} {continue}
  set ot_inputs {}
  foreach ot_t [[$ot_q getNet] getITerms] {
   if {$ot_t ne $ot_q && [$ot_t getIoType] eq "INPUT"} {lappend ot_inputs $ot_t}
  }
  if {[llength $ot_inputs]!=1} {error "payload output requires one direct capture sink"}
  set ot_d [lindex $ot_inputs 0];set ot_ff [$ot_d getInst]
  if {[[$ot_d getMTerm] getName] ne "D" || ![string match *DFF* [[$ot_ff getMaster] getName]]} {error "logic before macro capture"}
  set ot_fb [$ot_ff getBBox];set ot_rows {}
  foreach ot_row [$ot_block getRows] {
   set ot_rb [$ot_row getBBox]
   if {[$ot_fb yMin]==[$ot_rb yMin] && [$ot_fb xMin]>=[$ot_rb xMin] && [$ot_fb xMax]<=[$ot_rb xMax]} {lappend ot_rows $ot_row}
  }
  if {[llength $ot_rows]!=1 || [$ot_ff getOrient] ne [[lindex $ot_rows 0] getOrient]} {incr ot_row_mismatch}
  set ot_qxy [$ot_q getAvgXY];set ot_dxy [$ot_d getAvgXY]
  if {![lindex $ot_qxy 0] || ![lindex $ot_dxy 0]} {error "unplaced capture pin"}
  set ot_distance [expr {(abs([lindex $ot_qxy 1]-[lindex $ot_dxy 1])+abs([lindex $ot_qxy 2]-[lindex $ot_dxy 2]))/double($ot_dbu)}]
  set ot_max_distance [expr {max($ot_max_distance,$ot_distance)}]
  incr ot_captures
 }
}
set ot_leaves 0;set ot_max_leaf 0
foreach ot_net [$ot_block getNets] {
 set ot_clockpins 0;set ot_inputs 0
 foreach ot_t [$ot_net getITerms] {
  if {[$ot_t getIoType] ne "INPUT"} {continue}
  incr ot_inputs
  if {[[$ot_t getMTerm] getName] in {CLK CK clk}} {incr ot_clockpins}
 }
 if {$ot_clockpins>0} {incr ot_leaves;set ot_max_leaf [expr {max($ot_max_leaf,$ot_inputs)}]}
}
puts "OT_I16_CAPTURES $ot_captures"
puts "OT_I16_CAPTURE_DISTANCE $ot_max_distance"
puts "OT_I16_ROW_MISMATCH $ot_row_mismatch"
puts "OT_I16_CLOCK_LEAVES $ot_leaves"
puts "OT_I16_CLOCK_LEAF_MAX $ot_max_leaf"
check_power_grid -net VDD
puts OT_I16_PG_VDD_PASS
check_power_grid -net VSS
puts OT_I16_PG_VSS_PASS
exit
