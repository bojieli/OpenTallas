# Pre-CTS ideal LOCAL tree insertion, matching the virtual neighbour clock budget.
# Stage-only: pre_cts.tcl removes it before tree construction. Golden SDC stays unchanged.
set_clock_latency -clock clk 250.0000 [get_ports {clk clk_t1 clk_t2 clk_t3}]
