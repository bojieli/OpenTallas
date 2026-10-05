`timescale 1ns/1ps
module dsrom_source_root #(
    parameter integer D = 16,
    parameter integer QD = 16
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        i_v,
    input  wire [31:0] i_t,
    input  wire [31:0] i_d,
    input  wire        i_e,
    output reg         r_v,
    output reg  [15:0] r_row,
    output reg  [2:0]  r_pos,
    output reg  [31:0] r_fp32,
    output reg  [15:0] r_bf16,
    output reg         r_e,
    output reg         fault
,
output wire [15:0] obs_qc,
output wire [15:0] obs_held,
output wire obs_add,
output wire obs_sv
);
ot_v41_ret_root #(.D(D),.QD(QD)) dut(.*);
assign obs_qc=dut.qc;
assign obs_add=dut.add;
assign obs_sv=dut.sv;
integer n;reg [15:0] held;always @* begin held=0;for(n=0;n<D;n=n+1) held=held+dut.bv[n];end
assign obs_held=held;
endmodule
