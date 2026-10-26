# PRE_IO_PLACEMENT for ot_lkep_sub (864 x 643.2): every seam pin on the BOTTOM face (the cluster glue strip sits below
# the tiles), grouped in the order of the macro pins they serve, left to right: TX bank write / admission (W ring),
# TX out (S edge x 184..472), acks / feedback / status / clock / reset / session (S edge x 360..472), RX in and RX out
# (macro N edge, reached through the E ring with the RL relay stages).
set_io_pin_constraint -region bottom:4-300   -pin_names {w_d* w_oh* adm icr_ret}
set_io_pin_constraint -region bottom:300-480 -pin_names {tx_v tx_d* tx_cr}
set_io_pin_constraint -region bottom:480-560 -pin_names {ak* fb_v fb_d* st_fault st_drop st_rep* session* clk rst_n}
set_io_pin_constraint -region bottom:560-710 -pin_names {rx_v rx_d*}
set_io_pin_constraint -region bottom:710-860 -pin_names {o_v o_d* o_cr}
puts "OT_LKEP_SUB pins: bottom face only"
