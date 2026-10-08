# H16 quad parent: every input port on the bottom edge under the register channel (x 568.5 um).
set ot_ins {}
foreach ot_p [get_ports *] {
  if {[get_property $ot_p direction] eq "input"} { lappend ot_ins [get_full_name $ot_p] }
}
puts "OT_IO_BOTTOM_CHANNEL inputs=[llength $ot_ins]"
set_io_pin_constraint -pin_names $ot_ins -region bottom:398.5-738.5
# outputs (POUT banks; every pin flop-direct): head G's oy / oflt (and ov = head 0) on the die edge beside its quad's
# outer edge; quad (y, x) holds heads 8y+2x+{0,1,4,5}, left quads (x 0) on the left edge, right quads on the right.
set ot_q {}
foreach ot_p [get_ports *] {
  if {[get_property $ot_p direction] ne "output"} {continue}
  set ot_n [get_full_name $ot_p]
  if {[regexp {^oy\[([0-9]+)\]$} $ot_n -> ot_i]} { set ot_g [expr {$ot_i / 32}] } elseif {[regexp {^oflt\[([0-9]+)\]$} $ot_n -> ot_g]} {} else { set ot_g 0 }
  set ot_y [expr {$ot_g / 8}]; set ot_x [expr {($ot_g % 4) / 2}]
  dict lappend ot_q "$ot_y$ot_x" $ot_n
}
puts "OT_IO_OUT q00 [llength [dict get $ot_q 00]]"
set_io_pin_constraint -pin_names [dict get $ot_q 00] -region left:30.1-552.9
puts "OT_IO_OUT q01 [llength [dict get $ot_q 01]]"
set_io_pin_constraint -pin_names [dict get $ot_q 01] -region right:30.1-552.9
puts "OT_IO_OUT q10 [llength [dict get $ot_q 10]]"
set_io_pin_constraint -pin_names [dict get $ot_q 10] -region left:613.0-1135.9
puts "OT_IO_OUT q11 [llength [dict get $ot_q 11]]"
set_io_pin_constraint -pin_names [dict get $ot_q 11] -region right:613.0-1135.9
