`timescale 1ns/1ps
// Characterization boundary for one literal 256-bit bank of the 68-bank
// full-shape attention staging array. Registers are boundary assumptions,
// not added to the adopted token RTL.
module ot_chip_v41x_attn_sram_bank_phy (
    input wire clk,
    input wire wr_en,
    input wire [7:0] wr_addr,
    input wire [255:0] wr_data,
    input wire [7:0] rd_addr,
    output reg [255:0] rd_data
);
    reg wr_en_q;
    reg [7:0] wr_addr_q, rd_addr_q;
    reg [255:0] wr_data_q;
    wire [255:0] mem_q;
    always @(posedge clk) begin
        wr_en_q <= wr_en;
        wr_addr_q <= wr_addr;
        wr_data_q <= wr_data;
        rd_addr_q <= rd_addr;
        rd_data <= mem_q;
    end
    ot_sram_1r1w_256x256_m2_r2c2 u_mem (
        .clk(clk), .r_ce_in(1'b1), .r_addr_in(rd_addr_q), .rd_out(mem_q),
        .w_ce_in(wr_en_q), .w_addr_in(wr_addr_q), .wd_in(wr_data_q),
        .w_mask_in({256{1'b1}}), .rr_en(2'b0), .rr_addr(14'b0),
        .cr_en(2'b0), .cr_sel(16'b0));
endmodule
