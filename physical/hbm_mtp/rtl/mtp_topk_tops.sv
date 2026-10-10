`timescale 1ns/1ps
// mtp-hbm 2026-10-08: parameter-free route tops of the router top-K selector (Yosys chparam assertion workaround)
// router top-K selector, full shape (W19 B2 exact): the 1.2 GHz successor and the original
module mtp_topk_f384 (input wire clk, input wire rst_n, input wire in_valid, input wire [511:0] in_vals,
    input wire in_last, output wire out_valid, output wire [53:0] out_ids);
    ot_gpu_router_topk_f #(.N(384), .P(16), .K(6), .IW(9)) u (.clk(clk), .rst_n(rst_n), .in_valid(in_valid),
        .in_vals(in_vals), .in_last(in_last), .out_valid(out_valid), .out_ids(out_ids));
endmodule
module mtp_topk_384 (input wire clk, input wire rst_n, input wire in_valid, input wire [511:0] in_vals,
    input wire in_last, output wire out_valid, output wire [53:0] out_ids);
    ot_gpu_router_topk #(.N(384), .P(16), .K(6), .IW(9)) u (.clk(clk), .rst_n(rst_n), .in_valid(in_valid),
        .in_vals(in_vals), .in_last(in_last), .out_valid(out_valid), .out_ids(out_ids));
endmodule
