# PRE_GLOBAL_PLACE: local register ownership at the SRAM read pins.
# cap_q is a NEW pipeline edge; raw_q is the existing transport destination.
# The capture collar uses eight columns outside each macro's real pin face.
set cb [ord::get_db_block]
set cd [[ord::get_db_tech] getDbUnitsPerMicron]
set cc [$cb getCoreArea]
set anchored {}
foreach ff [$cb getInsts] {
  set name [$ff getName]
  if {![regexp {^(.*g_ram\[[0-9]+\])\.cap_q\[([0-9]+)\]} $name -> bank bit]} continue
  if {![string match DFF* [[$ff getMaster] getName]]} continue
  set mi [$cb findInst $bank.storage]
  if {$mi eq "NULL" || $mi eq ""} { error "Missing SRAM for capture $name" }
  set bb [$mi getBBox]
  set orient [$mi getOrient]
  if {$orient ni {R0 MY}} { error "Capture collar does not support macro orientation $orient" }
  set width [expr {double([[$ff getMaster] getWidth])/$cd}]
  set col [expr {$bit % 8}]
  set mx [expr {double([$bb xMin])/$cd}]
  set my [expr {double([$bb yMin])/$cd}]
  # The compiler LEF puts rd_out[b] on west face at y=1.536+0.096*b.
  # MY mirrors that face to the east, retaining its y coordinate.
  set y [expr {floor(($my + 1.536 + 0.096*$bit)/0.27)*0.27}]
  if {$orient eq "R0"} {
    set x [expr {$mx-1.08-($col+1)*0.70}]
  } else {
    set x [expr {double([$bb xMax])/$cd+1.08+$col*0.70}]
  }
  if {$x < double([$cc xMin])/$cd || $x+$width > double([$cc xMax])/$cd || $y < double([$cc yMin])/$cd || $y+0.27 > double([$cc yMax])/$cd} {
    error "Capture collar exceeds core: $name at $x $y"
  }
  $ff setLocation [expr {round($x*$cd)}] [expr {round($y*$cd)}]
  $ff setPlacementStatus FIRM
  lappend anchored $name
}
if {[llength $anchored]!=1120} { error "Expected full-shape 1120 local capture bits; found [llength $anchored]" }
set fh [open $::env(RESULTS_DIR)/ha2_capture_collar.txt w]
puts $fh [join $anchored "\n"]
close $fh
puts "HA2_CAPTURE_COLLAR anchored [llength $anchored] bank-owned capture flops"
