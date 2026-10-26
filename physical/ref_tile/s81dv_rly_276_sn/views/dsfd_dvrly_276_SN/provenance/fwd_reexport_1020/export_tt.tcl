read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz
read_db /work/results/asap7/opentallas_dsfd_dvrly_276_SN_asap7_ref_s81dv_rly_276_sn_dv4c_33a9d31b4/base/6_final.odb
set ::ot_ce_corner tt
read_sdc /work/results/asap7/opentallas_dsfd_dvrly_276_SN_asap7_ref_s81dv_rly_276_sn_dv4c_33a9d31b4/base/6_final.sdc
read_spef /work/results/asap7/opentallas_dsfd_dvrly_276_SN_asap7_ref_s81dv_rly_276_sn_dv4c_33a9d31b4/base/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /work/w18_extra.sdc
read_sdc /meas/app0_io_ref_routed.sdc
puts "OT_WS max [sta::worst_slack_cmd max] min [sta::worst_slack_cmd min]"

if {[llength [get_ports -quiet ck]] && [llength [get_ports -quiet ck_o]]} {
  set ot_fc_block [ord::get_db_block]
  set ot_fc_in [[$ot_fc_block findBTerm ck] getNet]
  set ot_fc_net [[$ot_fc_block findBTerm ck_o] getNet]
  set ot_fc_chain {}
  set ot_fc_it {}
  while {1} {
    set ot_fc_drivers {}
    foreach it [$ot_fc_net getITerms] {
      if {[$it getIoType] eq "OUTPUT"} {lappend ot_fc_drivers $it}
    }
    if {[llength $ot_fc_drivers] != 1} {error "forwarded ck_o chain net [$ot_fc_net getName] must have exactly one physical driver"}
    set ot_fc_d [lindex $ot_fc_drivers 0]
    if {$ot_fc_it eq {}} {set ot_fc_it $ot_fc_d}
    set ot_fc_ci [$ot_fc_d getInst]
    set ot_fc_ins {}
    foreach it [$ot_fc_ci getITerms] {
      if {[$it getIoType] eq "INPUT" && [$it getNet] ne "NULL"} {lappend ot_fc_ins $it}
    }
    if {[llength $ot_fc_ins] != 1} {error "forwarded ck_o chain cell [$ot_fc_ci getName] must have one input"}
    lappend ot_fc_chain $ot_fc_ci
    puts "OT_FC_CHAIN [[$ot_fc_ci getMaster] getName] [$ot_fc_ci getName]"
    set ot_fc_net [[lindex $ot_fc_ins 0] getNet]
    if {$ot_fc_net eq $ot_fc_in} {break}
    if {[llength $ot_fc_chain] >= 16} {error "forwarded ck_o chain longer than 16 cells"}
  }
  set ot_fc_inst [$ot_fc_it getInst]
  puts "OT_FC_DRIVER [[$ot_fc_inst getMaster] getName] [$ot_fc_inst getName]"
  set ot_fc_root {}
  foreach c [all_clocks] {
    foreach source [get_property $c sources] {
      if {[get_full_name $source] eq "ck"} {lappend ot_fc_root $c}
      if {[get_full_name $source] eq "ck_o"} {delete_clock $c}
    }
  }
  if {[llength $ot_fc_root] != 1} {error "forwarded ck needs exactly one source clock"}
  set ot_fc_root [lindex $ot_fc_root 0]
  set ot_fc_wave [$ot_fc_root waveform]
  if {[llength $ot_fc_wave] != 2} {error "forwarded clock needs exactly two waveform edges"}
  set_clock_latency -source 0 $ot_fc_root
  unset_input_delay [get_ports ck]
  set_propagated_clock [all_clocks]
  sta::find_timing_paths -path_delay max -group_path_count 1
  set ot_fc_driver_pin [get_pins "[$ot_fc_inst getName]/[[$ot_fc_it getMTerm] getName]"]
  set ot_fc_pin [sta::get_port_pin [lindex [get_ports ck_o] 0]]
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
  puts "OT_FC_ROOT ck"
}

write_timing_model -library_name dsfd_dvrly_276_SN_tt /out/dsfd_dvrly_276_SN_tt.lib


if {[info exists ot_fc_root]} {
delete_clock [all_clocks]
write_timing_model -library_name dsfd_dvrly_276_SN_tt_forwarded /out/forwarded_tt.lib.raw
}
puts "OT_EXPORT_DONE"
exit
