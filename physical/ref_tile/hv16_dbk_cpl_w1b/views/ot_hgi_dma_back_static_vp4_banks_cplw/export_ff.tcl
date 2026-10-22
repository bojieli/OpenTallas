read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /mv0/ot_hgi_dma_back_landing_bank.lef
read_lef /mv1/ot_hgi_dma_back_cp_collar.lef
read_lef /mv2/ot_hgi_dma_back_static_vp4_controller.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz
read_liberty /mv0/ot_hgi_dma_back_landing_bank_ff.lib
read_liberty /mv1/ot_hgi_dma_back_cp_collar_ff.lib
read_liberty /mv2/ot_hgi_dma_back_static_vp4_controller_ff.lib
set ::env(OT_PF_MACRO_LIBS) [list /src/physical/ref_tile/hv15_dbk_bank/views/ot_hgi_dma_back_landing_bank/ot_hgi_dma_back_landing_bank_ff.lib /src/physical/ref_tile/hv16_dbk_collar/views/ot_hgi_dma_back_cp_collar/ot_hgi_dma_back_cp_collar_ff.lib /src/physical/ref_tile/hv16_dbk_vp4_ctl_rt80/views/ot_hgi_dma_back_static_vp4_controller/ot_hgi_dma_back_static_vp4_controller_ff.lib]
read_db /work/results/asap7/opentallas_ot_hgi_dma_back_static_vp4_banks_cplw_asap7_ref_hv16_dbk_cpl_w1b_w1b_98344bac6/base/6_final.odb
set ::ot_ce_corner ff
read_sdc /work/results/asap7/opentallas_ot_hgi_dma_back_static_vp4_banks_cplw_asap7_ref_hv16_dbk_cpl_w1b_w1b_98344bac6/base/6_final.sdc
read_spef /work/results/asap7/opentallas_ot_hgi_dma_back_static_vp4_banks_cplw_asap7_ref_hv16_dbk_cpl_w1b_w1b_98344bac6/base/6_final.spef
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

ot_ref_audit_signal_layers M6 M7 /out/signal_layer_audit_ff.json
puts "OT_WS max [sta::worst_slack_cmd max] min [sta::worst_slack_cmd min]"
write_timing_model -library_name ot_hgi_dma_back_static_vp4_banks_cplw_ff /out/ot_hgi_dma_back_static_vp4_banks_cplw_ff.lib


if {[llength [get_ports -quiet clk_in]] == 1 && [llength [get_ports -quiet clk_out]] == 1} {

  set ot_fc_block [ord::get_db_block]
  set ot_fc_ib [$ot_fc_block findBTerm clk_in]
  set ot_fc_ob [$ot_fc_block findBTerm clk_out]
  if {[$ot_fc_ib getIoType] ne "INPUT" || [$ot_fc_ob getIoType] ne "OUTPUT"} {error OT_FC_PORT_DIRECTION}
  set ot_fc_in [$ot_fc_ib getNet]
  set ot_fc_net [$ot_fc_ob getNet]
  if {[$ot_fc_net getBTerms] ne [list $ot_fc_ob]} {error OT_FC_ALIASED_OUTPUT_ROOT}
  set ot_fc_chain {}
  set ot_fc_parity 0
  set ot_fc_it {}
  while {1} {
    set ot_fc_drivers {}
    foreach it [$ot_fc_net getITerms] {
      if {[$it getIoType] eq "OUTPUT"} {lappend ot_fc_drivers $it}
    }
    if {[llength $ot_fc_drivers] != 1} {error "OT_FC_UNIQUE_DRIVER [$ot_fc_net getName]"}
    set ot_fc_d [lindex $ot_fc_drivers 0]
    if {$ot_fc_it eq {}} {set ot_fc_it $ot_fc_d}
    set ot_fc_ci [$ot_fc_d getInst]
    if {$ot_fc_ci in $ot_fc_chain} {error OT_FC_CHAIN_CYCLE}
    set ot_fc_ins {}
    set ot_fc_outs {}
    foreach it [$ot_fc_ci getITerms] {
      if {[$it getIoType] eq "INPUT"} {lappend ot_fc_ins $it}
      if {[$it getIoType] eq "OUTPUT"} {lappend ot_fc_outs $it}
    }
    if {[llength $ot_fc_ins] != 1 || [llength $ot_fc_outs] != 1} {error OT_FC_NOT_UNARY}

    set ot_fc_input [lindex $ot_fc_ins 0]
    set ot_fc_ip [[$ot_fc_input getMTerm] getName]
    set ot_fc_op [[$ot_fc_d getMTerm] getName]
    set ot_fc_master [[$ot_fc_ci getMaster] getName]
    set ot_fc_functions {}
    foreach ot_fc_lib [get_libs -quiet *] {
      set ot_fc_lc [$ot_fc_lib find_liberty_cell $ot_fc_master]
      if {$ot_fc_lc in {"" NULL}} continue
      set ot_fc_lp [$ot_fc_lc find_liberty_port $ot_fc_op]
      if {$ot_fc_lp in {"" NULL} || [sta::liberty_port_direction $ot_fc_lp] ne "output"} {error OT_FC_LIBERTY_OUTPUT}
      set ot_fc_fn [string map {" " "" "\t" "" "\n" "" "(" "" ")" ""} [$ot_fc_lp function]]
      dict set ot_fc_functions $ot_fc_fn 1
      puts "OT_FC_LIB $ot_fc_master [get_full_name $ot_fc_lib] $ot_fc_fn"
    }
    if {[dict size $ot_fc_functions] != 1} {error OT_FC_LIBERTY_AMBIGUOUS_FUNCTION}
    set ot_fc_fn [lindex [dict keys $ot_fc_functions] 0]
    if {$ot_fc_fn eq $ot_fc_ip} {
      set ot_fc_inv 0
    } elseif {$ot_fc_fn in [list !$ot_fc_ip ~$ot_fc_ip ${ot_fc_ip}']} {
      set ot_fc_inv 1
    } else {error "OT_FC_LIBERTY_NOT_UNARY $ot_fc_master $ot_fc_fn"}
    set ot_fc_parity [expr {$ot_fc_parity ^ $ot_fc_inv}]
    puts "OT_FC_ROLE $ot_fc_master [$ot_fc_ci getName] $ot_fc_ip $ot_fc_op $ot_fc_fn $ot_fc_inv"

    lappend ot_fc_chain $ot_fc_ci
    puts "OT_FC_CHAIN [[$ot_fc_ci getMaster] getName] [$ot_fc_ci getName]"
    set ot_fc_net [[lindex $ot_fc_ins 0] getNet]
    if {$ot_fc_net eq "NULL"} {error OT_FC_DISCONNECTED_INPUT}
    if {$ot_fc_net eq $ot_fc_in} {break}
    if {[llength [$ot_fc_net getBTerms]]} {error OT_FC_WRONG_INPUT_ROOT}
  }
  if {[$ot_fc_in getBTerms] ne [list $ot_fc_ib]} {error OT_FC_ALIASED_INPUT_ROOT}
  foreach it [$ot_fc_in getITerms] {
    if {[$it getIoType] eq "OUTPUT"} {error OT_FC_DRIVEN_INPUT_ROOT}
  }
  set ot_fc_sense [expr {$ot_fc_parity ? "negative_unate" : "positive_unate"}]
  puts "OT_FC_SENSE $ot_fc_sense"
  set ot_fc_inst [$ot_fc_it getInst]
  puts "OT_FC_DRIVER [[$ot_fc_inst getMaster] getName] [$ot_fc_inst getName]"
  set ot_fc_root {}
  set ot_fc_delete {}
  foreach c [all_clocks] {
    foreach source [get_property $c sources] {
      if {[get_full_name $source] eq "clk_in"} {lappend ot_fc_root $c}
      if {[get_full_name $source] eq "clk_out"} {lappend ot_fc_delete $c}
    }
  }
  if {[llength $ot_fc_root] != 1} {error OT_FC_UNIQUE_SOURCE_CLOCK}
  set ot_fc_root [lindex $ot_fc_root 0]
  if {[$ot_fc_root is_generated]} {error OT_FC_GENERATED_INPUT_ROOT}
  set ot_fc_wave [$ot_fc_root waveform]
  if {[llength $ot_fc_wave] != 2} {error OT_FC_TWO_ROOT_EDGES}
  puts "OT_FC_WAVE [sta::time_sta_ui [lindex $ot_fc_wave 0]] [sta::time_sta_ui [lindex $ot_fc_wave 1]]"
  puts "OT_FC_CLOCK [get_full_name $ot_fc_root]"
  sta::update_generated_clks
  foreach c [lsort -unique $ot_fc_delete] {
    if {![$c is_generated]} {error OT_FC_OUTPUT_NOT_GENERATED}
    set ot_fc_period [$ot_fc_root period]
    set ot_fc_output_wave [$c waveform]
    if {abs([$c period] - $ot_fc_period) > 1e-6 * $ot_fc_period || [llength $ot_fc_output_wave] != 2} {error OT_FC_OUTPUT_PERIOD}
    for {set edge 0} {$edge < 2} {incr edge} {
      set delta [expr {[lindex $ot_fc_output_wave $edge] - [lindex $ot_fc_wave [expr {$edge ^ $ot_fc_parity}]]}]
      if {abs($delta - round($delta / $ot_fc_period) * $ot_fc_period) > 1e-6 * $ot_fc_period} {error OT_FC_OUTPUT_PHASE}
    }
    puts "OT_FC_OUTPUT_CLOCK [get_full_name $c]"
  }
  write_sdc /out/forwarded_clock_signoff_ff.sdc
  foreach c [lsort -unique $ot_fc_delete] {delete_clock $c}
  unset_input_delay [get_ports clk_in]
  set_propagated_clock [all_clocks]
  sta::find_timing_paths -path_delay max -group_path_count 1
  set ot_fc_driver_pin [get_pins "[$ot_fc_inst getName]/[[$ot_fc_it getMTerm] getName]"]
  set ot_fc_pin [sta::get_port_pin [lindex [get_ports clk_out] 0]]
  set ot_fc_input_pin [sta::get_port_pin [lindex [get_ports clk_in] 0]]
  foreach prop {arrival_max_rise arrival_min_rise arrival_max_fall arrival_min_fall slew_max_rise slew_max_fall} {
    set input_value [get_property $ot_fc_input_pin $prop]
    puts "OT_FC_INPUT_METRIC $prop $input_value"
    set value [get_property $ot_fc_pin $prop]
    puts "OT_FC_ABSOLUTE_METRIC $prop $value"
    set driver_value [get_property $ot_fc_driver_pin $prop]
    puts "OT_FC_DRIVER_ABSOLUTE_METRIC $prop $driver_value"
    if {[string match arrival_* $prop]} {
      set edge [expr {[string match *_fall $prop] ? 1 : 0}]
      set source_edge [expr {$edge ^ $ot_fc_parity}]
      set phase [sta::time_sta_ui [lindex $ot_fc_wave $source_edge]]
      puts "OT_FC_PHASE $prop $source_edge $phase"
      set value [expr {$value - $phase}]
      set driver_value [expr {$driver_value - $phase}]
    }
    puts "OT_FC_METRIC $prop $value"
    puts "OT_FC_DRIVER_METRIC $prop $driver_value"
  }
  puts "OT_FC_ROOT clk_in"
}

if {[info exists ot_fc_root]} {
delete_clock [all_clocks]
write_timing_model -library_name ot_hgi_dma_back_static_vp4_banks_cplw_ff_forwarded /out/forwarded_ff.lib.raw
}
puts "OT_EXPORT_DONE"
exit
