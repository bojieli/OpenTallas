# DIE-KV-47 2026-10-30: Q2 routed-DB DRV ECO (incremental, no full re-route) -- brief (2): the shared PRD clears every
# DATA wire and re-runs a full DRT (q2_prd_b: 4888 hold buffers from a mis-measured FF session, DRT not converging).
# Here: the routed 5_2_route.odb + its routed RCX SPEF at TT (sign-off TT libs incl. the exact LVT7 clock lib), clock
# frozen (clk_freeze.tcl), every old instance LOCKED, only RVT data cells usable (no LVT/SLVT, no sequential/SRAM
# masters), repair_design (liberty slew/cap, margin 20 %, as prd_hook) under global_route -start/-end_incremental;
# GRT re-routes only DIRTY nets (new / reconnected / resized-driver nets); every other net keeps its wire, is re-encoded
# FIXED (DRT never rips it up) and is asserted token-identical after the ONE detailed_route.
set_thread_count 16
set O /work/kv47_q2eco
source /p/q2_libprocs.tcl
ot_lib_load TT $O/libraries_tt.json
set R [glob /work/run/results/asap7/*/base]
read_db $R/5_2_route.odb
read_spef $R/6_final.spef
read_sdc /sdc/golden.sdc
set_propagated_clock [all_clocks]
source /work/setRC_rcx.tcl
set b [ord::get_db_block]
puts "KV47Q2_BEFORE slew_viol [sta::max_slew_violation_count] cap_viol [sta::max_capacitance_violation_count] wns [sta::worst_slack_cmd max]"
source /work/clk_freeze.tcl
# pre-ECO wire tokens of every routed signal net
array set tok0 {}
foreach n [$b getNets] { if {[$n getSigType] in {POWER GROUND}} continue; set w [$n getWire]; if {$w eq "NULL" || $w eq ""} continue; set tok0([$n getName]) [ot_clk_wire_tokens $n] }
puts "KV47Q2_WIRED_NETS [array size tok0]"
set ::env(RESULTS_DIR) $O
ot_clk_freeze $O
# every old instance LOCKED + master recorded
set m0 [dict create]; set wasplaced [dict create]
foreach i [$b getInsts] { dict set m0 [$i getName] [[$i getMaster] getName]; if {[$i getPlacementStatus] eq "PLACED"} { dict set wasplaced [$i getName] 1; $i setPlacementStatus LOCKED } }
# usable cells: RVT only (Q2 LVT7 clock policy pins exactly 7 LVT cells; no further low-Vt), no sequential / macro resize
set_dont_use [get_lib_cells -quiet */*_ASAP7_75t_L]
set_dont_use [get_lib_cells -quiet */*_ASAP7_75t_SL]
foreach pat {DFF* SDF* DHL* DLL* ICG* ot_sram*} { set c [get_lib_cells -quiet */$pat]; if {[llength $c]} { set_dont_use $c } }
set_routing_layers -signal M2-M5
global_route -start_incremental
repair_design -slew_margin 20 -cap_margin 20
puts "KV47Q2_AFTER_REPAIR slew_viol [sta::max_slew_violation_count] cap_viol [sta::max_capacitance_violation_count]"
# resized old instances + new instances are the only movable cells
set nres 0; set nnew 0; set mov {}
foreach i [$b getInsts] {
  set nm [$i getName]
  if {![dict exists $m0 $nm]} { incr nnew; $i setPlacementStatus PLACED; lappend mov $nm; continue }
  if {[[$i getMaster] getName] ne [dict get $m0 $nm]} {
    incr nres; puts "KV47Q2_RESIZED $nm [dict get $m0 $nm] -> [[$i getMaster] getName]"
    if {[dict exists $wasplaced $nm]} { $i setPlacementStatus PLACED; lappend mov $nm } else { error "KV47Q2: frozen instance $nm was resized" }
  }
}
puts "KV47Q2_ECO new $nnew resized $nres"
detailed_placement
check_placement -verbose
set nmoved 0
foreach nm $mov { set i [$b findInst $nm]; puts "KV47Q2_CELL $nm [[$i getMaster] getName] [$i getLocation]" }
global_route -end_incremental -congestion_report_file $O/congestion.rpt
foreach i [$b getInsts] { if {[dict exists $wasplaced [$i getName]]} { $i setPlacementStatus PLACED } }
# nets: wired + token-identical = untouched (FIXED), no wire = ECO net (needs guides)
set eco {}; set changed 0; set fixed 0
foreach n [$b getNets] {
  if {[$n getSigType] in {POWER GROUND}} continue
  set nm [$n getName]; set w [$n getWire]
  if {$w eq "NULL" || $w eq ""} {
    if {[llength [$n getITerms]] + [llength [$n getBTerms]] > 1} { lappend eco $nm; if {![llength [$n getGuides]]} { error "KV47Q2 ECO net $nm has no guide" } }
    continue
  }
  if {![info exists tok0($nm)] || [ot_clk_wire_tokens $n] ne $tok0($nm)} { incr changed; puts "KV47Q2_WIRE_CHANGED $nm"; continue }
  incr fixed [ot_clk_fix_wire $n]
}
puts "KV47Q2_ECO_NETS [llength $eco] [lrange $eco 0 30]"
puts "KV47Q2_FROZEN_REENCODED $fixed changed_wired $changed"
if {$changed} { error "KV47Q2 wired nets changed before DRT" }
source /work/kv47_q2eco/eco_drt_pre.tcl
detailed_route -output_drc $O/5_route_drc.rpt -output_maze $O/maze.log -droute_end_iter 64 -verbose 1
set bad 0; set unr {}
foreach n [$b getNets] {
  if {[$n getSigType] in {POWER GROUND}} continue
  set nm [$n getName]; set w [$n getWire]
  if {($w eq "NULL" || $w eq "") && [llength [$n getITerms]] + [llength [$n getBTerms]] > 1} { lappend unr $nm; continue }
  if {[info exists tok0($nm)] && $nm ni $eco && [ot_clk_wire_tokens $n] ne $tok0($nm)} { incr bad; puts "KV47Q2_FROZEN_CHANGED $nm" }
}
puts "KV47Q2_VERIFY frozen_changed $bad unrouted [llength $unr] [lrange $unr 0 9]"
if {$bad || [llength $unr]} { error "KV47Q2 verify failed" }
check_antennas -report_file $O/drt_antennas.log
estimate_parasitics -global_routing
puts "KV47Q2_POST_EST slew_viol [sta::max_slew_violation_count] cap_viol [sta::max_capacitance_violation_count] (GRT-estimate on ECO nets, SPEF elsewhere)"
write_db $O/5_2_route.odb
write_verilog $O/5_2_route.v
puts "KV47Q2_ECO_DONE insts [llength [$b getInsts]]"
