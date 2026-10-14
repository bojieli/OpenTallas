`timescale 1ns/1ps
module ot_qwen_tp8_pv256_finalize_tb(
 input wire clk,rst_n,start,input wire [15:0] epoch,
 input wire [127:0] reciprocal,input wire reciprocal_valid,
 output wire reciprocal_ready,input wire [15:0] reciprocal_epoch,
 input wire p0_valid,p1_valid,output wire p0_ready,p1_ready,
 input wire [15:0] p0_epoch,p1_epoch,input wire [16383:0] p0_partial,p1_partial,
 output wire out_valid,input wire out_ready,output wire [16383:0] out_data,
 output wire [15:0] out_epoch,output wire fault
);
// Functional adapter only; real parent exposes all 32 independent join roots.
 ot_qwen_tp8_pv256_finalize u(.clk_join({32{clk}}),.clk_control(clk),.*);
endmodule
