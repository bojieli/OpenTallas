set_propagated_clock [all_clocks]
if {[llength [all_clocks]]!=6} {error "clock count changed"}
report_clock_properties [all_clocks]
# Report both real internal transport groups with complete clock insertion.
foreach c {ab_hop1 ba_hop1} {
 report_checks -to [all_registers -clock $c -data_pins] -path_delay min_max -group_path_count 4 -format full_clock_expanded
}
set block [ord::get_db_block]; set dbu [$block getDbUnitsPerMicron]
set count 0
foreach i [$block getInsts] {
 set n [$i getName]
 foreach {s lo hi} {s0 2.16 127.848 s1 432.72 558.408} {
  if {[string match "${s}.*" $n] || [string match "${s}/*" $n]} {
   lassign [$i getLocation] x y
   set x [expr {double($x)/$dbu}];set y [expr {double($y)/$dbu}]
   set xmax [expr {$x+double([[$i getMaster] getWidth])/$dbu}]
   set ymax [expr {$y+double([[$i getMaster] getHeight])/$dbu}]
   if {$x<$lo || $xmax>$hi || $y<2.16 || $ymax>66.912} {error "station bay escaped: $n at $x,$y to $xmax"}
   incr count
  }
 }
}

if {$count<2136} {error "mapped state/clock inventory disappeared"}
puts "FORWARDED_PAIR_PLACEMENT original_stage_cells=$count"

source /src/physical/qwen_link_forwarded_tmr_pair/reset_inventory.tcl
