# Exact leaf-only buffer insertion. Timing after mutation is deliberately NOT
# used as a verdict: the runner launches fresh SS and FF processes on the output.
set block [ord::get_db_block]
if {[$block getName] ne $expected_top} {error "Wrong relay design"}
set native_count 0
foreach instance [$block getInsts] {
  set master_name [[$instance getMaster] getName]
  if {[string match DFF* $master_name]} {
    if {$master_name ne "DFFASRHQNx1_ASAP7_75t_R"} {error "Unexpected sequential master"}
    incr native_count
  }
}
if {$native_count != 64} {error "Native relay FF count is not 64"}
set matched {}
foreach cell [get_cells -hierarchical *] {
  set name [get_full_name $cell]
  if {[regexp {^u_stage\.g_registered\.payload\[([0-9]+)\]\$_DFF_PN0_$} $name -> bit]} {
    if {$bit < 0 || $bit > 63 || [lsearch -exact $matched $bit] >= 0} {error "Unexpected relay FF identity"}
    lappend matched $bit
  }
}
if {[llength $matched] != 64} {error "Expected exactly 64 native relay FFs"}
set dbu [$block getDbUnitsPerMicron]
set die [$block getDieArea]
if {abs(double([$die dx])/$dbu - 20.0) > 0.000001 || abs(double([$die dy])/$dbu - 20.0) > 0.000001} {error "Original 20x20 slot changed"}
set buffer_master [[ord::get_db] findMaster BUFx2_ASAP7_75t_R]
if {$buffer_master eq "NULL"} {error "Missing buffer master"}
set area [expr {double([$buffer_master getWidth])*[$buffer_master getHeight]/$dbu/$dbu}]
if {abs($area - 0.0729) > 0.000001} {error "Buffer area disagrees with model"}
set ordinal 0
set original_nets [dict create]
set inserted_chains [dict create]
# Resolve the complete inventory before removing fillers or changing any net.
foreach {endpoint expected_master masters} $patches {
  set hits {}
  foreach p [get_pins -hierarchical *] {if {[get_full_name $p] eq $endpoint} {lappend hits $p}}
  if {[llength $hits] != 1} {error "Preflight endpoint identity mismatch $endpoint"}
  set terminal [sta::sta_to_db_pin [lindex $hits 0]]
  if {$terminal eq "NULL" || $terminal eq "" || [[[$terminal getInst] getMaster] getName] ne $expected_master || [$terminal getNet] eq "NULL"} {error "Preflight original master/connectivity mismatch"}
  dict set original_nets $endpoint [$terminal getNet]
}
set_thread_count 4
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
if {![grt::have_routes]} {error "Original routing guides required"}
remove_fillers
set_global_routing_layer_adjustment M2-M7 0.25
set_routing_layers -signal M2-M7 -clock M4-M7
global_route -start_incremental
foreach {endpoint expected_master masters} $patches {
  set pins {}
  foreach p [get_pins -hierarchical */[lindex [split $endpoint /] end]] {
    if {[get_full_name $p] eq $endpoint} {lappend pins $p}
  }
  if {[llength $pins] != 1} {error "STA/ODB endpoint identity mismatch $endpoint"}
  # STA prints brackets without the escapes retained by OpenDB. Resolve the
  # unique literal STA pin directly, without rewriting or globbing its name.
  if {![llength [info commands sta::sta_to_db_pin]]} {error "STA/ODB pin mapping unavailable"}
  set d [sta::sta_to_db_pin [lindex $pins 0]]
  if {$d eq "NULL" || $d eq ""} {error "No mapped data terminal $endpoint"}
  set sink [$d getInst]
  if {$sink eq "NULL" || [$sink findITerm [lindex [split $endpoint /] end]] ne $d ||
      [[$sink getMaster] getName] ne $expected_master} {
    error "Mapped endpoint is not the expected original relay terminal $endpoint"
  }
  puts "HBM_RELAY_IDENTITY sta=$endpoint odb=[$sink getName] pin=[lindex [split $endpoint /] end]"
  foreach master $masters {
    set original [$d getNet]
    set name hbm_relay_hold_$ordinal
    if {[$block findInst $name] ne "NULL"} {error "Patch already applied"}
    set prior_instances [$block getInsts]
    lassign [$sink getLocation] x y
    insert_buffer -buffer_cell $master -load_pins $pins \
      -buffer_name $name -net_name hbm_relay_net_$ordinal \
      -location [list [expr {double($x)/$dbu}] [expr {double($y)/$dbu}]]
    # insert_buffer treats -buffer_name as a prefix and appends its unique ID.
    # Bind the actual new driver through the exact sink net, not guessed names.
    set drivers {}
    foreach t [[$d getNet] getITerms] {
      if {[[$t getMTerm] getIoType] eq "OUTPUT"} {lappend drivers $t}
    }
    if {[llength $drivers] != 1} {error "Inserted sink net has no unique driver"}
    set added [[lindex $drivers 0] getInst]
    set actual_name [$added getName]
    if {[lsearch -exact $prior_instances $added] >= 0 ||
        ![regexp "^${name}\[0-9\]*$" $actual_name] ||
        [[$added getMaster] getName] ne $master} {error "Wrong inserted cell"}
    if {[[$added findITerm A] getNet] ne $original ||
        [[$added findITerm Y] getNet] ne [$d getNet] || [$d getNet] eq $original} {
      error "Inserted cell does not preserve exact data connectivity"
    }
    set added_sta_cells {}
    foreach c [get_cells -hierarchical *] {
      if {[get_full_name $c] eq $actual_name} {lappend added_sta_cells $c}
    }
    if {[llength $added_sta_cells] != 1} {error "Inserted cell STA identity mismatch"}
    set_dont_touch $added_sta_cells
    dict lappend inserted_chains $endpoint $actual_name
    puts "HBM_RELAY_PATCH endpoint=$endpoint cell=$actual_name master=$master cycles_added=0"
    incr ordinal
  }
}
if {$ordinal != 384} {error "Wrong buffer inventory"}
detailed_placement
check_placement -verbose
# Reuse original GRT guides for unaffected nets. Strip detailed wires because
# this OpenROAD build fails connectivity with mixed kept/fresh detailed routing.
foreach net [$block getNets] {
  if {[$net getSigType] in {POWER GROUND}} continue
  if {[$net getWire] ne "NULL"} {odb::dbWire_destroy [$net getWire]}
}
global_route -end_incremental -allow_congestion -resistance_aware
detailed_route -output_drc $patch_out/drc.rpt -verbose 1
filler_placement {FILLERxp5_ASAP7_75t_R FILLER_ASAP7_75t_R}
check_placement -verbose
extract_parasitics -ext_model_file /OpenROAD-flow-scripts/flow/platforms/asap7/rcx_patterns.rules
write_spef $patch_out/6_final.spef
write_db $patch_out/6_final.odb
write_verilog $patch_out/6_final.v
# Fresh physical topology audit after routing: each leaf retains exactly its
# three inserted noninverting cells and reconnects to the original driver net.
foreach {endpoint expected_master masters} $patches {
  set hits {}
  foreach p [get_pins -hierarchical *] {if {[get_full_name $p] eq $endpoint} {lappend hits $p}}
  if {[llength $hits] != 1} {error "Final terminal identity changed"}
  set terminal [sta::sta_to_db_pin [lindex $hits 0]]
  set net [$terminal getNet]
  foreach name [lreverse [dict get $inserted_chains $endpoint]] {
    set cell [$block findInst $name]
    if {$cell eq "NULL" || [[$cell getMaster] getName] ne "BUFx2_ASAP7_75t_R" || [[$cell findITerm Y] getNet] ne $net} {error "Final chain connectivity changed"}
    set drivers {}
    foreach pin [$net getITerms] {if {[[$pin getMTerm] getIoType] eq "OUTPUT"} {lappend drivers $pin}}
    if {[llength $drivers] != 1 || [lindex $drivers 0] ne [$cell findITerm Y]} {error "Final chain has unexpected driver"}
    set net [[$cell findITerm A] getNet]
  }
  if {$net ne [dict get $original_nets $endpoint]} {error "Final chain input changed"}
}
set actual_count 0
foreach cell [$block getInsts] {
  if {[string match hbm_relay_hold_* [$cell getName]]} {
    if {[[$cell getMaster] getName] ne "BUFx2_ASAP7_75t_R"} {error "Changed buffer topology"}
    incr actual_count
  }
}
if {$actual_count != 384} {error "Inserted buffer disappeared during route"}
puts "HBM_RELAY_PATCH_WRITTEN cells_added=$ordinal fresh_corner_processes_required=1"
exit
