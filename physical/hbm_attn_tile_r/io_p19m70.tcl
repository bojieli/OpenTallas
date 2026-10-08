# H16 quad parent POUT 0: inputs under the channel; outputs unconstrained (the placer puts each next to its quad output pin).
# H16 quad parent: every input port on the bottom edge under the register channel (x 568.5 um).
set ot_ins {}
foreach ot_p [get_ports *] {
  if {[get_property $ot_p direction] eq "input"} { lappend ot_ins [get_full_name $ot_p] }
}
puts "OT_IO_BOTTOM_CHANNEL inputs=[llength $ot_ins]"
set_io_pin_constraint -pin_names $ot_ins -region bottom:398.5-738.5
