# Real external core clock structural successor; generated divider/gating/MC absent.
# Keep original host core_clk policy and IO boundaries. Values are ps (ASAP7).
if {[llength [get_ports cx*]] != 1} { error "OT_LOADER_CX real clock pin absent" }
create_clock -name loader_core -period 1666.666667 [get_ports cx*]
set_clock_uncertainty -setup 60 [get_clocks loader_core]
set_clock_uncertainty -hold 25 [get_clocks loader_core]
# The actual 24 finite Gray-pointer channel instances are the sole crossings.
# This inherits the approved L-DIV asynchronous crossing contract.
set_clock_groups -asynchronous -group [get_clocks loader_core] -group [get_clocks core_clk]
puts "OT_LOADER_CX actual external core clock; no divider, gate or multicycle"
