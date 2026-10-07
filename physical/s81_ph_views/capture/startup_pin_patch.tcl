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
  set inst_name [string range $endpoint 0 end-2]
  set sink [$block findInst $inst_name]
  if {$sink eq "NULL"} {error "Missing literal startup sink $endpoint"}
  set d [$sink findITerm D]
  if {$d eq "NULL"} {error "No data terminal $endpoint"}
  set pins {}
  foreach p [get_pins -hierarchical */D] {
    if {[get_full_name $p] eq $endpoint} {lappend pins $p}
  }
  if {[llength $pins] != 1} {error "STA/ODB endpoint identity mismatch $endpoint"}
  foreach master $masters {
    set original [$d getNet]
    set name s81_startup_hold_$ordinal
    if {[$block findInst $name] ne "NULL"} {error "Patch already applied"}
    lassign [$sink getLocation] x y
    insert_buffer -buffer_cell $master -load_pins $pins \
      -buffer_name $name -net_name s81_startup_net_$ordinal \
      -location [list [expr {double($x)/$dbu}] [expr {double($y)/$dbu}]]
    set added [$block findInst $name]
    if {$added eq "NULL" || [[$added getMaster] getName] ne $master} {error "Wrong inserted cell"}
    if {[[$added findITerm A] getNet] ne $original ||
        [[$added findITerm Y] getNet] ne [$d getNet] || [$d getNet] eq $original} {
      error "Inserted cell does not preserve exact data connectivity"
    }
    set_dont_touch [get_cells $name]
    puts "S81_STARTUP_PATCH endpoint=$endpoint cell=$name master=$master cycles_added=0"
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
