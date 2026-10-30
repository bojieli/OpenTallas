# One balanced clock tree replaces the exploratory nested quadrant clock trees.
# No logic, external pin, clock root, SDC or cycle changes.
source /work/max_fanout.tcl
set b [ord::get_db_block]
unset_dont_touch [get_nets -of_objects [get_pins ot_pcq_tap_*/A]]
unset_dont_touch [get_nets -of_objects [get_pins ot_pcq_tap_*/Y]]
unset_dont_touch [get_cells ot_pcq_tap_*]
set total 0
for {set k 0} {$k < 4} {incr k} {
 set nm ot_pcq_tap_$k
 set i [$b findInst $nm]
 if {$i eq "NULL" || $i eq ""} {error "PC_UNIFORM missing expected internal tap $nm"}
 set ni "";set no ""
 foreach it [$i getITerms] {
  if {[[$it getMTerm] getSigType] ni {SIGNAL CLOCK}} continue
  if {[$it isInputSignal]} {set ni [$it getNet]}
  if {[$it isOutputSignal]} {set no [$it getNet]}
 }
 if {$ni eq "NULL" || $ni eq "" || $no eq "NULL" || $no eq ""} {error "PC_UNIFORM disconnected $nm"}
 set sinks {}
 foreach it [$no getITerms] {if {[$it getInst] ne $i} {lappend sinks $it}}
 foreach it $sinks {$it disconnect;$it connect $ni;incr total}
 puts "PC_UNIFORM $nm reconnects [llength $sinks] clock pins to [$ni getName]"
 odb::dbInst_destroy $i
 odb::dbNet_destroy $no
}
puts "PC_UNIFORM removed 4 nested tap drivers; reconnected $total sinks; ONE original clock root retained"
