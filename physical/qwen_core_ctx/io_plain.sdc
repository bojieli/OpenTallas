# Boundary delays referenced to the clock port (the form every ORFS stage loads and writes back): 0.2 T each side,
# the same as tools/run_abi3_physical.py --io-delay-fraction 0.2 writes in constraint.sdc.
unset_input_delay [all_inputs]
unset_output_delay [all_outputs]
# the gated engine clock (ICG output to the ME spine) is a clock, not a boundary data port
set qcc_outs {}
foreach p [all_outputs] { if {[get_full_name $p] ne "u_me.clk"} { lappend qcc_outs $p } }
set_input_delay 166.6 -clock core_clk [all_inputs -no_clocks]
set_output_delay 166.6 -clock core_clk $qcc_outs
