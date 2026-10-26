
# One isolated current noID clock candidate, OFF in every other kit.
override export PRE_CTS_TCL = /work/pre_cts_tkm_clock.tcl
override export POST_CTS_TCL = /work/post_cts_tkm_clock.tcl
override export OT_F4_NEXT_TCL =
export OT_DTSH_CLOSED_LOOP = 1
export OT_DTSH_CL_SINK = 0
export OT_DTSH_NDR = 4w

# The proven tile clock is tile_clk; density-tap default clk is not a tile port.
export OT_DTAP_PORT = tile_clk
