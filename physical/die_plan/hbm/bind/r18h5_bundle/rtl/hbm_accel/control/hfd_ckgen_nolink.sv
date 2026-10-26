`timescale 1ns/1ps
`default_nettype none
// L2H-PAD l21 (LEAD2-HBM, 2026-10-19): hfd_ckgen without the unused link domain.
// The d4g HBM die has no consumer of the link domain: every die link (host UCIe, d2d) runs on pll_stream, and the
// pll_link / por_link outputs of hfd_ckgen were the die's only unread clock-generator nets (strict bind residual).
// This master is hfd_ckgen with those two outputs and the link reset-release synchroniser removed (truly dead logic).
// The PLL macro is unchanged (its clk_link output stays unloaded inside the block); the three remaining domain
// releases are the same hfd_ckgen_rel two-flop synchronisers, so por_stream/por_serial/por_hbm are cycle-identical.
module hfd_ckgen_nolink (
    input  wire refclk,
    input  wire por_n,
    output wire pll_stream, output wire pll_serial, output wire pll_hbm,
    output wire por_stream, output wire por_serial, output wire por_hbm
);
    wire locked;
    wire clk_link_unloaded;
    ot_hbm_pll_bb u_pll (.refclk(refclk), .reset_n(por_n), .clk_stream(pll_stream), .clk_serial(pll_serial),
                         .clk_hbm(pll_hbm), .clk_link(clk_link_unloaded), .locked(locked));
    hfd_ckgen_rel3 u_rel (.ck_stream(pll_stream), .ck_serial(pll_serial), .ck_hbm(pll_hbm),
                          .por_n(por_n), .locked(locked),
                          .rst_stream(por_stream), .rst_serial(por_serial), .rst_hbm(por_hbm));
endmodule

// reset-release leaf: three domains, one tile (each synchroniser in its own domain clock)
module hfd_ckgen_rel3 (input wire ck_stream, ck_serial, ck_hbm, input wire por_n, locked,
                       output wire rst_stream, rst_serial, rst_hbm);
    hfd_ckgen_rel u_rs (.ck(ck_stream), .por_n(por_n), .locked(locked), .rst_n(rst_stream));
    hfd_ckgen_rel u_rr (.ck(ck_serial), .por_n(por_n), .locked(locked), .rst_n(rst_serial));
    hfd_ckgen_rel u_rh (.ck(ck_hbm),    .por_n(por_n), .locked(locked), .rst_n(rst_hbm));
endmodule
`default_nettype wire
