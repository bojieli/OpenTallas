# ot_qwen_stream4_cdc_pc: one pseudo-channel of the STREAM4 memory clock interface.
# Two asynchronous roots: core clk 833.333 ps (1.2 GHz) and the external periodic controller clock hclk 1,024 ps.
# Signoff policy unchanged: setup uncertainty 60 ps (SS), hold 25 ps (FF) on BOTH clocks.
create_clock -name clk  -period 833.333  [get_ports clk]
create_clock -name hclk -period 1024.000 [get_ports hclk]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
# Crossing arcs (no clock groups, no false paths).  The two roots have no static phase relation, so every
# clk<->hclk arc is a datapath budget: Gray pointer -> first synchronizer flop, and the reading domain's
# storage read mux -> capture register (the slot is stable for >= SYNC reading edges after its pointer
# moves).  Budget = the FASTER period minus the setup uncertainty (773.333 ps), applied in BOTH directions,
# which is stricter than the source-period bound of the clock plan for the hclk-captured arcs.
# Hold: a crossing arc needs only a non-negative datapath delay (the slot / pointer is held for a full
# source period at least).
set_max_delay -ignore_clock_latency 773.333 -from [get_clocks clk]  -to [get_clocks hclk]
set_max_delay -ignore_clock_latency 773.333 -from [get_clocks hclk] -to [get_clocks clk]
set_min_delay -ignore_clock_latency 0 -from [get_clocks clk]  -to [get_clocks hclk]
set_min_delay -ignore_clock_latency 0 -from [get_clocks hclk] -to [get_clocks clk]
# Boundary: 0.2 T on each port, in its own domain.
set_input_delay  166.667 -clock clk  [get_ports {c_arst_n l_pop w_v w_sec* w_data* w_tag*}]
set_output_delay 166.667 -clock clk  [get_ports {l_v l_sec* l_row* l_data* w_room wd_v wd_tag* c_fault}]
set_input_delay  204.800 -clock hclk [get_ports {h_arst_n h_lv h_lsec* h_lrow* h_ldata* h_hand h_wcon h_av h_atag*}]
set_output_delay 204.800 -clock hclk [get_ports {h_cred* h_wv h_wsec* h_cv h_csec* h_cdata* h_ctag* h_fault}]
set_max_fanout 32 [current_design]
