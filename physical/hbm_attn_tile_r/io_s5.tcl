# H16 two-strip tile: every input port (the packet, rst_n, clk) on the left edge around the middle gap (y 572.9 um),
# beside the ROOT bank; the outputs (straight from the leaves) are left to the pin placer.
set ot_ins {}
foreach ot_p [get_ports *] {
  if {[get_property $ot_p direction] eq "input"} { lappend ot_ins [get_full_name $ot_p] }
}
puts "OT_IO_LEFT_MIDDLE inputs=[llength $ot_ins]"
set_io_pin_constraint -pin_names $ot_ins -region left:412.9-732.9
