# H4 quad: every input port on the left edge at the register strip (y 291.4 um); the HC bank sits in the strip.
set ot_ins {}
foreach ot_p [get_ports *] {
  if {[get_property $ot_p direction] eq "input"} { lappend ot_ins [get_full_name $ot_p] }
}
puts "OT_IO_LEFT_STRIP inputs=[llength $ot_ins]"
set_io_pin_constraint -pin_names $ot_ins -region left:141.4-441.4
