`timescale 1ns/1ps
// HE local slice with a whole-word ingress.  Eight 512-bit VM words/cycle
// would deliver sixteen HCP chunks, allowing two distinct slices in each
// term bank to take one 128-bit write each.  This block is one such slice.
// A four-word VM reader can fill one slice per term bank/cycle (eight chunks).
module ot_hdc_v41x_he_xslice_wide #(
    parameter integer DEPTH=80,
    parameter integer LANES=8,
    parameter integer AW=$clog2(DEPTH),
    parameter integer LW=$clog2(LANES)
) (
    input wire clk,
    input wire wr_v,
    input wire [AW-1:0] wr_addr,
    input wire [LW-1:0] wr_lane,
    input wire [15:0] wr_data,
    input wire pre_v,
    input wire [AW-1:0] pre_addr,
    input wire [LANES*16-1:0] pre_data,
    input wire rd_v,
    input wire [AW-1:0] rd_addr,
    output reg [LANES*16-1:0] rd_data
);
    reg [LANES*16-1:0] mem [0:DEPTH-1];
    always @(posedge clk) begin
        if (pre_v) mem[pre_addr] <= pre_data;
        else if (wr_v) mem[wr_addr][wr_lane*16 +:16] <= wr_data;
        if (rd_v) rd_data <= mem[rd_addr];
    end
endmodule
