read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz
read_db /work/results/asap7/opentallas_ot_hgi_coll_qso_n2s1_b1_asap7_ref_hcoll_v7_qso_n2s1_b1_d4f_b7d189f49/base/6_final.odb
set ::ot_ce_corner ff
read_sdc /work/results/asap7/opentallas_ot_hgi_coll_qso_n2s1_b1_asap7_ref_hcoll_v7_qso_n2s1_b1_d4f_b7d189f49/base/6_final.sdc
read_spef /work/results/asap7/opentallas_ot_hgi_coll_qso_n2s1_b1_asap7_ref_hcoll_v7_qso_n2s1_b1_d4f_b7d189f49/base/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /work/w18_extra.sdc
read_sdc /meas/app0_io_ref_routed.sdc
puts "OT_WS max [sta::worst_slack_cmd max] min [sta::worst_slack_cmd min]"

if {[llength [get_ports -quiet clk_in]] && [llength [get_ports -quiet clk_out]]} {
  set ot_fc_block [ord::get_db_block]
  set ot_fc_in [[$ot_fc_block findBTerm clk_in] getNet]
  set ot_fc_out [[$ot_fc_block findBTerm clk_out] getNet]
  set ot_fc_drivers {}
  foreach it [$ot_fc_out getITerms] {
    if {[$it getIoType] eq "OUTPUT"} {lappend ot_fc_drivers $it}
  }
  if {[llength $ot_fc_drivers] != 1} {error "forwarded clk_out must have exactly one physical driver"}
  set ot_fc_it [lindex $ot_fc_drivers 0]
  set ot_fc_inst [$ot_fc_it getInst]
  set ot_fc_inputs 0
  foreach it [$ot_fc_inst getITerms] {
    if {[$it getIoType] ne "INPUT"} {continue}
    incr ot_fc_inputs
    if {[$it getNet] ne $ot_fc_in} {error "forwarded clk_out is not directly buffered from clk_in"}
  }
  if {$ot_fc_inputs != 1} {error "forwarded clk_out driver must have one input"}
  puts "OT_FC_DRIVER [[$ot_fc_inst getMaster] getName] [$ot_fc_inst getName]"
  set ot_fc_root {}
  foreach c [all_clocks] {
    foreach source [get_property $c sources] {
      if {[get_full_name $source] eq "clk_in"} {lappend ot_fc_root $c}
      if {[get_full_name $source] eq "clk_out"} {delete_clock $c}
    }
  }
  if {[llength $ot_fc_root] != 1} {error "forwarded clk_in needs exactly one source clock"}
  set ot_fc_root [lindex $ot_fc_root 0]
  set ot_fc_wave [$ot_fc_root waveform]
  if {[llength $ot_fc_wave] != 2} {error "forwarded clock needs exactly two waveform edges"}
  set_clock_latency -source 0 $ot_fc_root
  unset_input_delay [get_ports clk_in]
  set_propagated_clock [all_clocks]
  sta::find_timing_paths -path_delay max -group_path_count 1
  set ot_fc_driver_pin [get_pins "[$ot_fc_inst getName]/[[$ot_fc_it getMTerm] getName]"]
  set ot_fc_pin [sta::get_port_pin [lindex [get_ports clk_out] 0]]
  foreach prop {arrival_max_rise arrival_min_rise arrival_max_fall arrival_min_fall slew_max_rise slew_max_fall} {
    set value [get_property $ot_fc_pin $prop]
    set driver_value [get_property $ot_fc_driver_pin $prop]
    if {[string match arrival_* $prop]} {
      set edge [expr {[string match *_fall $prop] ? 1 : 0}]
      set phase [sta::time_sta_ui [lindex $ot_fc_wave $edge]]
      set value [expr {$value - $phase}]
      set driver_value [expr {$driver_value - $phase}]
    }
    puts "OT_FC_METRIC $prop $value"
    puts "OT_FC_DRIVER_METRIC $prop $driver_value"
  }
  puts "OT_FC_ROOT clk_in"
}

write_timing_model -library_name ot_hgi_coll_qso_n2s1_b1_ff /out/ot_hgi_coll_qso_n2s1_b1_ff.lib


if {[info exists ot_fc_root]} {
delete_clock [all_clocks]
write_timing_model -library_name ot_hgi_coll_qso_n2s1_b1_ff_forwarded /out/forwarded_ff.lib.raw
}
puts "OT_EXPORT_DONE"
exit
