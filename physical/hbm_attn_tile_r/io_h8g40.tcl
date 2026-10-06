# H8 half tile: every input port on the bottom edge centre (x 552.9 um); the ROOT sits in the strip above.
set ot_ins {}
foreach ot_p [get_ports *] {
  if {[get_property $ot_p direction] eq "input"} { lappend ot_ins [get_full_name $ot_p] }
}
puts "OT_IO_BOTTOM_CENTRE inputs=[llength $ot_ins]"
set_io_pin_constraint -pin_names $ot_ins -region bottom:382.9-722.9
