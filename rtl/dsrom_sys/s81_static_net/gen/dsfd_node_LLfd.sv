`timescale 1ns/1ps
module dsfd_node_LLfd (
    input wire [62:0] a,
    input wire [62:0] b,
    input wire [0:0] clk,
    input wire [0:0] fi,
    output wire [0:0] fo,
    output wire [65:0] o,
    input wire [0:0] rst_n
);
    wire a_v = a[0]; wire [31:0] a_d = a[32:1]; wire a_e = a[59];
    wire [31:0] a_t = {a[62:60], a[48:33], a[53:49], 3'd0, a[58:54]};
    wire b_v = b[0]; wire [31:0] b_d = b[32:1]; wire b_e = b[59];
    wire [31:0] b_t = {b[62:60], b[48:33], b[53:49], 3'd0, b[58:54]};
    wire ov, oe, flt; wire [31:0] ot_, od;
    ot_s81_retn_static #(.WIN(2), .RST(1)) u_n (.clk(clk[0]), .rst_n(rst_n[0]), .a_v(a_v), .a_t(a_t), .a_d(a_d), .a_e(a_e), .b_v(b_v), .b_t(b_t), .b_d(b_d), .b_e(b_e), .o_v(ov), .o_t(ot_), .o_d(od), .o_e(oe), .fault(flt));
    assign o = {oe, od, ot_, ov};
    reg fr; always @(posedge clk[0] or negedge rst_n[0]) if (!rst_n[0]) fr <= 1'b0; else fr <= flt | fi[0];
    assign fo = fr;
endmodule
