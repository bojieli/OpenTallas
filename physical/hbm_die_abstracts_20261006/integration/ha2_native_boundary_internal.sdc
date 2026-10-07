# CONDITIONAL_NATIVE_CALLER_CONTEXT: internal paths only.
# Ideal primary-input clk is a diagnostic reference; SOURCE IS UNQUALIFIED.
# No external TU read-mux delay, PLL insertion/jitter, reset-release bound or
# external receiver cap is supplied by this SDC. Report unbound I/O separately.
create_clock -name clk -period 833 -waveform {0 416.5} [get_ports clk]
set_clock_uncertainty -setup 60 [get_clocks clk]
set_clock_uncertainty -hold 25 [get_clocks clk]
# Preserve real propagated CTS / corner parasitics in the routed report.
# No false paths, no 20% I/O budget, no parent clock/IO closure claim.
