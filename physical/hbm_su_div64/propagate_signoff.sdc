# After routed clock creation, include real insertion on every generated clock.
if {[llength [get_clocks div64_*]] != 4} {error "DDIV64 missing generated clocks at signoff"}
set_propagated_clock [get_clocks {core_clk div64_*}]
