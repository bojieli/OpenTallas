foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_SS*] { read_liberty $l }
read_liberty {/src/physical/ref_tile/dscoll_cesc0/views/dsfd_coll_cesc0/dsfd_coll_cesc0_ss.lib}
read_liberty {/src/physical/ref_tile/dscoll_cesl/views/dsfd_coll_cesl/dsfd_coll_cesl_ss.lib}
read_liberty {/src/physical/ref_tile/dscoll_ceso/views/dsfd_coll_ceso/dsfd_coll_ceso_ss.lib}
read_liberty {/src/physical/ref_tile/dscoll_cesp0/views/dsfd_coll_cesp0/dsfd_coll_cesp0_ss.lib}
read_liberty {/src/physical/ref_tile/dscoll_cesx/views/dsfd_coll_cesx/dsfd_coll_cesx_ss.lib}
read_db /base/4_1_cts.odb
read_sdc /base/4_cts.sdc
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
estimate_parasitics -placement
delete_clock [all_clocks]
create_clock -name core_clk -period 833.333
create_clock -name ot_entry_0 -period 833.333 [get_ports {ck_x1}]
create_clock -name ot_entry_1 -period 833.333 [get_ports {ck_x2}]
create_clock -name ot_entry_2 -period 833.333 [get_ports {ck_x3}]
create_clock -name ot_entry_3 -period 833.333 [get_ports {ck_core}]
create_clock -name ot_entry_4 -period 833.333 [get_ports {ck_l0}]
create_clock -name ot_entry_5 -period 833.333 [get_ports {ck_l1}]
create_clock -name ot_entry_6 -period 833.333 [get_ports {ck_l2}]
create_clock -name ot_entry_7 -period 833.333 [get_ports {ck_l3}]
create_clock -name ot_entry_8 -period 833.333 [get_ports {ck_o}]
create_clock -name ot_entry_9 -period 833.333 [get_ports {ck_pt}]
set ::env(CORNER) WC
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
# AUTO clock entries: bound insertion.json boundary refs; no ETM arc modification.
set ::ot_ce_refs [dict create {dsfd_coll_cesx/ck} {tt {123.0 127.3 131.0} ff {98.7 102.8 106.1} ss {166.3 171.0 175.3}} {dsfd_coll_cesc0/ck} {tt {300.4 321.5 363.5} ff {243.7 263.0 304.2} ss {394.5 418.9 460.9}} {dsfd_coll_cesl/ck} {tt {107.8 113.7 116.3} ff {81.5 87.0 89.4} ss {154.9 161.7 164.5}} {dsfd_coll_ceso/ck} {tt {91.9 98.2 104.0} ff {72.3 78.9 85.0} ss {126.4 132.6 138.9}} {dsfd_coll_cesp0/ck} {tt {158.9 166.3 175.5} ff {127.6 135.0 144.2} ss {212.5 219.8 229.2}}]
set ::ot_ce_counts [dict create {dsfd_coll_cesx} 3 {dsfd_coll_cesc0} 1 {dsfd_coll_cesl} 4 {dsfd_coll_ceso} 1 {dsfd_coll_cesp0} 1]
set ::ot_ce_ports {{ck_x1} {ck_x2} {ck_x3} {ck_core} {ck_l0} {ck_l1} {ck_l2} {ck_l3} {ck_o} {ck_pt}}

set ::ot_ce_require_wire 1
proc ot_ce_corner {} {
  if {[info exists ::ot_ioref_scene] && $::ot_ioref_scene eq "BC"} { return ff }
  if {[info exists ::ot_ce_corner]} { return $::ot_ce_corner }
  # WC is a scene label, not an actual library corner: option-B overlays WC
  # with TT. Bind the reference to actual loaded child Liberty objects.
  set found {}
  foreach cell [get_cells -quiet -hierarchical *] {
    set master [get_property $cell ref_name]
    if {![dict exists $::ot_ce_counts $master]} continue
    set libcells [get_lib_cells -quiet -of_objects $cell]
    if {![llength $libcells]} { error "OT_ENTRIES: $master has no loaded Liberty association" }
    foreach lc $libcells {
      set full [get_full_name $lc]
      if {![regexp -nocase {_(tt|ff|ss)/} $full -> corner]} { error "OT_ENTRIES: unknown actual child Liberty corner $full" }
      dict set found [string tolower $corner] 1
    }
  }
  if {[dict size $found] == 1} { return [lindex [dict keys $found] 0] }
  # A multi-mode database needs its actual setup corner or BC scene shim.
  if {[info exists ::env(OT_MM_SETUP_CORNER)]} {
    switch -nocase -- $::env(OT_MM_SETUP_CORNER) {
      TC - tt {set corner tt} BC - ff {set corner ff} WC - ss {set corner ss}
      default { error "OT_ENTRIES: unknown actual setup corner" }
    }
    if {[dict exists $found $corner]} { return $corner }
  }
  error "OT_ENTRIES: ambiguous actual loaded child corners [dict keys $found]"
}
proc ot_ce_apply {} {
  set corner [ot_ce_corner]
  set clk [get_clocks core_clk]
  if {[llength $clk] != 1} { error "OT_ENTRIES: core_clk missing" }
  # Wires-only parents have no CTS tree to set this flag for us.
  # Ideal clocks silently report zero network arrival despite real entry wires.
  set_propagated_clock [get_clocks ot_entry_*]
  set sources {}; set names {}
  foreach c [get_clocks ot_entry_*] {
    foreach p [get_property $c sources] { lappend sources $p; lappend names [get_full_name $p] }
  }
  if {[lsort $names] ne [lsort $::ot_ce_ports]} { error "OT_ENTRIES: source clock coverage differs from spec" }
  foreach c [get_clocks ot_entry_*] { set_clock_latency -source 0 $c }
  sta::worst_slack_cmd max
  set rows {}; set seen {}; set counts {}
  foreach cell [get_cells -quiet -hierarchical *] {
    set master [get_property $cell ref_name]
    if {![dict exists $::ot_ce_counts $master]} continue
    dict incr counts $master
    foreach pin [get_pins -quiet -of_objects $cell] {
      set key "$master/[get_property $pin lib_pin_name]"
      if {![dict exists $::ot_ce_refs $key]} continue
      set ports [get_ports -quiet -of_objects [get_nets -quiet -of_objects $pin]]
      if {[llength $ports] != 1} { error "OT_ENTRIES: [get_full_name $pin] lacks one direct top clock port" }
      set port [lindex $ports 0]; set name [get_full_name $port]
      if {$name ni $::ot_ce_ports || [dict exists $seen $name]} { error "OT_ENTRIES: duplicate or undeclared source $name" }
      dict set seen $name 1
      set wire [get_property $pin arrival_max_rise]
      if {![string is double -strict $wire]} { error "OT_ENTRIES: missing entry wire clock arrival on [get_full_name $pin]" }
      if {abs($wire) < 1.0e-9 && [info exists ::ot_ce_require_wire] && $::ot_ce_require_wire} {
        # A zero arrival is admissible only if actual source and child pin are
        # physically coincident. Missing parasitics/ideal clocks cannot qualify.
        if {![llength [info commands ord::get_db_block]]} { error "OT_ENTRIES: zero wire lacks physical source/pin proof" }
        set block [ord::get_db_block]
        set bt [$block findBTerm $name]
        set it [$block findITerm [get_full_name $pin]]
        if {$bt eq "NULL" || $it eq "NULL"} { error "OT_ENTRIES: missing physical source/child clock pin" }
        set pb [$bt getBBox]; set ib [$it getBBox]
        set distance [expr {(abs(([$pb xMin]+[$pb xMax])-([$ib xMin]+[$ib xMax])) + abs(([$pb yMin]+[$pb yMax])-([$ib yMin]+[$ib yMax]))) / 2.0 / [$block getDbUnitsPerMicron]}]
        if {$distance > 0.001} { error "OT_ENTRIES: zero clock wire arrival despite $distance um source/pin separation on $name" }
        puts "OT_ENTRIES ZERO_WIRE_PROVEN $name [get_full_name $pin] distance=$distance"
      }
      lassign [dict get $::ot_ce_refs $key $corner] lo mean hi
      set clock [get_clocks ot_entry_[lsearch -exact $::ot_ce_ports $name]]
      if {[llength $clock] != 1} { error "OT_ENTRIES: $name has no unique related clock" }
      set ttmean [lindex [dict get $::ot_ce_refs $key tt] 1]
      lappend rows [list $port $pin $wire $lo $mean $hi $clock $ttmean]
    }
  }
  dict for {m n} $::ot_ce_counts {
    if {![dict exists $counts $m] || [dict get $counts $m] != $n} { error "OT_ENTRIES: bound child count mismatch $m" }
  }
  if {[dict size $seen] != [llength $::ot_ce_ports]} { error "OT_ENTRIES: incomplete actual child/source coverage" }
  set ref 0
  foreach row $rows { lassign $row p pin wire lo mean hi; set ref [expr {max($ref, $wire + $mean)}] }
  set low {}; set high {}; set lowclocks {}; set highclocks {}
  foreach row $rows {
    lassign $row p pin wire lo mean hi clock ttmean
    if {$ttmean > 300} { lappend highclocks $clock } else { lappend lowclocks $clock }
    set latency [expr {$ref - $wire - $mean}]
    set_clock_latency -source $latency $clock
    lappend low [expr {$ref + $lo - $mean}]; lappend high [expr {$ref + $hi - $mean}]
    puts "OT_ENTRIES COMP $corner [get_full_name $p] -> [get_full_name $pin] wire=$wire R=$mean latency=$latency phi=$ref"
  }
  # Every entry is synchronous and related. Reserve die skew on internal hops;
  # no asynchronous groups, false paths or ETM insertion add-back.
  set_clock_uncertainty -setup 150 -from [get_clocks ot_entry_*] -to [get_clocks ot_entry_*]
  # H1 authoritative pair_check.HOLD_TREE =50ps hold margin+50ps die skew.
  # Tile-local25ps uncertainty is not the composed pair margin.
  set_clock_uncertainty -hold 100 -from [get_clocks ot_entry_*] -to [get_clocks ot_entry_*]
  if {[llength $lowclocks] && [llength $highclocks]} {
    set_clock_uncertainty -setup 210 -from $lowclocks -to $highclocks
    set_clock_uncertainty -setup 210 -from $highclocks -to $lowclocks
  }
  # Preserve measured boundary spread: balancing the mean does not erase the
  # earliest/latest physical boundary arrivals or change ETM setup/hold arcs.
  set lmin [lindex [lsort -real $low] 0]; set lmax [lindex [lsort -real $high] end]
  unset_input_delay [all_inputs]; unset_output_delay [all_outputs]
  set sk [expr {[info exists ::env(OT_IO_SKEW)] ? $::env(OT_IO_SKEW) : 90}]
  set hk [expr {[info exists ::env(OT_IO_HOLD_SKEW)] ? $::env(OT_IO_HOLD_SKEW) : 50}]
  set_input_delay [expr {166.667+$lmax+$sk}] -max -clock $clk [all_inputs -no_clocks]
  set hki [expr {[info exists ::env(OT_IO_IN_HOLD_SKEW)] ? $::env(OT_IO_IN_HOLD_SKEW) : 0}]
  set_input_delay [expr {$lmin-$hki}] -min -clock $clk [all_inputs -no_clocks]
  set_output_delay [expr {166.667-$lmax+$sk}] -max -clock $clk [all_outputs]
  set_output_delay [expr {-$lmin-$hk}] -min -clock $clk [all_outputs]
  if {[info exists ::env(OT_IO_INTER)] && $::env(OT_IO_INTER) ne ""} {
    foreach pattern [split $::env(OT_IO_INTER) ","] {
      set_input_delay [expr {166.667+$lmax+150}] -max -clock $clk [get_ports -quiet $pattern -filter "direction == input"]
      set_output_delay [expr {166.667-$lmax+150}] -max -clock $clk [get_ports -quiet $pattern -filter "direction == output"]
    }
  }
  puts "OT_ENTRIES COMP DONE $corner [llength $rows] entries phi=$ref boundary=$lmin..$lmax"
}
ot_ce_apply

sta::worst_slack_cmd max
set actual {}; set wires {}
foreach cell [get_cells -hierarchical *] {
 set m [get_property $cell ref_name]
 foreach pin [get_pins -of_objects $cell] {
  set key "$m/[get_property $pin lib_pin_name]"
  if {![dict exists $::ot_ce_refs $key]} continue
  set mean [lindex [dict get $::ot_ce_refs $key [ot_ce_corner]] 1]
  set arrival [get_property $pin arrival_max_rise]
  lappend actual [expr {$arrival+$mean}]
 }
}
set vals [lsort -real $actual]
if {[llength $actual] != 10 || abs([lindex $vals end]-[lindex $vals 0])>0.02} { error "REAL_WIRE phi coverage failed" }
foreach c [get_clocks ot_entry_*] { set_clock_latency -source 0 $c }
sta::worst_slack_cmd max
foreach cell [get_cells -hierarchical *] {
 set m [get_property $cell ref_name]
 foreach pin [get_pins -of_objects $cell] {
  if {![dict exists $::ot_ce_refs "$m/[get_property $pin lib_pin_name]"]} continue
  set wire [get_property $pin arrival_max_rise]; lappend wires $wire
  puts "REAL_WIRE [ot_ce_corner] [get_full_name $pin] $wire"
 }
}
set peak [lindex [lsort -real $wires] end]
if {$peak<10} { error "REAL_WIRE no nonzero clock wire proven" }
puts "REAL_WIRE_PASS [ot_ce_corner] 10 exact pins measured peak=$peak phi_spread=[expr {[lindex $vals end]-[lindex $vals 0]}]"
exit
