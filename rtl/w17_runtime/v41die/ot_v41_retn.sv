`timescale 1ns/1ps
// ot_v41_retn: one return-tree node of the adopted V4.1 ROM field (W17): W10's ot_v41_ret_node followed by RST
// wire register stages -- exactly the per-level stage of W10's ot_v41_rom_array.  Used by ot_v41_field and, as a
// separately compiled model, by the runtime composition (rtl/test/v41_runtime).
module ot_v41_retn #(
    parameter integer RD = 64,
    parameter integer RST = 1,
    parameter integer BYPASS = 1
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        a_v,
    input  wire [31:0] a_t,
    input  wire [31:0] a_d,
    input  wire        a_e,
    input  wire        b_v,
    input  wire [31:0] b_t,
    input  wire [31:0] b_d,
    input  wire        b_e,
    output wire        o_v,
    output wire [31:0] o_t,
    output wire [31:0] o_d,
    output wire        o_e,
    output wire        fault,
    output wire        quiet            // nothing queued or in flight (simulation host: skip while inputs idle)
);
    wire ov, oe;
    wire [31:0] ot, od;
    ot_v41_ret_node #(.D(RD), .BYPASS(BYPASS)) u_n (.clk(clk), .rst_n(rst_n),
        .a_v(a_v), .a_t(a_t), .a_d(a_d), .a_e(a_e), .b_v(b_v), .b_t(b_t), .b_d(b_d), .b_e(b_e),
        .o_v(ov), .o_t(ot), .o_d(od), .o_e(oe), .fault(fault));
    wire [64:0] rq;
    ot_hdc_delay #(.W(65), .D(RST)) u_rd (.clk(clk), .rst_n(rst_n), .d({ot, od, oe}), .q(rq));
    wire [RST:0] rv;
    assign rv[0] = ov;
    genvar r;
    generate for (r = 0; r < RST; r = r + 1) begin : g_rv
        reg q;
        always @(posedge clk or negedge rst_n) if (!rst_n) q <= 1'b0; else q <= rv[r];
        assign rv[r+1] = q;
    end endgenerate
    assign o_v = rv[RST];
`ifdef V41_RT
    assign quiet = u_n.ac == 0 && u_n.bc == 0 && u_n.vp == 0 && u_n.ap == 0 && !u_n.by_v && rv[RST:1] == '0 && !a_v && !b_v;
`else
    assign quiet = 1'b0;
`endif
    assign o_t = rq[64:33];
    assign o_d = rq[32:1];
    assign o_e = rq[0];
endmodule

