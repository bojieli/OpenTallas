# ROOT-scoped initial normal ORFS clock+signal GRT only. No repair/STA/DRT.
source $::env(SCRIPTS_DIR)/load.tcl
load_design local_relief_prep.odb 4_cts.sdc
set ::probe_block [ord::get_db_block]
proc probe_cells {b} {set s {};foreach i [$b getInsts] {lappend s [list [$i getName] [[$i getMaster] getName] [$i getLocation] [$i getOrient]]};return $s}
proc probe_nets {b} {set s {};foreach n [$b getNets] {lappend s [list [$n getName] [$n getSigType] [$n isSpecial]]};return $s}
set ::probe_before_cells [probe_cells $::probe_block]
set ::probe_before_nets [probe_nets $::probe_block]
if {[llength $::probe_before_cells]!=103954 || [llength $::probe_before_nets]!=101706} {error "wrong exact PREP graph"}
rename ::global_route ::probe_native_global_route
proc ::global_route {args} {
  if {[lsearch -exact $args -start_incremental]>=0 || [lsearch -exact $args -end_incremental]>=0} {error "incremental repair not authorized"}
  puts "RELIEF_COMBINED_INITIAL_GRT_ARGS $args"
  set rc [catch {::probe_native_global_route {*}$args} err opts]
  set b $::probe_block
  set f [open /probe/probe_result.txt w]
  puts $f "NATIVE_GRT_RC=$rc MESSAGE=$err"
  set intact [expr {[probe_cells $b] eq $::probe_before_cells && [probe_nets $b] eq $::probe_before_nets}]
  puts $f "EXACT_PLACEMENT_MASTERS_NET_TYPES_SPECIAL_FLAGS_UNCHANGED=$intact"
  set ck 0;set ckg 0;set sig 0;set sigg 0;set ng 0
  foreach n [$b getNets] {
    set guides [llength [$n getGuides]];incr ng $guides
    if {[$n getSigType] eq "CLOCK"} {incr ck;if {$guides>0} {incr ckg}}
    if {[$n getSigType] eq "SIGNAL"} {incr sig;if {$guides>0} {incr sigg}}
  }
  puts $f "CLOCK_NETS=$ck CLOCK_WITH_GUIDES=$ckg SIGNAL_NETS=$sig SIGNAL_WITH_GUIDES=$sigg TOTAL_GUIDES=$ng"
  foreach n [$b getNets] {
    if {[$n getSigType] in {POWER GROUND}} {
      set prc [catch {check_power_grid -net [$n getName]} pe]
      puts $f "PG [$n getName] RC=$prc MESSAGE=$pe"
    }
  }
  close $f
  write_db /probe/combined_probe.odb
  catch {write_guides /probe/combined_probe.guide} ge
  if {!$intact} {error "scope changed during route; result refused"}
  if {$ck!=860 || $ckg!=860} {error "incomplete actual clock guide coverage; no PASS"}
  if {$rc} {return -options $opts $err}
  puts "RELIEF_INITIAL_PROBE_DONE_NO_REPAIR_NO_STA_NO_DRT"
  exit 0
}
source $::env(SCRIPTS_DIR)/global_route.tcl
