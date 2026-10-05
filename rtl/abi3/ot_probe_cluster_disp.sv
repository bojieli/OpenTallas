`timescale 1ns/1ps
module ot_probe_cluster_disp (
    input wire clk, input wire rst_n,
    input wire dv, output wire dr,
    input wire [8:0] dk, input wire [7:0] dsc, input wire [5:0] dp,
    output wire cs, output wire [8:0] ck, output wire [7:0] csc,
    input wire [15:0] busy, input wire [15:0] done,
    output wire [31:0] nd, output wire [31:0] npass,
    output wire [63:0] ub, output wire [31:0] cc, output wire [31:0] sv);
  ot_cluster_dispatcher #(.UNITS(16), .QUEUE_LOG2(3), .PASS_W(6)) u (
    .clk(clk), .rst_n(rst_n), .desc_valid(dv), .desc_ready(dr),
    .desc_k(dk), .desc_scale(dsc), .desc_passes(dp),
    .cu_start(cs), .cu_cfg_k(ck), .cu_cfg_scale(csc),
    .cu_busy(busy), .cu_done(done),
    .descriptors_retired(nd), .passes_launched(npass),
    .unit_busy_cycles(ub), .cluster_cycles(cc), .starved_cycles(sv));
endmodule
