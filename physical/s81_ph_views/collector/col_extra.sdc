# CLAUDE S81-PH collector: rst is the die reset net into a 2-flop synchroniser (async assertion, synchronised release
# rst_s[1], covered by the rst_mcp2 multicycle of io_vclk_m_770.sdc).  No timing from the rst pin (as the gather /
# capture views): col_m1 reported its removal check (-713 ps, unfixable at a port) as the worst hold endpoint.
set_false_path -from [get_ports {rst}]
