# write_sdc does not preserve clock-gating overrides; restore the same policy.
set_clock_uncertainty -setup 60 [get_clocks {core_clk q_gated}]
set_clock_uncertainty -hold 25 [get_clocks {core_clk q_gated}]
set_clock_gating_check -setup 60 -hold 25 [get_cells u_qx.u_e.g_cg.u_cg.u_icg]
