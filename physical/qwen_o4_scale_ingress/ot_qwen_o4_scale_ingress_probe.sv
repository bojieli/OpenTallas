`timescale 1ns/1ps
// Physical cut at one O4 group after the FP32 K-split tree. Both arms have
// sixteen row-scale multipliers, the same source capture, and the same clock.
// ROM includes a single analytical 8192x266 macro (256 useful bits); HBM
// starts at a registered local 256-bit scale-word boundary. Neither arm is a
// whole tile, HBM controller, or token simulation.
module ot_qwen_o4_scale_ingress_probe #(
    parameter integer HBM_SOURCE = 0
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         valid,
    input  wire         scale_group_re,
    input  wire [12:0]  rom_addr,
    input  wire [255:0] hbm_scale_word,
    input  wire [511:0] completed_sum,
    output wire         out_valid,
    output wire [511:0] scaled_result,
    output wire         fault
);
    wire [255:0] source_scale;
    generate if (HBM_SOURCE == 0) begin: g_rom
        wire [265:0] rom_q;
        ot_rom_8192x266_m8 u_scale_rom (
            .clk(clk), .ce_in(scale_group_re), .addr_in(rom_addr), .rd_out(rom_q)
        );
        assign source_scale = rom_q[255:0];
    end else begin: g_hbm
        assign source_scale = hbm_scale_word;
    end endgenerate

    reg [255:0] scale_q;
    reg [511:0] sum_q;
    reg [5:0] valid_q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) valid_q <= 6'b0;
        else valid_q <= {valid_q[4:0], valid};
    end
    always @(posedge clk) begin
        if (scale_group_re) scale_q <= source_scale;
        sum_q <= completed_sum;
    end
    wire [15:0] faults;
    for (genvar i = 0; i < 16; i = i + 1) begin: g_scale_lane
        ot_hdc_fmul u_mul (
            .clk(clk), .rst_n(rst_n), .v(valid_q[0]),
            .a(sum_q[32*i +: 32]), .b({scale_q[16*i +: 16], 16'b0}),
            .y(scaled_result[32*i +: 32]), .fault(faults[i])
        );
    end
    assign out_valid = valid_q[5];
    assign fault = |faults;
endmodule
