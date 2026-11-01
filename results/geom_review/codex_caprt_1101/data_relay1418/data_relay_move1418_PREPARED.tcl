# PREPARED ONLY: exact two-existing-data-buffer relay, no new cells/stages/ABI.
# Requires the reviewed BclassF final ODB. No DRT/acceptance waiver.
source $::env(SCRIPTS_DIR)/load.tcl
load_design 5_1_grt.odb 4_cts.sdc
set_propagated_clock [get_clocks clk]
set_routing_layers -signal M2-M5 -clock M2-M5
set blk [ord::get_db_block]
set movers {wire19249 wire19380}
set before {};set statuses {}
proc dr_rect {r} {return [list [$r xMin] [$r yMin] [$r xMax] [$r yMax]]}
proc dr_net_census {} {
 set r {}
 foreach n [$::blk getNets] {
  set terms {}
  foreach t [$n getITerms] {lappend terms [list I [[$t getInst] getName] [[$t getMTerm] getName]]}
  foreach t [$n getBTerms] {lappend terms [list B [$t getName]]}
  lappend r [list [$n getName] [$n getSigType] [lsort -ascii $terms]]
 }
 return [lsort -ascii $r]
}
proc dr_port_outline_census {} {
 set ports {}
 foreach t [$::blk getBTerms] {
  set pins {}
  foreach p [$t getBPins] {
   set boxes {}
   foreach q [$p getBoxes] {lappend boxes [list [[$q getTechLayer] getName] [dr_rect $q]]}
   lappend pins [list [$p getPlacementStatus] [lsort -ascii $boxes]]
  }
  lappend ports [list [$t getName] [$t getIoType] [$t getSigType] [lsort -ascii $pins]]
 }
 return [list [dr_rect [$::blk getDieArea]] [dr_rect [$::blk getCoreArea]] [lsort -ascii $ports]]
}
set dr_net_before [dr_net_census]
set dr_port_before [dr_port_outline_census]
foreach i [$blk getInsts] {
 dict set before [$i getName] [list [$i getLocation] [$i getOrient] [[$i getMaster] getName]]
 dict set statuses [$i getName] [$i getPlacementStatus]
}
if {[llength [$blk getInsts]] != 78475 || [llength [$blk getNets]] != 75870} {error "reviewed source inventory changed"}
estimate_parasitics -global_routing
global_route -start_incremental
foreach i [$blk getInsts] {if {[$i getName] ni $movers && [$i getPlacementStatus] eq "PLACED"} {$i setPlacementStatus FIRM}}
set i [$blk findInst {wire19249}]
if {$i eq "NULL" || [[$i getMaster] getName] ne "BUFx16f_ASAP7_75t_R" || [$i getLocation] ne {77814 84780} || [$i getOrient] ne "R0"} {error "reviewed source changed: wire19249"}
foreach t [$i getITerms] {set n [$t getNet];if {$n ne "NULL" && [$n getSigType] eq "CLOCK"} {error "data mover has clock net: wire19249"}}
$i setPlacementStatus PLACED
$i setLocation 36450 34560
set i [$blk findInst {wire19380}]
if {$i eq "NULL" || [[$i getMaster] getName] ne "BUFx16f_ASAP7_75t_R" || [$i getLocation] ne {78354 83430} || [$i getOrient] ne "MX"} {error "reviewed source changed: wire19380"}
foreach t [$i getITerms] {set n [$t getNet];if {$n ne "NULL" && [$n getSigType] eq "CLOCK"} {error "data mover has clock net: wire19380"}}
$i setPlacementStatus PLACED
$i setLocation 123012 29430
detailed_placement
check_placement -verbose
foreach i [$blk getInsts] {$i setPlacementStatus [dict get $statuses [$i getName]]}
proc dr_verify {} {
 global blk movers before dr_net_before dr_port_before
 if {[dr_net_census] ne $dr_net_before} {error "move-only prototype rewired net/ITerm/BTerm connectivity"}
 if {[dr_port_outline_census] ne $dr_port_before} {error "move-only prototype changed port boxes or outline"}
 set i [$blk findInst {wire19249}]
 if {[$i getLocation] ne {36450 34560} || [$i getOrient] ne "R0" || [[$i getMaster] getName] ne "BUFx16f_ASAP7_75t_R"} {error "reviewed exact relay placement/master changed: wire19249"}
 set i [$blk findInst {wire19380}]
 if {[$i getLocation] ne {123012 29430} || [$i getOrient] ne "MX" || [[$i getMaster] getName] ne "BUFx16f_ASAP7_75t_R"} {error "reviewed exact relay placement/master changed: wire19380"}
 if {[llength [$blk getInsts]] != [dict size $before]} {error "two-existing-cell prototype forbids added/deleted cells"}
 foreach i [$blk getInsts] {
  set n [$i getName]
  if {$n ni $movers && [list [$i getLocation] [$i getOrient] [[$i getMaster] getName]] ne [dict get $before $n]} {error "unreviewed nonmover mutation: $n"}
 }
}
dr_verify
puts "OT_DATA_RELAY exactly two existing buffers legalized; all other locations/masters/orientations unchanged"
global_route -end_incremental -resistance_aware -congestion_report_file /work/data_relay_actual_congestion.rpt
estimate_parasitics -global_routing
write_db /work/data_relay_placed.odb
write_sdc -no_timestamp /work/data_relay_placed.sdc
# Current canonical final repair follows the last physical mutation. Retain its
# fatal consistency checks and the normal actual released TT/FF/DRV gates.
source /work/core_final_repair.tcl
dr_verify
check_placement -verbose
write_db $::env(RESULTS_DIR)/5_1_grt.odb
write_sdc -no_timestamp $::env(RESULTS_DIR)/5_1_grt.sdc
puts "OT_DATA_RELAY_DONE: actual image/normal TT+FF/zero DRV still required; no DRT release"
