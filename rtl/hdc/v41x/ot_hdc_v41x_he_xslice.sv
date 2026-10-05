`timescale 1ns/1ps
// One local eight-lane slice of one HCP term bank.  Thirty-two such slices per
// term bank implement a 2,048-lane HCP; each slice sits next to its eight MAC
// lanes.  The fixed one-cycle read is the adapter's existing ex_data register,
// so HCP ML=2 is preserved.  A foundry SRAM macro can replace mem without
// changing the HCP issue schedule or its chunk8 reduction tree.
module ot_hdc_v41x_he_xslice #(
    parameter integer DEPTH = 80,         // PMAX * ceil(2560/HW), HW=256, PMAX=8
    parameter integer LANES = 8,
    parameter integer AW = $clog2(DEPTH),
    parameter integer LW = $clog2(LANES)
) (
    input  wire                   clk,
    input  wire                   wr_v,
    input  wire [AW-1:0]          wr_addr,
    input  wire [LW-1:0]          wr_lane,
    input  wire [15:0]            wr_data,
    input  wire                   rd_v,
    input  wire [AW-1:0]          rd_addr,
    output reg  [LANES*16-1:0]   rd_data
);
    reg [LANES*16-1:0] mem [0:DEPTH-1];
    always @(posedge clk) begin
        if (wr_v) mem[wr_addr][wr_lane*16 +:16] <= wr_data;
        if (rd_v) rd_data <= mem[rd_addr];
    end
endmodule
