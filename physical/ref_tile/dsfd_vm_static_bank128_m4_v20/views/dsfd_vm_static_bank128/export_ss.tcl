read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /mv0/ot_sram_1r1w_512x128_m4_r2c2.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz
read_liberty /mv0/ot_sram_1r1w_512x128_m4_r2c2_ss.lib
read_db /work/results/asap7/opentallas_dsfd_vm_static_bank128_asap7_ref_dsfd_vm_static_bank128_m4_v20_v20std2_977ea3ed7/base/6_final.odb
set ::ot_ce_corner ss
read_sdc /work/results/asap7/opentallas_dsfd_vm_static_bank128_asap7_ref_dsfd_vm_static_bank128_m4_v20_v20std2_977ea3ed7/base/6_final.sdc
read_spef /work/results/asap7/opentallas_dsfd_vm_static_bank128_asap7_ref_dsfd_vm_static_bank128_m4_v20_v20std2_977ea3ed7/base/6_final.spef
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

ot_ref_audit_signal_layers M4 M5 /out/signal_layer_audit_ss.json
puts "OT_WS max [sta::worst_slack_cmd max] min [sta::worst_slack_cmd min]"
write_timing_model -library_name dsfd_vm_static_bank128_ss /out/dsfd_vm_static_bank128_ss.lib
write_abstract_lef /out/dsfd_vm_static_bank128.lef

puts "OT_EXPORT_DONE"
exit
