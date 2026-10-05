`timescale 1ns/1ps
// V4.1 window KV row byte layout, independent of the HBM command scheduler.
// The producer supplies the deployed act_quant result: 512 E4M3FN codes and
// sixteen E8M0 scales, one per 32 codes.  This module does not quantize FP32
// scalar writes: quantization requires all 32 pre-quantized values in a block.
// Byte 0 is row[7:0].  Sectors 0..15 hold codes, sector 16 holds scales in
// bytes 0..15; the upper 16 bytes of that sector are padding (write-strobe 0).
// The 528-byte payload has a 544-byte HBM pitch, 17 sectors per row.
module ot_chip_v41x_window_row_codec #(
    parameter integer POS_W = 21,
    parameter integer SEC_W = 30,
    parameter integer MAX_CONTEXT = 1048576,
    parameter integer WINDOW_SLOTS = 128
) (
    input  wire [4223:0] row,
    input  wire [POS_W-1:0] position,
    input  wire [SEC_W-1:0] region_base_sector,
    input  wire [SEC_W-1:0] region_sector_count,
    input  wire [4:0] sector_index,
    output reg  [SEC_W-1:0] sector_address,
    output reg  [255:0] sector_data,
    output reg  [31:0] sector_strobe,
    output reg         address_fault,
    input  wire [8:0] element_index,
    output reg  [31:0] element_fp32,
    output reg         element_fault
);
    localparam integer PITCH_SECTORS = 17;
    localparam integer ROW_SECTORS = WINDOW_SLOTS * PITCH_SECTORS;
`ifndef SYNTHESIS
    initial if (WINDOW_SLOTS != 128 || POS_W < 21 || SEC_W < 30)
        $fatal(1, "window codec requires 128 slots, POS_W >= 21, SEC_W >= 30");
`endif
    wire [6:0] slot = position[6:0];
    reg [SEC_W:0] offset_wide, address_wide, region_end_wide;
    integer b;
    reg [7:0] code, scale;
    reg [3:0] exponent;
    reg [2:0] mantissa;
    reg [3:0] significand;
    integer k, biased, shift;
    reg [23:0] sig24;
    reg [23:0] subnormal;
    always @(*) begin
        offset_wide = (SEC_W+1)'(slot) * (SEC_W+1)'(PITCH_SECTORS) + (SEC_W+1)'(sector_index);
        address_wide = {1'b0, region_base_sector} + offset_wide;
        region_end_wide = {1'b0, region_base_sector} + {1'b0, region_sector_count};
        sector_address = address_wide[SEC_W-1:0];
        address_fault = (position >= POS_W'(MAX_CONTEXT)) || (sector_index >= 5'(PITCH_SECTORS)) ||
                        (region_sector_count < SEC_W'(ROW_SECTORS)) || address_wide[SEC_W] ||
                        region_end_wide[SEC_W] || (address_wide >= region_end_wide);
        sector_data = '0;
        sector_strobe = '0;
        if (!address_fault) begin
            if (sector_index < 16) begin
                for (b = 0; b < 32; b = b + 1)
                    sector_data[8*b +: 8] = row[8*(32*sector_index+b) +: 8];
                sector_strobe = 32'hffffffff;
            end else begin
                for (b = 0; b < 16; b = b + 1)
                    sector_data[8*b +: 8] = row[4096+8*b +: 8];
                sector_strobe = 32'h0000ffff;
            end
        end
        code = row[8*element_index +: 8];
        scale = row[4096+8*integer'(element_index >> 5) +: 8];
        exponent = code[6:3];
        mantissa = code[2:0];
        element_fp32 = '0;
        element_fault = ((code & 8'h7f) == 8'h7f) || (scale == 8'hff);
        significand = '0; k = 0; biased = 0; shift = 0; sig24 = '0; subnormal = '0;
        if (!element_fault && code[6:0] != 0) begin
            if (exponent != 0) begin
                significand = {1'b1, mantissa};
                biased = integer'(exponent) + integer'(scale) - 7;
            end else begin
                k = mantissa[2] ? 2 : (mantissa[1] ? 1 : 0);
                significand = {1'b0, mantissa} << (3-k);
                biased = integer'(scale) + k - 9;
            end
            sig24 = {significand, 20'b0};
            if (biased > 254) element_fault = 1'b1;
            else if (biased > 0)
                element_fp32 = {code[7], 8'(biased), sig24[22:0]};
            else begin
                shift = 1-biased;
                subnormal = sig24 >> shift;
                element_fp32 = {code[7], 8'b0, subnormal[22:0]};
            end
        end
        if (code[6:0] == 0) element_fp32 = '0; // canonical +0
        if (element_fault) element_fp32 = '0;
    end
endmodule
