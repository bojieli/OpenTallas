`default_nettype none
// Production analog macro interface only. No digital approximation of clocks.
// Vendor Liberty/LEF/GDS, acquisition, jitter, skew and fault response are
// required before physical qualification. Simulation supplies a separate model.
(* blackbox *)
module ot_hbm_pll_bb (
 input wire refclk, reset_n,
 output wire clk_stream, clk_serial, clk_hbm, clk_link, locked
);
endmodule
`default_nettype wire
