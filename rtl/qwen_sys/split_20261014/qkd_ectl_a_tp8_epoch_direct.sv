`timescale 1ns/1ps
// Native direct-seam successor, retaining the closed A/B/C stage allocation.
module qkd_ectl_a_tp8_epoch_direct (
    input wire ck, rst_n, input wire [4:0] cfg,
    output wire [16:0] rq, input wire [1024:0] rs,
    output wire [511:0] t0_row, t1_row,
    input wire [51:0] x_i, output wire [512:0] rs_o
);
    qkd_ectl_a_tp8_direct #(.EPOCH(1)) u (.*);
endmodule
