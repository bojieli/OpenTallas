# Native clock-family active-edge wire arrival, same API as ck_insertion39021.
source /work/kit/vendor/clock_family.tcl
report_units
check_setup -verbose
report_checks -unconstrained -path_delay min_max -format full_clock_expanded -group_path_count 30
set f [open /work/output/clock_pins_[expr {[info exists ::env(INT8_CORNER)] ? $::env(INT8_CORNER) : "TT"}].tsv w]
puts $f "pin\tactive_edge_wire_arrival\tslew_max_rise"
foreach pin [all_registers -clock_pins] {
 set owners [get_property $pin clocks]
 if {[llength $owners] != 1} {error "AMBIGUOUS_CLOCK_OWNER [get_full_name $pin]"}
 puts $f "[get_full_name $pin]\t[ot_cf_wire $pin $owners]\t[get_property $pin slew_max_rise]"
}
close $f
