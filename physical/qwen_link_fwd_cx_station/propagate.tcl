set_propagated_clock [all_clocks]
if {[llength [all_clocks]] != 4} {error "forwarded port clocks lost"}
