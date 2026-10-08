# Exact leaf-only buffer insertion. Timing after mutation is deliberately NOT
# used as a verdict: the runner launches fresh SS and FF processes on the output.
set block [ord::get_db_block]
if {[$block getName] ne "dsfd_capt_x"} {error "Wrong capture design"}
set dbu [$block getDbUnitsPerMicron]
set ordinal 0
set_thread_count 16
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
if {![grt::have_routes]} {error "Original routing guides required"}
remove_fillers
set_global_routing_layer_adjustment M2-M7 0.25
set_routing_layers -signal M2-M7 -clock M4-M7
global_route -start_incremental
foreach {endpoint masters} $patches {
  set pins {}
  foreach p [get_pins -hierarchical */D] {
    if {[get_full_name $p] eq $endpoint} {lappend pins $p}
  }
  if {[llength $pins] != 1} {error "STA/ODB endpoint identity mismatch $endpoint"}
  # STA prints brackets without the escapes retained by OpenDB. Resolve the
  # unique literal STA pin directly, without rewriting or globbing its name.
  if {![llength [info commands sta::sta_to_db_pin]]} {error "STA/ODB pin mapping unavailable"}
  set d [sta::sta_to_db_pin [lindex $pins 0]]
  if {$d eq "NULL" || $d eq ""} {error "No mapped data terminal $endpoint"}
  set sink [$d getInst]
  if {$sink eq "NULL" || [$sink findITerm D] ne $d ||
      [[$sink getMaster] getName] ne "DFFHQNx1_ASAP7_75t_R"} {
    error "Mapped endpoint is not the original startup data terminal $endpoint"
  }
  puts "S81_STARTUP_IDENTITY sta=$endpoint odb=[$sink getName] pin=D"
  foreach master $masters {
    set original [$d getNet]
    set name s81_startup_hold_$ordinal
    if {[$block findInst $name] ne "NULL"} {error "Patch already applied"}
    set prior_instances [$block getInsts]
    lassign [$sink getLocation] x y
    insert_buffer -buffer_cell $master -load_pins $pins \
      -buffer_name $name -net_name s81_startup_net_$ordinal \
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
    puts "S81_STARTUP_PATCH endpoint=$endpoint cell=$actual_name master=$master cycles_added=0"
    incr ordinal
  }
}
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
puts "S81_STARTUP_PATCH_WRITTEN cells_added=$ordinal fresh_corner_processes_required=1"
exit
