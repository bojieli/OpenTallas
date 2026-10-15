
set_thread_count 2
set P /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef {/srv/opentallas-scratch/codex/flow-prects-1103/src/physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.lef}
foreach l [glob $P/lib/NLDM/*RVT_TT*] {read_liberty $l}
read_liberty {/srv/opentallas-scratch/codex/flow-prects-1103/src/physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1_tt.lib}
read_verilog {/srv/opentallas-scratch/codex/flow-prects-1103/proof/raw-prects/t.v}
link_design top
initialize_floorplan -die_area {0 0 300 200} -core_area {5.4 5.4 294.6 194.4} -site asap7sc7p5t
source $P/openRoad/make_tracks.tcl
place_pins -hor_layers M4 -ver_layers M5
source {/srv/opentallas-scratch/codex/flow-prects-1103/proof/raw-prects/clocks.tcl}
source $P/setRC.tcl
set u [[ord::get_db_block] getDbUnitsPerMicron]
set k 0
foreach i [[ord::get_db_block] getInsts] {
  if {[$i getName] eq "u_m"} {$i setLocation [expr {100*$u}] [expr {90*$u}];$i setPlacementStatus FIRM} else {
    $i setLocation [expr {(15+12*($k%4))*$u}] [expr {(15+12*($k/4))*$u}];$i setPlacementStatus PLACED;incr k
  }
}
detailed_placement
estimate_parasitics -placement
source {/srv/opentallas-scratch/codex/flow-prects-1103/proof/raw-prects/pre_entries.tcl}
if {[get_property [get_clocks ot_entry_0] is_propagated]} {error "CTS root must be ideal before CTS"}
if {![get_property [get_clocks ot_entry_1] is_propagated]} {error "raw macro clock must stay propagated"}
puts PRE_CTS_STANDARD_IDEAL_RAW_PROPAGATED

set ::ot_ce_cts_roots {ck}
source /src/physical/common_flow/clock_entries.tcl
set_propagated_clock [get_clocks ot_entry_*]
clock_tree_synthesis -sink_clustering_enable -buf_list BUFx4_ASAP7_75t_R -root_buf BUFx4_ASAP7_75t_R
estimate_parasitics -placement
set ::ot_ce_corner tt
source {/srv/opentallas-scratch/codex/flow-prects-1103/proof/raw-prects/entries.tcl}
puts TILE_HYBRID_RAW_PASS
