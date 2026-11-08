// PHY RE-FORM bench: behavioural stand-in for the qkd_hbm3e_phy_pc4 blackbox (same ports).  Every pi bit changes every
// cycle (an LFSR folded with the po inputs), so a one-cycle lane misalignment is visible on every lane.  rst_n === 0
// resets the state; an X reset (landing not yet started) keeps it running so the payload is exercised from cycle 1.
`timescale 1ns/1ps
module qkd_hbm3e_phy_pc4 (
    input  wire         clk,
    input  wire         rst_n,
    output wire [288:0] pi0, output wire [288:0] pi1, output wire [288:0] pi2, output wire [288:0] pi3,
    input  wire [327:0] po0, input  wire [327:0] po1, input  wire [327:0] po2, input  wire [327:0] po3,
    output wire [3:0]   fh0, output wire [3:0]   fh1, output wire [3:0]   fh2, output wire [3:0]   fh3,
    output wire [3:0]   rh0, output wire [3:0]   rh1, output wire [3:0]   rh2, output wire [3:0]   rh3
);
    reg [63:0] s = 64'h0123456789abcdef;
    wire [63:0] f = po0[63:0] ^ po1[127:64] ^ po2[191:128] ^ po3[255:192];
    always @(posedge clk)
        if (rst_n === 1'b0) s <= 64'h1;
        else s <= {s[62:0], s[63] ^ s[62] ^ s[60] ^ s[59]} ^ f;
    wire [63:0] a = s, b = {s[31:0], s[63:32]} ^ 64'ha5a5a5a5a5a5a5a5, c = ~s, d = {s[15:0], s[63:16]};
    assign pi0 = {a[32:0], a, b, c, d};
    assign pi1 = {b[32:0], b, c, d, a};
    assign pi2 = {c[32:0], c, d, a, b};
    assign pi3 = {d[32:0], d, a, b, c};
    assign fh0 = a[3:0]; assign fh1 = b[3:0]; assign fh2 = c[3:0]; assign fh3 = d[3:0];
    assign rh0 = a[7:4]; assign rh1 = b[7:4]; assign rh2 = c[7:4]; assign rh3 = d[7:4];
endmodule
