`timescale 1ns/1ps
// Physical proposal only. Compared with the direct cut, the synchronous
// memory output is captured without a data mux and the read enable drives
// only the ROM CE and a local valid flop. One added data stage is common to
// ROM and HBM; production matvec tag/valid/writeback alignment is not edited.
module ot_qwen_o4_scale_registered_probe #(
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

    reg [255:0] raw_scale_q, scale_q;
    reg [511:0] raw_sum_q, sum_q;
    reg req_q;
    reg [6:0] valid_q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            req_q <= 1'b0;
            valid_q <= 7'b0;
        end else begin
            req_q <= scale_group_re;
            valid_q <= {valid_q[5:0], valid && req_q};
        end
    end
    always @(posedge clk) begin
        raw_scale_q <= source_scale;
        raw_sum_q <= completed_sum;
        scale_q <= raw_scale_q;
        sum_q <= raw_sum_q;
    end
    wire [15:0] faults;
    for (genvar i = 0; i < 16; i = i + 1) begin: g_scale_lane
        ot_hdc_fmul u_mul (
            .clk(clk), .rst_n(rst_n), .v(valid_q[1]),
            .a(sum_q[32*i +: 32]), .b({scale_q[16*i +: 16], 16'b0}),
            .y(scaled_result[32*i +: 32]), .fault(faults[i])
        );
    end
    assign out_valid = valid_q[6];
    assign fault = |faults;
endmodule
