set_propagated_clock [all_clocks]
if {[llength [all_clocks]] != 6} {error "two roots plus four actual forwarded clocks required"}
