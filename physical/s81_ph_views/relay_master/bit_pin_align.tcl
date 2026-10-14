# Actual r3 pin receipt: i/o same-bit y differs by up to53.928um and layer
# allocation wraps independently, producing crossing nets in the central strip.
# Preserve every net/register/port and W/E faces; make each E output match its
# own W input's real y/layer track. Existing hold cells are redistributed next.
set pa_blk [ord::get_db_block]
set pa_n 0
foreach pa_o [$pa_blk getBTerms] {
  if {![regexp {^o\[([0-9]+)\]$} [$pa_o getName] -> pa_bit]} continue
  set pa_i [$pa_blk findBTerm "i\[$pa_bit\]"]
  if {$pa_i eq "NULL"} { error "missing corresponding input bit $pa_bit" }
  set pa_src ""; set pa_dst ""
  foreach pa_p [$pa_i getBPins] { foreach pa_b [$pa_p getBoxes] {set pa_src $pa_b; break}; if {$pa_src ne ""} break }
  foreach pa_p [$pa_o getBPins] { foreach pa_b [$pa_p getBoxes] {set pa_dst $pa_b; break}; if {$pa_dst ne ""} break }
  if {$pa_src eq "" || $pa_dst eq ""} { error "missing physical bit pin $pa_bit" }
  set pa_x0 [$pa_dst xMin]; set pa_x1 [$pa_dst xMax]
  set pa_y0 [$pa_src yMin]; set pa_y1 [$pa_src yMax]
  set pa_l [$pa_src getTechLayer]
  foreach pa_p [$pa_o getBPins] { odb::dbBPin_destroy $pa_p }
  set pa_new [odb::dbBPin_create $pa_o]
  odb::dbBox_create $pa_new $pa_l $pa_x0 $pa_y0 $pa_x1 $pa_y1
  $pa_new setPlacementStatus FIRM
  incr pa_n
}
if {$pa_n == 0} { error "no registered same-bit E outputs found" }
puts "RELAY_BIT_PIN_ALIGN: aligned $pa_n output pins to actual corresponding input y/layer; unchanged W/E faces, nets and state"
