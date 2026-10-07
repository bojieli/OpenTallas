# Candidate constraint fragment for standalone ot_hdc_fdiv64.
# Run after creating core_clk on clk at 0.833333 ns (HBM lane fast domain),
# setting real die IO budgets, and read_liberty at the actual SS/FF corner.
# The serial-chain 0.9 GHz domain is distinct; this candidate is not selected
# there. Deriving half clocks from this master preserves the 1.2 GHz fast
# input/output boundaries and prices each core at 0.6 GHz.
# Fail closed if synthesis changed the two ICG pin names.
foreach {name edges pin} {div64_a {1 2 5} ga/u_icg/GCLK div64_b {3 4 7} gb/u_icg/GCLK} {
    set endpoint [get_pins $pin]
    if {[llength $endpoint] != 1} { error "missing unique divider ICG pin $pin" }
    create_generated_clock -name $name -master_clock core_clk -source [get_ports clk] -edges $edges $endpoint
}
set div64_period [get_property [get_clocks core_clk] period]
set_clock_uncertainty -setup [expr {$div64_period * 60.0 / 833.333}] [get_clocks {core_clk div64_a div64_b}]
set_clock_uncertainty -hold [expr {$div64_period * 25.0 / 833.333}] [get_clocks {core_clk div64_a div64_b}]
# No false paths, multicycle exceptions, or relaxed fast crossings. Propagated
# clocks, ICG ENA checks, min pulse widths and real IO delays remain required.
# Hierarchical/full-lane instances require separately scoped ICG pin paths.
