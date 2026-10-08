# Physical data-path ECO on the immutable b25c67c final routed snapshot.
# No sequential cells, clock topology, timing constraints, or RTL cycles change.
set block [ord::get_db_block]
set preserve [expr {[info exists ::env(OT_ECO_PRESERVE_ROUTES)] && $::env(OT_ECO_PRESERVE_ROUTES) eq "1"}]
if {$preserve} {write_def /work/eco_original.def}
set changed_nets {}
remove_fillers
set original {}
set connectivity {}
foreach inst [$block getInsts] {
  set name [$inst getName]
  dict set original $name [list [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] [[$inst getMaster] getName]]
  foreach pin [$inst getITerms] {
    set net [$pin getNet]
    dict set connectivity "$name/[[$pin getMTerm] getName]" [expr {$net eq "NULL" ? "NULL" : [$net getName]}]
  }
  $inst setPlacementStatus LOCKED
}
set targets [list \
 {g_sk[4].g_flat.u_b.genblk1.g_delay.g_stage[16].stage_q[7]$_DFF_P_/D} \
 {g_sk[5].g_flat.u_a.genblk1.g_delay.g_stage[18].stage_q[2]$_DFF_P_/D}]
set index 0
set actual_targets {}
foreach name $targets {
  set inst NULL
  foreach candidate [$block getInsts] {
    if {[string map {\\ {}} [$candidate getName]] eq [file dirname $name]} {set inst $candidate;break}
  }
  if {$inst eq "NULL"} {error "ECO missing endpoint $name"}
  lappend changed_nets [[[$inst findITerm D] getNet] getName]
  set actual_name "[$inst getName]/D"
  lappend actual_targets $actual_name
  set loc [$inst getLocation]
  set units [$block getDbUnitsPerMicron]
  set xy [list [expr {[lindex $loc 0]/double($units)}] [expr {[lindex $loc 1]/double($units)}]]
  set pin [sta::find_pin $name]
  if {$pin eq "NULL"} {set pin [sta::find_pin $actual_name]}
  if {$pin eq "NULL"} {error "ECO endpoint selection failed $actual_name"}
  insert_buffer -buffer_cell BUFx2_ASAP7_75t_R -load_pins $pin -location $xy -buffer_name ot_hold_eco_$index -net_name ot_hold_eco_net_$index
  incr index
}
if {[llength [$block getInsts]] != [dict size $original]+2} {error "ECO changed more than two cells"}
# All original cells locked: detailed placement legalizes only the two new buffers.
detailed_placement
check_placement -verbose
set changed {}
foreach inst [$block getInsts] {
 set name [$inst getName]
 if {[dict exists $original $name]} {
  lassign [dict get $original $name] loc orient status master
  if {[$inst getLocation] ne $loc || [$inst getOrient] ne $orient || [[$inst getMaster] getName] ne $master} {error "ECO moved or resized original cell $name"}
  foreach pin [$inst getITerms] {
   set key "$name/[[$pin getMTerm] getName]"
   set net [$pin getNet]
   set netname [expr {$net eq "NULL" ? "NULL" : [$net getName]}]
   if {$netname ne [dict get $connectivity $key]} {lappend changed $key}
  }
  $inst setPlacementStatus $status
 } else {
  puts "OT_ECO_NEW_CELL $name [[$inst getMaster] getName] [$inst getLocation]"
 }
}
if {[lsort $changed] ne [lsort $actual_targets]} {error "ECO unexpected connectivity diff: $changed"}
set keep [get_cells -hierarchical *u_min_delay]
if {[llength $keep]!=15424} {error "ECO lost architectural min-delay buffers"}
set_dont_touch $keep
set_dont_touch [get_cells ot_hold_eco_*]
# Discard old signal routes only; PDN special wires remain. Full GRT/DRT follows.
set removed 0
foreach net [$block getNets] {
 if {[$net getSigType] in {POWER GROUND}} {continue}
 if {$preserve && [$net getName] ni $changed_nets} {continue}
 set wire [$net getWire]
 if {$wire ne "NULL"} {odb::dbWire_destroy $wire; incr removed}
}
puts "OT_TWO_PATH_ECO_PASS original_cells=[dict size $original] inserted=2 changed_data_pins=2 unchanged_original_placement=1 unchanged_clock_connectivity=1 retained_min_delay=15424 cleared_signal_routes=$removed"
write_db /work/two_path_eco.odb
write_verilog /work/two_path_eco.v

if {$preserve} {
 write_def /work/eco_changed.def
 puts [exec python3 /src/tools/s81_head_glue_fixed_routes.py freeze --original /work/eco_original.def --current /work/eco_changed.def --output /work/eco_fixed.def]
 foreach net [$block getNets] {
  if {[$net getSigType] in {POWER GROUND}} {continue}
  set wire [$net getWire]
  if {$wire ne "NULL"} {odb::dbWire_destroy $wire}
 }
 read_def -incremental /work/eco_fixed.def
 write_def /work/eco_fixed_roundtrip.def
 puts [exec python3 /src/tools/s81_head_glue_fixed_routes.py check --original /work/eco_original.def --current /work/eco_fixed_roundtrip.def --output /work/eco_fixed.json]
 check_placement -verbose
 write_db /work/two_path_fixed.odb
}
