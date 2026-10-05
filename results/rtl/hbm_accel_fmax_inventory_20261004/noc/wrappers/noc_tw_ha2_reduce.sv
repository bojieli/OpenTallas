`timescale 1ns/1ps
// Parameter-free timing wrappers of ot_ha2_owner_reduce at the DS-V4.1 TP-96 shape (NC 8, E 1,024, INJ 2, NP 20,
// LAT 7; LANES 16 = full shape, _l4 = 4-lane screening vehicle): Yosys 0.68 asserts re-deriving the parameterised
// top (rtlil.cc:1231), as the HA2 campaign's parameter-free hierarchical wrappers avoid.
module noc_tw_ha2_reduce_sr0 (
    input  wire clk, input wire rst_n, input wire [7:0] rank,
    input  wire [1:0] h_v, input wire [2*(16+512)-1:0] h_d,
    input  wire [19:0] p_v, input wire [20*537-1:0] p_flit,
    output wire r_v, output wire [15:0] r_m, output wire [511:0] r_d, output wire dupe, output wire issue_o
);
    ot_ha2_owner_reduce #(.GS(16), .NC(8), .E(1024), .LANES(16), .ONESHOT(0), .BF16(1), .INJ(2), .NP(20), .LAT(7),
        .SLOTREG(0)) u (.clk(clk), .rst_n(rst_n), .rank(rank), .h_v(h_v), .h_d(h_d), .p_v(p_v), .p_flit(p_flit),
        .r_v(r_v), .r_m(r_m), .r_d(r_d), .dupe(dupe), .issue_o(issue_o));
endmodule
module noc_tw_ha2_reduce_sr1 (
    input  wire clk, input wire rst_n, input wire [7:0] rank,
    input  wire [1:0] h_v, input wire [2*(16+512)-1:0] h_d,
    input  wire [19:0] p_v, input wire [20*537-1:0] p_flit,
    output wire r_v, output wire [15:0] r_m, output wire [511:0] r_d, output wire dupe, output wire issue_o
);
    ot_ha2_owner_reduce #(.GS(16), .NC(8), .E(1024), .LANES(16), .ONESHOT(0), .BF16(1), .INJ(2), .NP(20), .LAT(7),
        .SLOTREG(1)) u (.clk(clk), .rst_n(rst_n), .rank(rank), .h_v(h_v), .h_d(h_d), .p_v(p_v), .p_flit(p_flit),
        .r_v(r_v), .r_m(r_m), .r_d(r_d), .dupe(dupe), .issue_o(issue_o));
endmodule
module noc_tw_ha2_reduce_sr0_l4 (
    input  wire clk, input wire rst_n, input wire [7:0] rank,
    input  wire [1:0] h_v, input wire [2*(16+128)-1:0] h_d,
    input  wire [19:0] p_v, input wire [20*153-1:0] p_flit,
    output wire r_v, output wire [15:0] r_m, output wire [127:0] r_d, output wire dupe, output wire issue_o
);
    ot_ha2_owner_reduce #(.GS(16), .NC(8), .E(1024), .LANES(4), .ONESHOT(0), .BF16(1), .INJ(2), .NP(20), .LAT(7),
        .SLOTREG(0)) u (.clk(clk), .rst_n(rst_n), .rank(rank), .h_v(h_v), .h_d(h_d), .p_v(p_v), .p_flit(p_flit),
        .r_v(r_v), .r_m(r_m), .r_d(r_d), .dupe(dupe), .issue_o(issue_o));
endmodule
module noc_tw_ha2_reduce_sr1_l4 (
    input  wire clk, input wire rst_n, input wire [7:0] rank,
    input  wire [1:0] h_v, input wire [2*(16+128)-1:0] h_d,
    input  wire [19:0] p_v, input wire [20*153-1:0] p_flit,
    output wire r_v, output wire [15:0] r_m, output wire [127:0] r_d, output wire dupe, output wire issue_o
);
    ot_ha2_owner_reduce #(.GS(16), .NC(8), .E(1024), .LANES(4), .ONESHOT(0), .BF16(1), .INJ(2), .NP(20), .LAT(7),
        .SLOTREG(1)) u (.clk(clk), .rst_n(rst_n), .rank(rank), .h_v(h_v), .h_d(h_d), .p_v(p_v), .p_flit(p_flit),
        .r_v(r_v), .r_m(r_m), .r_d(r_d), .dupe(dupe), .issue_o(issue_o));
endmodule
