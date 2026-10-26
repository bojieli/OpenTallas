# Structural CP boundary: bank capture and each separate face owns its pin flop.
source /src/physical/ha2_truecredit_20261007/rx_capture_at_macros.tcl
source /src/physical/common_flow/io_flop_at_pins.tcl
# send_v also feeds the return pipeline internally, so the generic one-load IO
# detector skips it. Trace its actual driver and place it beside its NORTH pin.
set cb [ord::get_db_block]
set cd [[ord::get_db_tech] getDbUnitsPerMicron]
set core [$cb getCoreArea]
set extra {}
for {set lane 0} {$lane<2} {incr lane} {
 set bt [$cb findBTerm [format {send_v[%d]} $lane]]
 if {$bt eq "NULL" || $bt eq ""} {error "Missing send_v pin $lane"}
 set net [$bt getNet]
 set ff ""
 for {set depth 0} {$depth<8} {incr depth} {
  set driver ""
  foreach it [$net getITerms] {if {[$it isOutputSignal]} {set driver $it;break}}
  if {$driver eq ""} {error "Missing send_v driver lane $lane"}
  set inst [$driver getInst]
  set master [[$inst getMaster] getName]
  if {[string match DFF* $master]} {set ff $inst;break}
  if {![regexp {^(INV|BUF)} $master]} {error "Unexpected send_v driver $master"}
  set input ""
  foreach it [$inst getITerms] {if {[$it isInputSignal]} {set input $it;break}}
  if {$input eq ""} {error "Missing send_v buffer input"}
  set net [$input getNet]
 }
 if {$ff eq ""} {error "No pin-owned send_v flop for lane $lane"}
 set bb [$bt getBBox]
 set x [expr {([$bb xMin]+[$bb xMax])/2.0-0.3*$cd}]
 set y [expr {[$core yMax]-3.16*$cd}]
 $ff setLocation [expr {round($x)}] [expr {round($y)}]
 $ff setPlacementStatus FIRM
 lappend extra [$ff getName]
}
set fh [open $::env(RESULTS_DIR)/ha2_send_pin_flops.txt w]
puts $fh [join $extra "\n"]
close $fh
puts "HA2_SEND_PINS anchored [llength $extra] distinct north-face valid flops"
