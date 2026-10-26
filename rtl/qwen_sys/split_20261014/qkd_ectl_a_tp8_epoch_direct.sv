`timescale 1ns/1ps
// Native direct-seam successor, retaining the closed A/B/C stage allocation.
module qkd_ectl_a_tp8_epoch_direct #(parameter integer STATIC_QK=0, parameter integer QK_ISSUE_AGE=34, parameter integer ROW_RETURN_LAT=9, parameter integer HXK=0) (
    input wire ck, rst_n, input wire [4:0] cfg,
    output wire [16:0] rq, input wire [1024:0] rs,
    output wire [511:0] t0_row, t1_row,
    input wire [51:0] x_i, output wire [512:0] rs_o
);
    qkd_ectl_a_tp8_direct #(.EPOCH(1), .STATIC_QK(STATIC_QK), .QK_ISSUE_AGE(QK_ISSUE_AGE), .ROW_RETURN_LAT(ROW_RETURN_LAT), .HXK(HXK)) u (.*);
endmodule
