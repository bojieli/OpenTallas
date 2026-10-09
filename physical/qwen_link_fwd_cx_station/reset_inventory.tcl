# Physical reset inventory of one station: raw POR reaches 2 directions x 3 rails x 2 release FFs = 12;
# the local majority clears 2 x 16 control FFs = 32. No timing exceptions on either.
set raw {}
foreach p [get_fanout -from [get_ports rst_n] -flat -endpoints_only -trace_arcs all] {
 if {[string match */RESETN [get_full_name $p]]} {lappend raw [get_full_name $p]}
}
set all_reset {}
foreach p [all_registers -async_pins] {
 if {[string match */RESETN [get_full_name $p]]} {lappend all_reset [get_full_name $p]}
}
set raw [lsort -unique $raw];set all_reset [lsort -unique $all_reset]
if {[llength $raw]!=12 || [llength $all_reset]!=44} {error "TMR reset inventory wrong: raw=[llength $raw] total=[llength $all_reset]"}
puts "TMR_RESET_INVENTORY raw_POR=12 local_majority_CLR=32 total=44"
