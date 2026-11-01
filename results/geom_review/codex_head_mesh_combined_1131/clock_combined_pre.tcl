# Root/flow-approved isolated normal-stage probe: preserve every special flag.
source /work/hold_repair_pre.tcl
set clk 0
set sig 0
set excluded {}
set f [open /work/combined_pre_census.tsv w]
puts $f "class\tnet\tdegree\tspecial\tspecial_wires"
foreach n [[ord::get_db_block] getNets] {
  set ty [$n getSigType]
  puts $f "$ty\t[$n getName]\t[expr {[llength [$n getITerms]]+[llength [$n getBTerms]]}]\t[$n isSpecial]\t[llength [$n getSWires]]"
  if {$ty ni {CLOCK SIGNAL}} continue
  if {[llength [$n getSWires]] || [$n isSpecial]} { lappend excluded "$ty:[$n getName]" }
  if {$ty eq "CLOCK"} { incr clk } else { incr sig }
}
close $f
puts "COMBINED_GRT_PRE excluded CLOCK/SIGNAL nets=$excluded"
if {[llength $excluded]} { error "COMBINED_GRT original special/excluded or unaccounted special-wire occupancy; flags preserved" }
if {$clk == 0 || $sig == 0} { error "COMBINED_GRT omitted required net class CLOCK=$clk SIGNAL=$sig" }
puts "COMBINED_GRT_PRE CLOCK=$clk SIGNAL=$sig originally non-special; all flags and PG unchanged; special-wires=0"
