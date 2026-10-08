`timescale 1ns/1ps
// Full-shape spatial lane. Six-band serialization is deliberately not implicit.
// Opt-in physical candidate: current token RTL and its latency remain unchanged.
// OSTN = 1 (qwen-blocks 2026-10-07; 0 = original): y and fault leave through kept pin-station registers beside the
// right face (+1 cycle), and the tree's per-level fault ORs are registered (+1 fault cycle).
module ot_qwen_spine_lane #(
    parameter integer TREE_LAT = 7,
    parameter integer OSTN = 0
) (
    input wire clk,
    input wire rst_n,
    input wire [1535:0] t_in,
    input wire [13:0] sel_e,
    input wire [13:0] tv_e,
    output wire [1535:0] y,
    output wire fault
);
    wire [1535:0] y_t;
    wire f_t;
    ot_qwen_me_sptree_w12 #(.GT(6144),.SMIN(7),.TCUT(7),
        .TREE_LAT(TREE_LAT),.TINREG(1),.FREG(OSTN)) u_lane (
        .clk(clk),.rst_n(rst_n),.t_in(t_in),.sel_e(sel_e),.tv_e(tv_e),.y(y_t),.fault(f_t));
    generate if (OSTN != 0) begin : g_ostn
        (* keep *) reg [1535:0] y_p;
        (* keep *) reg f_p;
        always @(posedge clk) y_p <= y_t;
        always @(posedge clk or negedge rst_n) if (!rst_n) f_p <= 1'b0; else f_p <= f_t;
        assign y = y_p; assign fault = f_p;
    end else begin : g_w
        assign y = y_t; assign fault = f_t;
    end endgenerate
endmodule
