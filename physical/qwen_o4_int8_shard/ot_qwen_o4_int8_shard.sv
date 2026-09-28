`timescale 1ns/1ps
// Bounded physical probe: one 266-bit ROM abstract feeding 32 signed-INT8
// product lanes. The 32-lane read uses 256 data bits; ten macro bits are spare.
// This is a structural P&R vehicle, not the full G=6144 tile.
module ot_qwen_o4_int8_shard (
    input wire clk,
    input wire rst_n,
    input wire ce_in,
    input wire [12:0] addr_in,
    input wire [15:0] x_bf16,
    input wire [4:0] lane_sel,
    input wire scale_valid,
    input wire [31:0] completed_sum,
    input wire [15:0] row_scale_bf16,
    output wire product_out_valid,
    output wire [31:0] product,
    output wire product_fault,
    output wire scaled_out_valid,
    output wire [31:0] scaled_result,
    output wire scale_fault
);
    wire [265:0] rd_out;
    wire [31:0] products [0:31];
    wire [31:0] valid;
    wire [31:0] faults;
    ot_rom_8192x266_m8 u_weight_rom (
        .clk(clk), .ce_in(ce_in), .addr_in(addr_in), .rd_out(rd_out)
    );
    for (genvar i = 0; i < 32; i = i + 1) begin: gen_lane
        ot_hdc_qwen_int8_arith u_lane (
            .clk(clk), .rst_n(rst_n), .product_valid(ce_in),
            .code_lo(rd_out[8*i +: 4]), .code_hi(rd_out[8*i+4 +: 4]),
            .x_bf16(x_bf16), .product_out_valid(valid[i]),
            .product(products[i]), .product_fault(faults[i]),
            .scale_valid((i == 0) ? scale_valid : 1'b0),
            .completed_sum(completed_sum), .row_scale_bf16(row_scale_bf16),
            .scaled_out_valid(), .scaled_result(), .scale_fault()
        );
    end
    // The selected result keeps every lane live through synthesis while
    // retaining a bounded top-level pin count.
    assign product = products[lane_sel];
    assign product_out_valid = valid[lane_sel];
    assign product_fault = faults[lane_sel];
    ot_hdc_qwen_int8_arith u_row_scale (
        .clk(clk), .rst_n(rst_n), .product_valid(1'b0),
        .code_lo(4'b0), .code_hi(4'b0), .x_bf16(16'b0),
        .product_out_valid(), .product(), .product_fault(),
        .scale_valid(scale_valid), .completed_sum(completed_sum),
        .row_scale_bf16(row_scale_bf16), .scaled_out_valid(scaled_out_valid),
        .scaled_result(scaled_result), .scale_fault(scale_fault)
    );
endmodule
