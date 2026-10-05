
set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [lsort [glob $P/lib/NLDM/*_RVT_$::env(PROBE_CORNER)_*.lib*]] {read_liberty $f}
read_db $::env(PROBE_ODB)
read_sdc $::env(PROBE_SDC)
read_spef $::env(PROBE_SPEF)
set_propagated_clock [all_clocks]
report_units
set selected {}
foreach cell [get_cells *] {
    set name [get_full_name $cell]
    if {[string match {rst_q*} $name]} {lappend selected $cell}
    if {[regexp {^u_l\.q\[([0-9]+)\]} $name -> bit] &&
        ($bit == 0 || ($bit >= 672 && $bit < 704) || $bit >= 747)} {
        lappend selected $cell
    }
}
if {![llength $selected]} {error "Missing retained boundary launch cells"}
foreach cell $selected {
    puts "PROBE_CELL [get_full_name $cell]"
    foreach pin [get_pins -of_objects $cell] {
        if {[get_property $pin direction] == "output"} {
            foreach net [get_nets -of_objects $pin] {
                report_net -digits 6 [get_full_name $net]
            }
        }
    }
}
puts "PROBE_CLOCK_AND_CAPTURE"
report_checks -from $selected -path_delay max -group_path_count 4 -format full_clock_expanded -digits 4
report_checks -from $selected -path_delay min -group_path_count 4 -format full_clock_expanded -digits 4
puts "PROBE_DONE"
