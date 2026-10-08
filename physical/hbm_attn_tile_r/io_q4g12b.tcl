# H4 quad (option B): every input port on the left edge at the register strip (y 281.5 um); the HC bank sits in the strip.
set ot_ins {}
foreach ot_p [get_ports *] {
  if {[get_property $ot_p direction] eq "input"} { lappend ot_ins [get_full_name $ot_p] }
}
puts "OT_IO_LEFT_STRIP inputs=[llength $ot_ins]"
set_io_pin_constraint -pin_names $ot_ins -region left:131.5-431.5
# option B / die tile b: every output (oy, gov, oflt) on the right (outer) edge at the register strip, where the
# leaves' top-edge outputs meet; the die tile takes them into an EW bank in its side channel
set ot_outs {}
foreach ot_p [get_ports *] {
  if {[get_property $ot_p direction] eq "output"} { lappend ot_outs [get_full_name $ot_p] }
}
puts "OT_IO_RIGHT_STRIP outputs=[llength $ot_outs]"
set_io_pin_constraint -pin_names $ot_outs -region right:256.0-307.0
