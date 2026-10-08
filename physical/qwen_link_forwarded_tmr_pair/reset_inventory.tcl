# Physical reset inventory. No timing exceptions: both raw POR and local
# majority clear paths remain ordinary recovery/removal paths.
set raw {}
foreach p [get_fanout -from [get_ports rst_n] -flat -endpoints_only -trace_arcs all] {
 if {[string match */RESETN [get_full_name $p]]} {lappend raw [get_full_name $p]}
}
set all_reset {}
foreach p [all_registers -async_pins] {
 if {[string match */RESETN [get_full_name $p]]} {lappend all_reset [get_full_name $p]}
}
set raw [lsort -unique $raw];set all_reset [lsort -unique $all_reset]
if {[llength $raw]!=24 || [llength $all_reset]!=88} {error "TMR reset inventory wrong: raw=[llength $raw] total=[llength $all_reset]"}
puts "TMR_RESET_INVENTORY raw_POR=24 local_majority_CLR=64 total=88"
