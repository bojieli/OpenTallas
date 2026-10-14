read_liberty /src/physical/ref_tile/qfd_vm_su_t/views/ot_qfd_vm_su_t/ot_qfd_vm_su_t_tt.lib
read_verilog /probe/probe.v
link_design deep
create_clock -name core_clk -period 833.333
create_clock -name ot_entry_0 -period 833.333 [get_ports {a}]
create_clock -name ot_entry_1 -period 833.333 [get_ports {b}]
set_propagated_clock [get_clocks ot_entry_*]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
foreach k {max min} { set p [find_timing_paths -path_delay $k -group_path_count 1]; if {![llength $p]} {error "missing actual baseline $k"}; dict set before $k [get_property [lindex $p 0] slack] }
set ::ot_ce_corner tt
# AUTO clock entries: bound insertion.json boundary refs; no ETM arc modification.
set ::ot_ce_refs [dict create {ot_qfd_vm_su_t/clk} {tt {337.3 371.2 433.2} ff {277.1 310.7 364.6} ss {433.5 466.3 539.5}}]
set ::ot_ce_counts [dict create {ot_qfd_vm_su_t} 2]
set ::ot_ce_ports {{a} {b}}

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
  # TREE pair_check.SKEW_DEEP applies when either TT reference exceeds300ps,
  # including two deep entries with their own earlier trunk taps.
  if {[llength $highclocks]} {
    set_clock_uncertainty -setup 210 -from $highclocks -to [get_clocks ot_entry_*]
    set_clock_uncertainty -setup 210 -from [get_clocks ot_entry_*] -to $highclocks
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
foreach k {max min} {set p [find_timing_paths -path_delay $k -group_path_count 1]; if {![llength $p]} {error "missing actual final $k"}; set actual [get_property [lindex $p 0] slack]; set expected [expr {[dict get $before $k] - ($k eq "max" ? 150 : 75)}]; if {abs($actual-$expected)>0.02} {error "deep budget mismatch $actual/$expected"}; puts "DEEP_PATH $k $actual expected=$expected"}
puts "DEEP_PASS tt"
exit
