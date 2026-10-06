# H16 registered tile: every input port (the 1,618-bit packet, rst_n and clk) on the bottom edge's centre 340 um, where
# the ROOT register sits; the outputs (straight from the leaves, ROC 0) are left to the pin placer.
set ot_die [ord::get_die_area]
set ot_xc [expr {([lindex $ot_die 0] + [lindex $ot_die 2]) / 2.0}]
set ot_ins {}
foreach ot_p [get_ports *] {
  if {[get_property $ot_p direction] eq "input"} { lappend ot_ins [get_full_name $ot_p] }
}
puts "OT_IO_BOTTOM_CENTRE inputs=[llength $ot_ins] x=[expr {$ot_xc - 170}]..[expr {$ot_xc + 170}]"
set_io_pin_constraint -pin_names $ot_ins -region bottom:[expr {$ot_xc - 170}]-[expr {$ot_xc + 170}]
