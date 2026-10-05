`timescale 1ns/1ps
// Area probe: the cheapest lane-multiplier copy of one matrix-engine group --
// W lanes of (exact BF16 multiplier -> pipelined FP32 add with the IL-cycle
// circulation and the first-element select), exactly the per-lane datapath of
// ot_hdc_matvec, fed by the group's SHARED weight word (w, registered once for
// the group) and the copy's own x operand; the split tree, the result port and
// the argmax are shared with (time-multiplexed from) the base lane and are not
// here.  Sums leave through a registered port.
module ot_hdc_lane_copy #(
    parameter integer W  = 16,
    parameter integer IL = 8
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire            v,
    input  wire            first,
    input  wire [W*32-1:0] w,
    input  wire [31:0]     x,
    output reg  [W*32-1:0] sum_q,
    output reg             fault
);
    localparam integer FB = IL - 5;
    reg [31:0] x_q;
    reg v_q, first_q;
    always @(posedge clk) begin x_q <= x; v_q <= v; first_q <= first; end
    wire [5:0] vl;
    ot_hdc_vline #(.D(5)) u_v (.clk(clk), .rst_n(rst_n), .v(v_q), .vd(vl));
    wire [5:0] fl;
    ot_hdc_vline #(.D(5)) u_f (.clk(clk), .rst_n(rst_n), .v(v_q && first_q), .vd(fl));
    wire [W*32-1:0] sum;
    wire [W-1:0] lf;
    genvar l;
    generate for (l = 0; l < W; l = l + 1) begin : g_lane
        wire [31:0] prod, fb_pre;
        reg  [31:0] acc_q;
        wire f0, f1;
        ot_hdc_bmul u_mul (.clk(clk), .rst_n(rst_n), .v(v_q), .a(w[32*l +: 32]), .b(x_q), .y(prod), .fault(f0));
        always @(posedge clk) acc_q <= fl[4] ? 32'd0 : fb_pre;
        ot_hdc_fadd u_add (clk, rst_n, vl[5], acc_q, prod, sum[32*l +: 32], f1);
        ot_hdc_delay #(.W(32), .D(FB - 1)) u_fb (.clk(clk), .rst_n(rst_n), .d(sum[32*l +: 32]), .q(fb_pre));
        assign lf[l] = f0 | f1;
    end endgenerate
    always @(posedge clk) begin sum_q <= sum; fault <= |lf; end
endmodule
