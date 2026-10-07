`timescale 1ns/1ps
// CLAUDE S81-PH ctrl v2: centre tile of the S81 HBM controller boundary (between PC tiles 15 and 16).  The slab-level
// glue of the v1 dsfd_ctrl: reset synchronisers, the PHY reset (a ckh flop released after the synchroniser), the
// sticky PHY out-of-range status (ckh) crossed to cks, and the die status st = {fault, live} merged from the two
// column chains (PC 0 -> 15 on the W face, PC 31 -> 16 on the E face).  Every output is a flop; every input enters
// one gate before its flop (status levels) or a synchroniser.
`default_nettype none
module dsfd_ctrl_ctr (
    input  wire [0:0] cks,
    input  wire [0:0] ckh,
    input  wire [0:0] rst,
    input  wire [1:0] co_w,      // chain from PC 15
    input  wire [1:0] co_e,      // chain from PC 16
    input  wire [0:0] k_oor,     // PHY outputs (ckh)
    input  wire [0:0] w_oor,
    output reg  [0:0] phy_rst_n, // PHY rst_n
    output reg  [1:0] st
);
    wire hrst_n, srst_n;
    ot_s81ph_sync u_hrs (.clk(ckh[0]), .rst_n(rst[0]), .d(1'b1), .q(hrst_n));
    ot_s81ph_sync u_srs (.clk(cks[0]), .rst_n(rst[0]), .d(1'b1), .q(srst_n));
    always @(posedge ckh[0] or negedge hrst_n) if (!hrst_n) phy_rst_n <= 1'b0; else phy_rst_n <= 1'b1;
    reg oor_h;
    always @(posedge ckh[0] or negedge hrst_n) if (!hrst_n) oor_h <= 1'b0; else oor_h <= oor_h | k_oor[0] | w_oor[0];
    wire [1:0] hs;
    ot_s81ph_sync #(.W(2)) u_hs (.clk(cks[0]), .rst_n(srst_n), .d({oor_h, hrst_n}), .q(hs));
    always @(posedge cks[0] or negedge srst_n)
        if (!srst_n) st <= 2'b00;
        else st <= {st[1] | hs[1] | co_w[1] | co_e[1], hs[0] & co_w[0] & co_e[0]};
endmodule
`default_nettype wire
