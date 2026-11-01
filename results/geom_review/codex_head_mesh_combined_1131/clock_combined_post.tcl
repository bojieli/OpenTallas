read_db /work/run/results/asap7/dp_hd_mesh_e/base/5_1_grt.odb
set f [open /work/combined_clock_census.tsv w]
set cf [open /work/clock_pin_coverage.tsv w]
puts $cf "net\tinstance\tmaster\tpin\tdirection"
set rf [open /work/clock_roots.tsv w]
puts $rf "net\tport\tdirection"
puts $f "class\tnet\tdegree\tspecial\tguides\tspecial_wires"
set clk 0
set sig 0
set clk_missing 0
foreach n [[ord::get_db_block] getNets] {
  set ty [$n getSigType]
  set degree [expr {[llength [$n getITerms]]+[llength [$n getBTerms]]}]
  set sp [$n isSpecial]
  set ng [llength [$n getGuides]]
  set sw [llength [$n getSWires]]
  puts $f "$ty\t[$n getName]\t$degree\t$sp\t$ng\t$sw"
  if {$ty in {CLOCK SIGNAL} && $degree > 1} {
    if {$sp || $sw} { error "COMBINED_GRT special routed-class net $ty [$n getName]" }
    if {$ty eq "CLOCK"} { incr clk; if {$ng == 0} { incr clk_missing } } else { incr sig }
    if {$ty eq "CLOCK"} {
      foreach it [$n getITerms] { set i [$it getInst]; puts $cf "[$n getName]\t[$i getName]\t[[$i getMaster] getName]\t[[$it getMTerm] getName]\t[[$it getMTerm] getIoType]" }
      foreach bt [$n getBTerms] { puts $rf "[$n getName]\t[$bt getName]\t[$bt getIoType]" }
    }
  }
}
close $f
close $cf
close $rf
puts "COMBINED_GRT_POST connected_CLOCK=$clk connected_SIGNAL=$sig CLOCK_without_guides=$clk_missing"
if {$clk == 0 || $sig == 0 || $clk_missing != 0} { error "COMBINED_GRT omitted physical clock occupancy" }
