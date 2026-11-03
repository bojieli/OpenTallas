read_db /work/input.odb
source /work/clk_freeze.tcl
set f [open /work/net_coverage.tsv w];puts $f "name\tsignal_type\tterminals\tguides\twire_length\twire_types\tspecial\tcovered"
set count 0;set missing 0;set clocks 0;set badclock 0;set guide_nets 0;set fixed_nets 0
foreach n [[ord::get_db_block] getNets] {
 set type [$n getSigType];if {$type ni {SIGNAL CLOCK}} continue
 set terminals [expr {[llength [$n getITerms]]+[llength [$n getBTerms]]}]
 if {$terminals<2} continue
 incr count;set ng [llength [$n getGuides]];set w [$n getWire];set wl 0;set wt {}
 if {$w ne "NULL" && $w ne ""} {set wl [$w length];set wt [ot_clk_wire_types $n]}
 set fixed [expr {$wl>0 && $wt eq {64}}];set covered [expr {$ng>0 || $fixed}]
 if {$ng>0} {incr guide_nets};if {$fixed} {incr fixed_nets};if {!$covered} {incr missing}
 if {$type eq "CLOCK"} {incr clocks;if {[$n isSpecial]} {incr badclock}}
 puts $f "[$n getName]\t$type\t$terminals\t$ng\t$wl\t$wt\t[$n isSpecial]\t$covered"
};close $f
source /work/pg_connect.tcl
ot_pg_require_bound red_final_saved_grt
puts "RED_FINAL_SAVED_COVERAGE connected=$count clocks=$clocks guide_nets=$guide_nets fixed_nets=$fixed_nets missing=$missing excluded_special_clock=$badclock"
if {$missing || $badclock || !$clocks} {error "RED_FINAL_SAVED_COVERAGE_FAIL"}
puts "RED_FINAL_SAVED_COVERAGE_PASS"
