# OT_CLOCK_ENTRY_DOMAIN_API_VERSION 1
create_clock -name core_clk -period 833.333000000
create_clock -name ot_entry_0 -period 833.333000000 [get_ports {ca}]
create_clock -name ot_entry_1 -period 833.333000000 [get_ports {cb}]
