`timescale 1ns/1ps
// One 16-bit ME activation bank for a full 5,120-element position.  This is
// the unit of SRAM macro placement; 8*MG banks form the independent-read
// activation store.  The read is registered, exactly as the adapter's xr[0].
module ot_hdc_v41x_me_xslice #(
    parameter integer DEPTH = 80,
    parameter integer AW = $clog2(DEPTH)
) (
    input wire clk,
    input wire wr_v,
    input wire [AW-1:0] wr_addr,
    input wire [15:0] wr_data,
    input wire rd_v,
    input wire [AW-1:0] rd_addr,
    output reg [15:0] rd_data
);
    reg [15:0] mem [0:DEPTH-1];
    always @(posedge clk) begin
        if (wr_v) mem[wr_addr] <= wr_data;
        if (rd_v) rd_data <= mem[rd_addr];
    end
endmodule
