`timescale 1ns/1ps
// Physical characterization shell for one 265-bit packed-row group.
// The request and response registers represent the local row-buffer boundary;
// this shell is not on the token RTL path and adds two interface cycles.
module ot_chip_v41x_attn_stage_port_phy (
    input wire clk,
    input wire wr_en,
    input wire [7:0] wr_addr,
    input wire [264:0] wr_data,
    input wire [7:0] rd_addr,
    output reg [264:0] rd_data
);
    reg wr_en_q;
    reg [7:0] wr_addr_q, rd_addr_q;
    reg [264:0] wr_data_q;
    wire [264:0] mem_q;
    always @(posedge clk) begin
        wr_en_q <= wr_en;
        wr_addr_q <= wr_addr;
        wr_data_q <= wr_data;
        rd_addr_q <= rd_addr;
        rd_data <= mem_q;
    end
    ot_hdc_v41x_attn_staging #(.D(32), .NL(1), .TROWS(160), .SRAM_MACRO(1)) u_stage (
        .clk(clk), .wr_en(wr_en_q), .wr_addr(wr_addr_q), .wr_data(wr_data_q),
        .rd_addr(rd_addr_q), .rd_data(mem_q));
endmodule
