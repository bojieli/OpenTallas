read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /mv0/qkd_ectl_b_tp8_direct.lef
read_lef /mv1/qkd_ectl_c_st.lef
read_lef /mv2/qkd_static_ectla_kiss.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz
read_liberty /mv0/qkd_ectl_b_tp8_direct_ss.lib
read_liberty /mv1/qkd_ectl_c_st_ss.lib
read_liberty /mv2/qkd_static_ectla_kiss_ss.lib
read_db /work/results/asap7/opentallas_qkd_ectl3_kiss_st_asap7_ref_qkd_ectl3_kiss_st_e5_188da89ab/base/6_final.odb
set ::ot_ce_corner ss
read_sdc /work/results/asap7/opentallas_qkd_ectl3_kiss_st_asap7_ref_qkd_ectl3_kiss_st_e5_188da89ab/base/6_final.sdc
read_spef /work/results/asap7/opentallas_qkd_ectl3_kiss_st_asap7_ref_qkd_ectl3_kiss_st_e5_188da89ab/base/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /work/w18_extra.sdc
read_sdc /meas/app0_io_ref_routed.sdc
# Audit the ACTUAL final routed OpenDB by net type. A lower signal ceiling
# never lowers the PG ceiling and never exempts clock nets or contact vias.
# The exporter re-runs this on final6_final.odb after any hold ECO.
proc ot_ref_json_layers {counts} {
  set out {}
  foreach layer [lsort [dict keys $counts]] { lappend out "\"$layer\":[dict get $counts $layer]" }
  return "{[join $out ,]}"
}
proc ot_ref_audit_signal_layers {signal_cap pg_cap output} {
  set tech [ord::get_db_tech]
  set sl [$tech findLayer $signal_cap]; set pl [$tech findLayer $pg_cap]
  if {$sl eq "NULL" || $pl eq "NULL"} { error "SIGNAL_LAYER_AUDIT: unknown layer" }
  set sigmax [$sl getRoutingLevel];set pgmax [$pl getRoutingLevel]
  if {$sigmax < 2 || $sigmax > $pgmax} {error "SIGNAL_LAYER_AUDIT: invalid signal/PG contract"}
  set signal [dict create];set power [dict create];set violations [dict create]
  set block [ord::get_db_block]
  foreach net [$block getNets] {
    set pg [expr {[$net getSigType] in {POWER GROUND}}]
    set limit [expr {$pg ? $pgmax : $sigmax}]
    set wire [$net getWire]
    if {$wire ne "NULL"} {
      set dec [odb::dbWireDecoder];$dec begin $wire
      while {[set op [$dec next]] != $odb::dbWireDecoder_END_DECODE} {
        set layers {}
        if {$op == $odb::dbWireDecoder_POINT || $op == $odb::dbWireDecoder_POINT_EXT} {
          lappend layers [$dec getLayer]
        } elseif {$op == $odb::dbWireDecoder_TECH_VIA || $op == $odb::dbWireDecoder_VIA} {
          if {$op == $odb::dbWireDecoder_TECH_VIA} {set via [$dec getTechVia]} else {set via [$dec getVia]}
          foreach box [$via getBoxes] {lappend layers [$box getTechLayer]}
        }
        foreach layer $layers {
          if {$layer eq "NULL" || [$layer getRoutingLevel] <= 0} continue
          set name [$layer getName]
          if {$pg} {dict incr power $name} else {dict incr signal $name}
          if {[$layer getRoutingLevel] > $limit} {dict incr violations "[$net getSigType]:$name"}
        }
      }
    }
    # PG lives primarily in special wires; retain their real layer evidence.
    foreach sw [$net getSWires] {
      foreach box [$sw getWires] {
        set layers {}
        if {[$box isVia]} {
          if {[$box getTechVia] ne "NULL"} {set via [$box getTechVia]} else {set via [$box getBlockVia]}
          foreach vb [$via getBoxes] {lappend layers [$vb getTechLayer]}
        } else {lappend layers [$box getTechLayer]}
        foreach layer $layers {
          if {$layer eq "NULL" || [$layer getRoutingLevel] <= 0} continue
          set name [$layer getName]
          if {$pg} {dict incr power $name} else {dict incr signal $name}
          if {[$layer getRoutingLevel] > $limit} {dict incr violations "[$net getSigType]:$name"}
        }
      }
    }
  }
  foreach term [$block getBTerms] {
    if {[$term getSigType] in {POWER GROUND}} continue
    foreach pin [$term getBPins] {foreach box [$pin getBoxes] {
      set layer [$box getTechLayer]
      if {$layer ne "NULL" && [$layer getRoutingLevel] > $sigmax} {dict incr violations "PIN:[$layer getName]"}
    }}
  }
  set fd [open $output w]
  puts $fd "{\"schema\":\"opentallas.ref_tile.routed-signal-cap.v1\",\"signal_cap\":\"$signal_cap\",\"pg_cap\":\"$pg_cap\",\"non_pg_layers\":[ot_ref_json_layers $signal],\"pg_layers\":[ot_ref_json_layers $power],\"violations\":[ot_ref_json_layers $violations]}"
  close $fd
  puts "SIGNAL_LAYER_AUDIT signal=$signal_cap PG=$pg_cap nonPG=$signal PGmetal=$power violations=$violations"
  if {[dict size $violations]} {error "SIGNAL_LAYER_AUDIT: actual routed metal violates its net-type ceiling"}
}

ot_ref_audit_signal_layers M6 M7 /out/signal_layer_audit_ss.json
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

write_timing_model -library_name qkd_ectl3_kiss_st_ss /out/qkd_ectl3_kiss_st_ss.lib
write_abstract_lef /out/qkd_ectl3_kiss_st.lef

if {[info exists ot_fc_root]} {
delete_clock [all_clocks]
write_timing_model -library_name qkd_ectl3_kiss_st_ss_forwarded /out/forwarded_ss.lib.raw
}
puts "OT_EXPORT_DONE"
exit
