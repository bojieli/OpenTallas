`timescale 1ns/1ps
// One local eight-lane HCP activation slice with the analytical ASAP7 SRAM
// abstract.  Its single registered read matches the HE adapter's ex_data
// stage; the 128-bit write accepts one complete eight-lane chunk per cycle.
module ot_hdc_v41x_he_xslice_macro #(
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
    output wire [LANES*16-1:0] rd_data
);
    wire [255:0] q;
    wire [LANES*16-1:0] lane_mask = ({{(LANES-1){16'b0}},16'hffff} << (wr_lane*16));
    wire [LANES*16-1:0] lane_data = ({{(LANES-1){16'b0}},wr_data} << (wr_lane*16));
    ot_sram_1r1w_128x256_m1_r2c2 u_mem (
        .clk(clk), .r_ce_in(rd_v), .r_addr_in(7'(rd_addr)), .rd_out(q),
        .w_ce_in(pre_v || wr_v), .w_addr_in(7'(pre_v ? pre_addr : wr_addr)),
        .wd_in({128'b0,pre_v ? pre_data : lane_data}),
        .w_mask_in({128'b0,pre_v ? {128{1'b1}} : lane_mask}),
        .rr_en(2'b0), .rr_addr(14'b0), .cr_en(2'b0), .cr_sel(16'b0));
    assign rd_data = q[LANES*16-1:0];
endmodule
