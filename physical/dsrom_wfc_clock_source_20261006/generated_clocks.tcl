# Source-only binding for the actual divider. The caller supplies its selected
# PLL clock/terminal and mapped output pins. No PLL jitter/slew/load is invented.
# Requires the actual PLL/IP boundary to be characterized before signoff.
proc ot_wfc_bind_common_divider {pll_clock pll_terminal fast_pin slow_pin} {
    if {[llength [get_clocks $pll_clock]] != 1} {error "Missing actual common PLL clock"}
    if {[llength $pll_terminal] != 1 || [llength $fast_pin] != 1 || [llength $slow_pin] != 1} {
        error "Bind literal mapped divider terminals"
    }
    # /3 has a real overlapping half-cycle register, preserving 50% duty.
    create_generated_clock -name clk_fast -master_clock $pll_clock -source $pll_terminal -edges {1 4 7} $fast_pin
    create_generated_clock -name clk_serial -master_clock $pll_clock -source $pll_terminal -edges {1 5 9} $slow_pin
    set_clock_uncertainty -setup 60 [get_clocks {clk_fast clk_serial}]
    set_clock_uncertainty -hold 25 [get_clocks {clk_fast clk_serial}]
    # Propagate only with the mapped divider and actual parent clock network.
    # Never use this source relationship as measured insertion or IO delay.
}
