# write_sdc omits per-cell gating checks in the installed STA version.
# Reapply these real checks at CTS/route; do not redefine the generated clock.
set_clock_uncertainty -setup 60 [get_clocks {core_clk q_gated}]
set_clock_uncertainty -hold 25 [get_clocks {core_clk q_gated}]
set_clock_gating_check -setup 60 -hold 25 [get_cells g_qx.g_cg.u_cg.u_icg]
